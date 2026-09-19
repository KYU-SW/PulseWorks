from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import (
    AiSummary,
    AiSummaryStatus,
    ClinicalReport,
    ClinicalReportStatus,
    Encounter,
    Patient,
    Role,
    User,
)
from app.schemas.clinical_report import (
    ClinicalReportCreate,
    ClinicalReportOut,
    EmrSnapshot,
    ReportContentSnapshot,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.services.mock_narrative import generate_mock_report_narrative
from app.services.report_data import ReportScopeError, collect_report_data

# 서로 다른 URL prefix(/patients/... vs /reports/...)를 하나의
# APIRouter(prefix=...)로 표현할 수 없어 두 개로 나눈다 — 계획 문서의
# Task 12(구 번호) 사례와 동일한 방식.
patient_reports_router = APIRouter(prefix="/patients", tags=["clinical_reports"])
reports_router = APIRouter(prefix="/reports", tags=["clinical_reports"])

_REPORT_SCOPE_NOT_FOUND_MESSAGE = "환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다."


def _to_clinical_report_out(report: ClinicalReport) -> ClinicalReportOut:
    return ClinicalReportOut(
        id=report.id,
        patient_id=report.patient_id,
        encounter_id=report.encounter_id,
        report_type=report.report_type.value,
        scope_type=report.scope_type.value,
        scope_encounter_ids=report.scope_encounter_ids,
        status=report.status.value,
        content=ReportContentSnapshot.model_validate(report.content),
        created_by_user_id=report.created_by_user_id,
        created_at=report.created_at,
        last_modified_by_user_id=report.last_modified_by_user_id,
        last_modified_at=report.last_modified_at,
        reviewed_by_user_id=report.reviewed_by_user_id,
        reviewed_at=report.reviewed_at,
        supersedes_report_id=report.supersedes_report_id,
    )


@patient_reports_router.post(
    "/{patient_id}/reports",
    response_model=ClinicalReportOut,
    status_code=201,
)
def create_clinical_report(
    patient_id: int,
    body: ClinicalReportCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """단일 Encounter 기준 진료참고 보고서 생성. DOCTOR 전용이며, 배정된
    담당 의사만 만들 수 있다(다른 담당 의사의 승인은 필요 없음 — 작성자와
    승인자가 같아도 된다는 정책은 Task 17에서 적용된다). 미배정/미존재
    환자, 존재하지 않는 Encounter, 다른 환자에게 속한 Encounter는 모두
    구분 없이 같은 404로 처리한다.

    동일한 (환자, 보고서 종류, 스코프, Encounter, 작성자) 조합의 DRAFT가
    이미 있으면 새로 만들지 않고 그 DRAFT를 그대로 반환한다(200) — 매번
    새 레코드가 쌓이지 않는다. 서로 다른 의사가 같은 조건으로 요청하면
    각자 별도의 DRAFT를 가질 수 있다.
    """
    patient = db.query(Patient).filter_by(id=patient_id).first()
    if patient is None or not can_access_patient(user, patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    encounter_id = body.encounter_ids[0]
    encounter = db.query(Encounter).filter_by(id=encounter_id).first()
    if encounter is None or encounter.patient_id != patient_id:
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    existing = (
        db.query(ClinicalReport)
        .filter_by(
            patient_id=patient_id,
            report_type=body.report_type,
            scope_type=body.scope_type,
            encounter_id=encounter_id,
            created_by_user_id=user.id,
            status=ClinicalReportStatus.DRAFT,
        )
        .first()
    )
    if existing is not None:
        response.status_code = 200
        return _to_clinical_report_out(existing)

    try:
        report_data = collect_report_data(db, patient_id, [encounter_id])
    except ReportScopeError:
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    content_snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data),
        narrative=None,
        handoff_note=None,
        patient_guidance=None,
    )

    now = datetime.now(timezone.utc)
    report = ClinicalReport(
        patient_id=patient_id,
        encounter_id=encounter_id,
        report_type=body.report_type,
        scope_type=body.scope_type,
        scope_encounter_ids=[encounter_id],
        status=ClinicalReportStatus.DRAFT,
        content=content_snapshot.model_dump(mode="json"),
        created_by_user_id=user.id,
        created_at=now,
        last_modified_by_user_id=user.id,
        last_modified_at=now,
        reviewed_by_user_id=None,
        reviewed_at=None,
        supersedes_report_id=None,
    )

    try:
        db.add(report)
        db.flush()
        write_audit_log(
            db,
            actor_user_id=user.id,
            action="CREATE_REPORT",
            resource_type="ClinicalReport",
            resource_id=str(report.id),
            reason="single_encounter_report_created",
            patient_id=patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="보고서 생성 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)


@reports_router.get("/{report_id}", response_model=ClinicalReportOut)
def get_clinical_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """저장된 보고서 스냅샷을 그대로 반환한다 — 원본 EMR 데이터를 다시
    수집하지 않는다. 존재하지 않는 report_id와 접근권한이 없는 report_id는
    구분 없이 같은 404로 처리한다."""
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if report is None or not can_access_patient(user, report.patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="VIEW_REPORT",
        resource_type="ClinicalReport",
        resource_id=str(report.id),
        reason="assigned_patient_report_view",
        patient_id=report.patient_id,
    )
    db.commit()

    return _to_clinical_report_out(report)


def _find_reusable_ai_summary(
    db: Session, patient_id: int, encounter_id: int, summary_text: str, source_record_ids: list[str]
) -> AiSummary | None:
    """(patient_id, encounter_id, status=DRAFT, summary_text) 조건으로 후보를
    좁힌 뒤, source_record_ids를 정렬해 정확히 일치하는 것만 재사용한다.
    JSON 배열 값 비교는 DB 쿼리 조건으로 이식성 있게 표현하기 어려워
    Python에서 비교한다."""
    sorted_target = sorted(source_record_ids)
    candidates = (
        db.query(AiSummary)
        .filter_by(
            patient_id=patient_id,
            encounter_id=encounter_id,
            status=AiSummaryStatus.DRAFT,
            summary_text=summary_text,
        )
        .all()
    )
    for candidate in candidates:
        if sorted(candidate.source_record_ids) == sorted_target:
            return candidate
    return None


@reports_router.post("/{report_id}/generate-narrative", response_model=ClinicalReportOut)
def generate_report_narrative(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """저장된 report.content.emr_snapshot만으로 결정적 Mock 설명문을
    만들어 content.narrative에 채운다. 원본 EMR 테이블을 다시 조회하지
    않는다 — collect_report_data()를 호출하지 않는다.

    DRAFT에서만 실행할 수 있다(APPROVED/REJECTED는 409). narrative가 이미
    있으면 자동으로 덮어쓰지 않고 기존 보고서를 그대로 200으로 반환한다 —
    강제 재생성 기능은 없다. 실제 LLM이나 외부 AI API를 호출하지 않는다.
    """
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if report is None or not can_access_patient(user, report.patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    if report.status != ClinicalReportStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail="검토가 이미 완료된 보고서의 설명문은 새로 생성할 수 없습니다.",
        )

    content = ReportContentSnapshot.model_validate(report.content)
    if content.narrative is not None:
        # 멱등성: 이미 생성된 설명문이 있으면 그대로 반환한다 — AiSummary
        # 추가 생성, content 재저장, 감사 로그, last_modified 갱신 없음.
        return _to_clinical_report_out(report)

    mock_result = generate_mock_report_narrative(content.emr_snapshot)

    new_content = ReportContentSnapshot(
        emr_snapshot=content.emr_snapshot,
        narrative=mock_result.summary_text,
        handoff_note=content.handoff_note,
        patient_guidance=content.patient_guidance,
    )

    now = datetime.now(timezone.utc)

    try:
        existing_summary = _find_reusable_ai_summary(
            db, report.patient_id, report.encounter_id,
            mock_result.summary_text, mock_result.source_record_ids,
        )
        if existing_summary is None:
            db.add(
                AiSummary(
                    encounter_id=report.encounter_id,
                    patient_id=report.patient_id,
                    status=AiSummaryStatus.DRAFT,
                    summary_text=mock_result.summary_text,
                    source_record_ids=mock_result.source_record_ids,
                    generated_at=now,
                    reviewed_by_user_id=None,
                    reviewed_at=None,
                )
            )
            db.flush()

        # JSON 내부를 제자리 수정하지 않는다 — 전체 새 dict를 만들어
        # 통째로 재할당한다.
        report.content = new_content.model_dump(mode="json")
        report.last_modified_by_user_id = user.id
        report.last_modified_at = now

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="GENERATE_REPORT_NARRATIVE",
            resource_type="ClinicalReport",
            resource_id=str(report.id),
            reason="deterministic_mock_narrative",
            patient_id=report.patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="설명문 생성 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)

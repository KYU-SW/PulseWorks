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
    ClinicalReportType,
    Encounter,
    Patient,
    Role,
    User,
)
from app.schemas.clinical_report import (
    ClinicalReportCreate,
    ClinicalReportOut,
    ClinicalReportPatch,
    EmrSnapshot,
    ReportContentSnapshot,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.services.narrative_providers.base import NarrativeProviderError
from app.services.narrative_providers.factory import get_narrative_provider
from app.services.narrative_validation import validate_narrative_provider_result
from app.services.report_data import ReportScopeError, collect_report_data

# 서로 다른 URL prefix(/patients/... vs /reports/...)를 하나의
# APIRouter(prefix=...)로 표현할 수 없어 두 개로 나눈다 — 계획 문서의
# Task 12(구 번호) 사례와 동일한 방식.
patient_reports_router = APIRouter(prefix="/patients", tags=["clinical_reports"])
reports_router = APIRouter(prefix="/reports", tags=["clinical_reports"])

_REPORT_SCOPE_NOT_FOUND_MESSAGE = "환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다."
# Task 17의 PATCH/approve/reject 세 엔드포인트가 공유하는 "이미 검토 완료된
# 보고서" 409 문구 — Task 16의 generate-narrative는 이미 커밋된 별도 문구를
# 그대로 두고(범위 밖 코드를 건드리지 않음), 이번에 새로 추가하는 세
# 엔드포인트끼리만 문구를 통일한다.
_REPORT_ALREADY_REVIEWED_MESSAGE = "검토가 이미 완료된 보고서는 수정할 수 없습니다."
_NARRATIVE_REQUIRED_FOR_APPROVAL_MESSAGE = "설명문을 작성하거나 생성한 후 승인할 수 있습니다."
# NarrativeProviderError의 code(LLM_API_KEY_MISSING 등)나 검증 실패
# 사유를 그대로 노출하지 않는다 - 둘 다 이 두 일반 메시지로만 응답한다.
_NARRATIVE_PROVIDER_UNAVAILABLE_MESSAGE = "설명문 생성 서비스를 사용할 수 없습니다."
_NARRATIVE_VALIDATION_FAILED_MESSAGE = "생성된 설명문이 검증을 통과하지 못했습니다."


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


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
    """저장된 report.content.emr_snapshot만으로 설명문을 만들어
    content.narrative에 채운다. 원본 EMR 테이블을 다시 조회하지 않는다 —
    collect_report_data()를 호출하지 않는다.

    DRAFT에서만 실행할 수 있다(APPROVED/REJECTED는 409). narrative가 이미
    있으면 자동으로 덮어쓰지 않고 기존 보고서를 그대로 200으로 반환한다 —
    강제 재생성 기능은 없다(이 분기가 provider 선택보다 먼저 있어,
    narrative가 있으면 provider를 아예 호출하지 않는다).

    실제로 어떤 provider를 쓸지는 NARRATIVE_PROVIDER 설정이 결정한다
    (기본값 mock). NARRATIVE_PROVIDER=llm인데 키/모델이 없거나 실제
    Adapter가 아직 없으면 Mock으로 조용히 대체하지 않고 503으로
    실패한다 — 이번 버전은 실제 LLM이나 외부 AI API를 호출하지 않는다.
    provider 결과는 저장하기 전 항상 validate_narrative_provider_result()를
    통과해야 한다 — 실패하면 AiSummary/ClinicalReport.content/감사
    로그/last_modified 무엇도 바뀌지 않는다.
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
        # 멱등성: 이미 생성된 설명문이 있으면 그대로 반환한다 — provider를
        # 아예 호출하지 않는다. AiSummary 추가 생성, content 재저장,
        # 감사 로그, last_modified 갱신 없음.
        return _to_clinical_report_out(report)

    try:
        provider = get_narrative_provider()
        provider_result = provider.generate(content.emr_snapshot)
    except NarrativeProviderError:
        # code(LLM_API_KEY_MISSING 등)는 서버 로그에만 남고 응답에는
        # 노출하지 않는다. DB에는 아무것도 쓰지 않았으므로 rollback도
        # 필요 없다.
        raise HTTPException(status_code=503, detail=_NARRATIVE_PROVIDER_UNAVAILABLE_MESSAGE)

    validation = validate_narrative_provider_result(provider_result, content.emr_snapshot)
    if not validation.ok:
        # 검증 사유(reason)도 응답에 노출하지 않는다. 마찬가지로 DB에는
        # 아직 아무것도 쓰지 않았다.
        raise HTTPException(status_code=502, detail=_NARRATIVE_VALIDATION_FAILED_MESSAGE)

    new_content = ReportContentSnapshot(
        emr_snapshot=content.emr_snapshot,
        narrative=provider_result.narrative,
        handoff_note=content.handoff_note,
        patient_guidance=content.patient_guidance,
    )

    now = datetime.now(timezone.utc)
    # Mock 성공은 Task 16의 기존 문구를 그대로 유지한다 — mock 기본값에서
    # 감사 로그가 조금이라도 달라지면 안 된다.
    audit_reason = (
        "deterministic_mock_narrative"
        if provider_result.provider == "DETERMINISTIC_MOCK"
        else "llm_generated_narrative"
    )

    try:
        existing_summary = _find_reusable_ai_summary(
            db, report.patient_id, report.encounter_id,
            provider_result.narrative, provider_result.cited_record_ids,
        )
        if existing_summary is None:
            db.add(
                AiSummary(
                    encounter_id=report.encounter_id,
                    patient_id=report.patient_id,
                    status=AiSummaryStatus.DRAFT,
                    summary_text=provider_result.narrative,
                    source_record_ids=provider_result.cited_record_ids,
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
            reason=audit_reason,
            patient_id=report.patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="설명문 생성 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)


@reports_router.patch("/{report_id}", response_model=ClinicalReportOut)
def patch_clinical_report(
    report_id: int,
    body: ClinicalReportPatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """DRAFT(또는 REJECTED — 자동으로 DRAFT로 되돌아감)의 서술형 필드
    (narrative/handoff_note/patient_guidance)만 수정한다. APPROVED는
    409로 거부한다 — 승인된 보고서는 이 Task에서 절대 바뀌지 않는다
    (새 DRAFT를 만드는 supersedes 흐름은 이후 Task의 몫).

    요청에 실제로 포함된 필드만 반영하고(model_fields_set 기준), 나머지
    두 필드는 기존 값을 그대로 유지한다. emr_snapshot은 항상 그대로
    복사해 새 content를 구성한 뒤 통째로 재할당한다 — JSON 제자리 수정을
    하지 않는다.
    """
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if report is None or not can_access_patient(user, report.patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    if report.status == ClinicalReportStatus.APPROVED:
        raise HTTPException(status_code=409, detail=_REPORT_ALREADY_REVIEWED_MESSAGE)

    was_rejected = report.status == ClinicalReportStatus.REJECTED

    content = ReportContentSnapshot.model_validate(report.content)
    provided_fields = body.model_dump(exclude_unset=True)
    new_content = ReportContentSnapshot(
        emr_snapshot=content.emr_snapshot,
        narrative=provided_fields.get("narrative", content.narrative),
        handoff_note=provided_fields.get("handoff_note", content.handoff_note),
        patient_guidance=provided_fields.get("patient_guidance", content.patient_guidance),
    )

    now = datetime.now(timezone.utc)

    try:
        report.content = new_content.model_dump(mode="json")
        report.last_modified_by_user_id = user.id
        report.last_modified_at = now

        if was_rejected:
            report.status = ClinicalReportStatus.DRAFT
            report.reviewed_by_user_id = None
            report.reviewed_at = None
            reason = "rejected_report_returned_to_draft"
        else:
            reason = "clinical_report_content_updated"

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="UPDATE_REPORT",
            resource_type="ClinicalReport",
            resource_id=str(report.id),
            reason=reason,
            patient_id=report.patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="보고서 수정 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)


@reports_router.post("/{report_id}/approve", response_model=ClinicalReportOut)
def approve_clinical_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """DRAFT 보고서만 승인할 수 있다(APPROVED/REJECTED는 409). 작성자
    본인이 승인해도 되고, 다른 담당 의사의 별도 승인은 필요 없다 —
    can_access_patient()를 만족하는 DOCTOR라면 누구나 승인할 수 있다.

    DOCTOR_REFERENCE 보고서는 narrative가 비어 있으면(None 또는 공백만)
    승인할 수 없다 — Mock 설명문을 먼저 작성/생성해야 한다.

    승인은 last_modified_by_user_id/last_modified_at을 건드리지 않는다
    — 그 컬럼은 서술형 필드 수정 시각만 의미하며, 검토 시각(reviewed_at)과
    분리되어야 한다.
    """
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if report is None or not can_access_patient(user, report.patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    if report.status != ClinicalReportStatus.DRAFT:
        raise HTTPException(status_code=409, detail=_REPORT_ALREADY_REVIEWED_MESSAGE)

    content = ReportContentSnapshot.model_validate(report.content)
    if report.report_type == ClinicalReportType.DOCTOR_REFERENCE and _is_blank(content.narrative):
        raise HTTPException(status_code=409, detail=_NARRATIVE_REQUIRED_FOR_APPROVAL_MESSAGE)

    now = datetime.now(timezone.utc)

    try:
        report.status = ClinicalReportStatus.APPROVED
        report.reviewed_by_user_id = user.id
        report.reviewed_at = now

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="APPROVE_REPORT",
            resource_type="ClinicalReport",
            resource_id=str(report.id),
            reason="clinical_report_approved",
            patient_id=report.patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="보고서 승인 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)


@reports_router.post("/{report_id}/reject", response_model=ClinicalReportOut)
def reject_clinical_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """DRAFT 보고서만 반려할 수 있다(APPROVED/REJECTED는 409). 반려 사유를
    저장할 필드가 현재 모델에 없어 이번 Task에서는 추가하지 않는다 —
    상태 전이와 감사 로그만 남긴다.

    승인과 마찬가지로 last_modified_by_user_id/last_modified_at은
    건드리지 않는다.
    """
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if report is None or not can_access_patient(user, report.patient_id, db):
        raise HTTPException(status_code=404, detail=_REPORT_SCOPE_NOT_FOUND_MESSAGE)

    if report.status != ClinicalReportStatus.DRAFT:
        raise HTTPException(status_code=409, detail=_REPORT_ALREADY_REVIEWED_MESSAGE)

    now = datetime.now(timezone.utc)

    try:
        report.status = ClinicalReportStatus.REJECTED
        report.reviewed_by_user_id = user.id
        report.reviewed_at = now

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="REJECT_REPORT",
            resource_type="ClinicalReport",
            resource_id=str(report.id),
            reason="clinical_report_rejected",
            patient_id=report.patient_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="보고서 반려 중 오류가 발생했습니다.")

    return _to_clinical_report_out(report)

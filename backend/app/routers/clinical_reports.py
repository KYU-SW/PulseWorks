from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import ClinicalReport, ClinicalReportStatus, Encounter, Patient, Role, User
from app.schemas.clinical_report import (
    ClinicalReportCreate,
    ClinicalReportOut,
    EmrSnapshot,
    ReportContentSnapshot,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
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

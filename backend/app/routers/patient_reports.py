from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import ClinicalReport, ClinicalReportStatus, Role, User
from app.schemas.clinical_report import ReportContentSnapshot
from app.schemas.patient_report import (
    PatientAllergyOut,
    PatientClinicalReportDetail,
    PatientDiagnosisOut,
    PatientLabResultOut,
    PatientLabTrendGroupOut,
    PatientLabTrendPointOut,
    PatientPrescriptionOut,
    PatientReportListItem,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.services.patient_evidence import build_patient_evidence

# 의사용 clinical_reports.py의 patient_reports_router(prefix="/patients")와는
# 별개의 라우터다 — 경로도(/patient 단수) 목적도(환자 본인 조회 전용) 다르다.
router = APIRouter(prefix="/patient", tags=["patient_reports"])

_PATIENT_REPORT_NOT_FOUND_MESSAGE = "보고서를 찾을 수 없거나 조회할 수 없습니다."
_SAFETY_NOTICE = (
    "검사결과와 참고범위만으로 건강상태를 판단하지 마세요.\n"
    "자세한 의미는 담당 의료진에게 확인하세요."
)


def _report_encounter(content: ReportContentSnapshot, report: ClinicalReport):
    """이 보고서가 다루는 대표 Encounter를 스냅샷에서 찾는다. 현재는
    SINGLE_ENCOUNTER 보고서만 존재하므로 report.encounter_id 하나로 항상
    충분하다 — collect_report_data()가 이미 그 Encounter를 스냅샷에
    포함시켰다는 것이 보장된 불변조건이다."""
    return next(e for e in content.emr_snapshot.encounters if e.id == report.encounter_id)


@router.get("/reports", response_model=list[PatientReportListItem])
def list_patient_reports(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.PATIENT)),
):
    """현재 로그인한 환자 본인의 APPROVED 보고서 목록만 반환한다. URL이나
    쿼리로 patient_id를 받지 않는다 — 서버가 user.patient_id만 사용한다.
    DRAFT/REJECTED는 제외하고, 목록 조회 자체는 감사 로그를 남기지
    않는다."""
    if user.patient_id is None:
        return []

    reports = (
        db.query(ClinicalReport)
        .filter_by(patient_id=user.patient_id, status=ClinicalReportStatus.APPROVED)
        .order_by(ClinicalReport.reviewed_at.desc())
        .all()
    )

    items = []
    for report in reports:
        content = ReportContentSnapshot.model_validate(report.content)
        encounter = _report_encounter(content, report)
        items.append(
            PatientReportListItem(
                id=report.id,
                report_type=report.report_type.value,
                department=encounter.department,
                encounter_date=encounter.start_time.date(),
                reviewed_at=report.reviewed_at,
            )
        )
    return items


@router.get("/reports/{report_id}", response_model=PatientClinicalReportDetail)
def get_patient_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.PATIENT)),
):
    """본인의 APPROVED 보고서만 조회할 수 있다. 존재하지 않음, 다른 환자
    소속, 본인 것이지만 DRAFT/REJECTED — 모두 동일한 일반화된 404다.
    저장된 report.content 스냅샷만으로 응답을 구성하며, 원본 EMR 테이블을
    다시 조회하지 않는다(collect_report_data() 미호출)."""
    report = db.query(ClinicalReport).filter_by(id=report_id).first()
    if (
        report is None
        or not can_access_patient(user, report.patient_id, db)
        or report.status != ClinicalReportStatus.APPROVED
    ):
        raise HTTPException(status_code=404, detail=_PATIENT_REPORT_NOT_FOUND_MESSAGE)

    content = ReportContentSnapshot.model_validate(report.content)
    snapshot = content.emr_snapshot
    encounter = _report_encounter(content, report)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="VIEW_REPORT",
        resource_type="ClinicalReport",
        resource_id=str(report.id),
        reason="patient_report_view",
        patient_id=report.patient_id,
    )
    db.commit()

    return PatientClinicalReportDetail(
        id=report.id,
        department=encounter.department,
        encounter_type=encounter.encounter_type,
        encounter_date=encounter.start_time.date(),
        reviewed_at=report.reviewed_at,
        narrative=content.narrative,
        patient_guidance=content.patient_guidance,
        diagnoses=[
            PatientDiagnosisOut(description=d.description, diagnosed_at=d.diagnosed_at)
            for d in snapshot.diagnoses
        ],
        lab_results=[
            PatientLabResultOut(
                test_name=lr.test_name,
                value=lr.value,
                unit=lr.unit,
                reference_low=lr.reference_low,
                reference_high=lr.reference_high,
                measured_at=lr.measured_at,
                status=lr.status,
            )
            for lr in snapshot.lab_results
        ],
        lab_trends=[
            PatientLabTrendGroupOut(
                test_name=group.test_name,
                unit=group.unit,
                points=[
                    PatientLabTrendPointOut(
                        value=point.value,
                        unit=point.unit,
                        reference_low=point.reference_low,
                        reference_high=point.reference_high,
                        measured_at=point.measured_at,
                        status=point.status,
                    )
                    for point in group.points
                ],
            )
            for group in snapshot.lab_trends
        ],
        prescriptions=[
            PatientPrescriptionOut(
                medication_name=p.medication_name,
                dosage=p.dosage,
                prescribed_at=p.prescribed_at,
            )
            for p in snapshot.prescriptions
        ],
        allergies=[
            PatientAllergyOut(substance=a.substance, reaction=a.reaction, severity=a.severity)
            for a in snapshot.allergies
        ],
        evidence=build_patient_evidence(snapshot),
        safety_notice=_SAFETY_NOTICE,
    )

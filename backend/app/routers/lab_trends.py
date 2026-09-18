from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import Encounter, LabResult, Patient, Role, User
from app.schemas.lab_trend import (
    LabTrendGroupOut,
    LabTrendPatientOut,
    LabTrendPointOut,
    PatientLabTrendsOut,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.services.lab_trend_grouping import group_lab_results_by_test

router = APIRouter(prefix="/patients", tags=["lab_trends"])

_PATIENT_NOT_FOUND_MESSAGE = "환자를 찾을 수 없거나 조회할 수 없습니다."


@router.get("/{patient_id}/lab-trends", response_model=PatientLabTrendsOut)
def get_patient_lab_trends(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """환자의 반복 검사결과를 (검사명, 단위) 기준으로 그룹화해 시간순으로
    반환한다. DOCTOR 전용이며, 매 요청마다 can_access_patient()로 담당
    관계를 다시 검사한다(IDOR 방지). 존재하지 않는 patient_id와 배정되지
    않은 patient_id는 Task 8/10과 동일하게 구분 없이 같은 404를 반환한다.

    이 판정(evaluate_lab_abnormal)은 등록된 데모 참고범위와의 기계적
    비교일 뿐이며, 진단이나 예측을 수행하지 않는다 — 최종 해석은 항상
    의료진이 수행한다.
    """
    patient = db.query(Patient).filter_by(id=patient_id).first()
    if patient is None or not can_access_patient(user, patient_id, db):
        raise HTTPException(status_code=404, detail=_PATIENT_NOT_FOUND_MESSAGE)

    encounter_ids = [
        encounter.id
        for encounter in db.query(Encounter).filter_by(patient_id=patient_id).all()
    ]

    lab_results: list[LabResult] = (
        db.query(LabResult).filter(LabResult.encounter_id.in_(encounter_ids)).all()
        if encounter_ids
        else []
    )

    trends: list[LabTrendGroupOut] = [
        LabTrendGroupOut(
            test_name=group.test_name,
            unit=group.unit,
            points=[
                LabTrendPointOut(
                    value=point.value,
                    unit=point.unit,
                    reference_low=point.reference_low,
                    reference_high=point.reference_high,
                    measured_at=point.measured_at,
                    status=point.status,
                    rule_id=point.rule_id,
                    encounter_id=point.encounter_id,
                    source_type=point.source_type,
                )
                for point in group.points
            ],
        )
        for group in group_lab_results_by_test(lab_results)
    ]

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="READ_LAB_TRENDS",
        resource_type="LabTrends",
        resource_id=str(patient_id),
        reason="assigned_patient_lab_trends",
        patient_id=patient_id,
    )
    db.commit()

    return PatientLabTrendsOut(
        patient=LabTrendPatientOut(
            id=patient.id,
            mrn=patient.mrn,
            name=patient.full_name,
            birth_date=patient.birth_date,
        ),
        trends=trends,
    )

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import (
    Allergy,
    Encounter,
    Patient,
    Prescription,
    Role,
    SafetyAlert,
    SafetyAlertPriority,
    User,
)
from app.schemas.prescription import (
    AllergyConflictOut,
    PrescriptionCreate,
    PrescriptionCreateResponse,
    PrescriptionOut,
)
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.services.safety_rules import (
    AllergyConflictResult,
    AllergyEvidence,
    check_allergy_conflict,
)

router = APIRouter(prefix="/patients", tags=["prescriptions"])

_PATIENT_NOT_FOUND_MESSAGE = "환자를 찾을 수 없거나 조회할 수 없습니다."
_ENCOUNTER_NOT_FOUND_MESSAGE = "요청한 진료 기록을 찾을 수 없거나 사용할 수 없습니다."


def _create_safety_alert_if_missing(
    db: Session,
    encounter_id: int,
    prescription_id: int,
    conflict: AllergyConflictResult,
) -> SafetyAlert | None:
    """같은 (prescription_id, rule_id) 조합의 SafetyAlert가 이미 있으면 다시
    만들지 않는다 — 동일 Prescription에 대해 이 함수를 두 번 호출해도
    중복 경고가 쌓이지 않도록 하는 유일한 방어선(신규 DB 제약/Migration
    없음). 완전한 동시성 경쟁조건 방지는 이 프로토타입의 범위 밖이다."""
    existing = (
        db.query(SafetyAlert)
        .filter_by(prescription_id=prescription_id, rule_id=conflict.rule_id)
        .first()
    )
    if existing is not None:
        return None

    safety_alert = SafetyAlert(
        encounter_id=encounter_id,
        prescription_id=prescription_id,
        lab_result_id=None,
        rule_id=conflict.rule_id,
        evidence={
            "matched_allergy_id": conflict.matched_allergy_id,
            "matched_allergy_name": conflict.matched_allergy_name,
            "medication_name": conflict.medication_name,
            "explanation": conflict.explanation,
        },
        priority=SafetyAlertPriority.HIGH,
        created_at=datetime.now(timezone.utc),
    )
    db.add(safety_alert)
    db.flush()
    return safety_alert


@router.post(
    "/{patient_id}/prescriptions",
    response_model=PrescriptionCreateResponse,
    status_code=201,
)
def create_prescription(
    patient_id: int,
    body: PrescriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """처방 생성 + 알레르기-처방 문자열 충돌 확인. DOCTOR 전용이며, 미배정
    또는 존재하지 않는 patient_id는 Task 8과 동일하게 구분 없이 같은 404를
    반환한다(IDOR 방지, 최소 노출). 요청 body의 encounter_id가 URL의
    patient_id에 속하지 않으면(다른 환자의 Encounter 조작) 마찬가지로
    일반화된 404로 거부하고 아무것도 만들지 않는다.

    충돌이 있어도 Prescription은 항상 정상 저장한다 — 이 시스템은 경고만
    제공하며 처방을 자동 차단·변경·취소하지 않는다. 최종 판단은 언제나
    의료진이 수행한다.
    """
    patient = db.query(Patient).filter_by(id=patient_id).first()
    if patient is None or not can_access_patient(user, patient_id, db):
        raise HTTPException(status_code=404, detail=_PATIENT_NOT_FOUND_MESSAGE)

    encounter = db.query(Encounter).filter_by(id=body.encounter_id).first()
    if encounter is None or encounter.patient_id != patient_id:
        raise HTTPException(status_code=404, detail=_ENCOUNTER_NOT_FOUND_MESSAGE)

    try:
        prescription = Prescription(
            encounter_id=encounter.id,
            medication_name=body.medication_name,
            dosage=body.dosage,
            prescribed_by_user_id=user.id,
            prescribed_at=datetime.now(timezone.utc),
            source_type=body.source_type,
        )
        db.add(prescription)
        db.flush()

        allergies = db.query(Allergy).filter_by(patient_id=patient_id).all()
        allergy_evidence = [
            AllergyEvidence(allergy_id=allergy.id, allergy_name=allergy.substance)
            for allergy in allergies
        ]
        conflict = check_allergy_conflict(allergy_evidence, body.medication_name)

        safety_alert_created = False
        if conflict.has_conflict:
            safety_alert = _create_safety_alert_if_missing(
                db, encounter.id, prescription.id, conflict
            )
            safety_alert_created = safety_alert is not None

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="CREATE_PRESCRIPTION",
            resource_type="Prescription",
            resource_id=str(prescription.id),
            reason="assigned_patient_prescription",
            patient_id=patient_id,
        )
        if safety_alert_created:
            write_audit_log(
                db,
                actor_user_id=user.id,
                action="CREATE_SAFETY_ALERT",
                resource_type="SafetyAlert",
                resource_id=str(safety_alert.id),
                reason="allergy_medication_conflict",
                patient_id=patient_id,
            )

        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="처방 생성 중 오류가 발생했습니다.")

    return PrescriptionCreateResponse(
        prescription=PrescriptionOut(
            id=prescription.id,
            encounter_id=prescription.encounter_id,
            medication_name=prescription.medication_name,
            dosage=prescription.dosage,
            source_type=prescription.source_type.value,
            prescribed_by_user_id=prescription.prescribed_by_user_id,
        ),
        allergy_conflict=AllergyConflictOut(
            has_conflict=conflict.has_conflict,
            rule_id=conflict.rule_id,
            matched_allergy_id=conflict.matched_allergy_id,
            matched_allergy_name=conflict.matched_allergy_name,
            medication_name=conflict.medication_name,
            priority=conflict.priority,
            explanation=conflict.explanation,
        ),
        safety_alert_created=safety_alert_created,
    )

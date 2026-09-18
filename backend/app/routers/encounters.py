from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import (
    ClinicalNote,
    Department,
    Diagnosis,
    Encounter,
    EncounterType,
    LabResult,
    Patient,
    Prescription,
    Role,
    User,
)
from app.schemas.encounter import PatientTimelineOut, TimelineItemOut, TimelinePatientOut
from app.services.audit import write_audit_log
from app.services.authorization import can_access_patient
from app.utils.text import truncate_for_display as _truncate_for_display

router = APIRouter(prefix="/patients", tags=["encounters"])

_DEPARTMENT_LABELS = {
    Department.ENDOCRINOLOGY: "내분비내과",
    Department.ORTHOPEDICS: "정형외과",
    Department.EMERGENCY_MEDICINE: "응급의학과",
}

_ENCOUNTER_TYPE_LABELS = {
    EncounterType.OUTPATIENT: "외래",
    EncounterType.INPATIENT: "입원",
    EncounterType.EMERGENCY: "응급",
}


def _sort_key(item: TimelineItemOut) -> tuple:
    # 최신순: event_time DESC -> encounter_id DESC -> event_type ASC -> id DESC.
    # 내림차순이 필요한 숫자/시각 필드는 음수로 뒤집어 하나의 오름차순 정렬로
    # 처리한다 — 동일 시각이라도 항상 같은 순서가 되도록 결정적이다.
    return (-item.event_time.timestamp(), -item.encounter_id, item.event_type, -item.id)


@router.get("/{patient_id}/timeline", response_model=PatientTimelineOut)
def get_patient_timeline(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR)),
):
    """Encounter 중심 임상 타임라인. DOCTOR 전용이며, URL의 patient_id를
    사용자가 조작해도 매 요청마다 담당 관계(can_access_patient)를 다시
    검사한다(IDOR 방지). 전체 환자/전체 임상정보를 먼저 조회한 뒤 Python에서
    거르지 않고, 권한 확인 후 이 환자의 데이터만 DB에서 조회한다.

    존재하지 않는 patient_id와, 존재하지만 이 DOCTOR에게 배정되지 않은
    patient_id는 **의도적으로 같은 404 응답**을 반환한다 — 둘을 구분하면
    "이 patient_id는 실제로 존재한다"는 사실 자체가 새어나가기 때문이다.
    401(미인증)과 403(DOCTOR 이외 역할)은 이 구분과 무관하게 그대로 유지한다.
    """
    patient = db.query(Patient).filter_by(id=patient_id).first()
    if patient is None or not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=404, detail="환자를 찾을 수 없거나 조회할 수 없습니다."
        )

    encounters = db.query(Encounter).filter_by(patient_id=patient_id).all()
    encounter_ids = [encounter.id for encounter in encounters]
    department_by_encounter_id = {encounter.id: encounter.department for encounter in encounters}

    items: list[TimelineItemOut] = []

    for encounter in encounters:
        department_label = _DEPARTMENT_LABELS[encounter.department]
        type_label = _ENCOUNTER_TYPE_LABELS[encounter.encounter_type]
        items.append(
            TimelineItemOut(
                id=encounter.id,
                encounter_id=encounter.id,
                event_type="ENCOUNTER",
                event_time=encounter.start_time,
                title=f"{department_label} {type_label} 방문",
                summary=f"{department_label} {type_label} 방문 (합성 데이터)",
                source_type=None,  # Encounter 모델엔 source_type이 없다.
                department=department_label,
            )
        )

    if encounter_ids:
        for diagnosis in (
            db.query(Diagnosis).filter(Diagnosis.encounter_id.in_(encounter_ids)).all()
        ):
            department_label = _DEPARTMENT_LABELS[department_by_encounter_id[diagnosis.encounter_id]]
            items.append(
                TimelineItemOut(
                    id=diagnosis.id,
                    encounter_id=diagnosis.encounter_id,
                    event_type="DIAGNOSIS",
                    event_time=diagnosis.diagnosed_at,
                    title=diagnosis.description,
                    summary=f"진단 코드: {diagnosis.code}",
                    source_type=diagnosis.source_type.value,
                    department=department_label,
                )
            )

        for lab in db.query(LabResult).filter(LabResult.encounter_id.in_(encounter_ids)).all():
            department_label = _DEPARTMENT_LABELS[department_by_encounter_id[lab.encounter_id]]
            # Task 8은 DB에 저장된 값/단위/참고범위를 그대로 표시만 한다.
            # "참고범위 이탈"/HIGH/LOW 같은 판정은 절대 여기서 만들지 않는다 —
            # 그 판정은 Task 9의 evaluate_lab_abnormal() 중앙 규칙 함수가
            # 전담한다(LabResult.is_abnormal 컬럼은 이 응답에 포함하지 않음).
            items.append(
                TimelineItemOut(
                    id=lab.id,
                    encounter_id=lab.encounter_id,
                    event_type="LAB_RESULT",
                    event_time=lab.measured_at,
                    title=lab.test_name,
                    summary=(
                        f"{lab.value}{lab.unit} "
                        f"(참고범위 {lab.reference_low}-{lab.reference_high}{lab.unit})"
                    ),
                    source_type=lab.source_type.value,
                    department=department_label,
                )
            )

        for prescription in (
            db.query(Prescription).filter(Prescription.encounter_id.in_(encounter_ids)).all()
        ):
            department_label = _DEPARTMENT_LABELS[
                department_by_encounter_id[prescription.encounter_id]
            ]
            items.append(
                TimelineItemOut(
                    id=prescription.id,
                    encounter_id=prescription.encounter_id,
                    event_type="PRESCRIPTION",
                    event_time=prescription.prescribed_at,
                    title=prescription.medication_name,
                    summary=f"용량: {prescription.dosage}",
                    source_type=prescription.source_type.value,
                    department=department_label,
                )
            )

        for note in (
            db.query(ClinicalNote).filter(ClinicalNote.encounter_id.in_(encounter_ids)).all()
        ):
            department_label = _DEPARTMENT_LABELS[department_by_encounter_id[note.encounter_id]]
            items.append(
                TimelineItemOut(
                    id=note.id,
                    encounter_id=note.encounter_id,
                    event_type="CLINICAL_NOTE",
                    event_time=note.created_at,
                    title="진료기록",
                    summary=_truncate_for_display(note.note_text),
                    source_type=note.source_type.value,
                    department=department_label,
                )
            )

    items.sort(key=_sort_key)

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="READ_PATIENT_TIMELINE",
        resource_type="PatientTimeline",
        resource_id=str(patient_id),
        reason="assigned_patient_timeline",
        patient_id=patient_id,
    )
    db.commit()

    return PatientTimelineOut(
        patient=TimelinePatientOut(
            id=patient.id,
            mrn=patient.mrn,
            name=patient.full_name,
            birth_date=patient.birth_date,
        ),
        timeline=items,
    )

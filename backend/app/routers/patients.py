from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import Patient, PatientAssignment, Role, User
from app.schemas.patient import AssignedPatientOut
from app.services.audit import write_audit_log

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/assigned", response_model=list[AssignedPatientOut])
def list_assigned_patients(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DOCTOR, Role.NURSE)),
):
    """현재 로그인한 DOCTOR/NURSE에게 PatientAssignment로 배정된 환자만
    반환한다. 같은 진료과라는 이유로는 절대 포함되지 않는다 — 필터링은
    PatientAssignment.staff_user_id 조건으로 데이터베이스 쿼리 자체에서
    이루어지고, 전체 Patient를 먼저 불러온 뒤 Python에서 걸러내지 않는다.
    """
    rows = (
        db.query(Patient, PatientAssignment.assignment_role)
        .join(PatientAssignment, PatientAssignment.patient_id == Patient.id)
        .filter(PatientAssignment.staff_user_id == user.id)
        .order_by(Patient.mrn, Patient.id, PatientAssignment.id)
        .all()
    )

    # 같은 환자에게 중복 배정 행이 있어도 한 번만 포함한다. 정렬된 순서로
    # 순회하므로 "먼저 만난" assignment_role을 쓰는 것도 결정적이다.
    seen_patient_ids: set[int] = set()
    assigned_patients: list[AssignedPatientOut] = []
    for patient, assignment_role in rows:
        if patient.id in seen_patient_ids:
            continue
        seen_patient_ids.add(patient.id)
        assigned_patients.append(
            AssignedPatientOut(
                id=patient.id,
                mrn=patient.mrn,
                name=patient.full_name,
                birth_date=patient.birth_date,
                assignment_role=assignment_role.value,
            )
        )

    write_audit_log(
        db,
        actor_user_id=user.id,
        action="READ_ASSIGNED_PATIENTS",
        resource_type="PatientList",
        resource_id=str(user.id),
        reason="assigned_patient_list",
    )
    db.commit()

    return assigned_patients

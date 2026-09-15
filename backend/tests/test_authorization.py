from app.core.security import create_access_token
from app.models import Patient, Role, User
from app.services.authorization import can_access_patient
from scripts.seed_synthetic_data import seed

DOCTOR_EMAIL = "endocrine.doctor@example.test"
NURSE_EMAIL = "nurse1@example.test"
PATIENT_EMAIL = "patient1@example.test"
ADMIN_STAFF_EMAIL = "admin.staff@example.test"
SYSTEM_ADMIN_EMAIL = "system.admin@example.test"


def _user(db, email):
    return db.query(User).filter_by(email=email).first()


def _patient(db, mrn):
    return db.query(Patient).filter_by(mrn=mrn).first()


# 8. 허용된 역할은 require_roles 통과
def test_require_roles_allows_permitted_role(db_session, auth_test_client):
    seed(db_session)
    doctor = _user(db_session, DOCTOR_EMAIL)
    token = create_access_token(subject=str(doctor.id), role=doctor.role.value)

    response = auth_test_client.get(
        "/doctors-only", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


# 9. 허용되지 않은 역할은 require_roles에서 403
def test_require_roles_rejects_role_not_in_allow_list(db_session, auth_test_client):
    seed(db_session)
    patient_user = _user(db_session, PATIENT_EMAIL)
    token = create_access_token(subject=str(patient_user.id), role=patient_user.role.value)

    response = auth_test_client.get(
        "/doctors-only", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


# 10. PATIENT가 본인 환자정보 접근 성공
def test_patient_can_access_own_record(db_session):
    seed(db_session)
    patient_user = _user(db_session, PATIENT_EMAIL)

    assert can_access_patient(patient_user, patient_user.patient_id, db_session) is True


# 11. PATIENT가 다른 환자정보 접근 실패
def test_patient_cannot_access_another_patients_record(db_session):
    seed(db_session)
    patient_user = _user(db_session, PATIENT_EMAIL)
    other_patient = _patient(db_session, "SYN-0002")

    assert can_access_patient(patient_user, other_patient.id, db_session) is False


# 12. DOCTOR가 배정 환자 접근 성공
def test_doctor_can_access_assigned_patient(db_session):
    seed(db_session)
    doctor = _user(db_session, DOCTOR_EMAIL)
    assigned_patient = _patient(db_session, "SYN-0001")  # endocrine.doctor의 담당 환자

    assert can_access_patient(doctor, assigned_patient.id, db_session) is True


# 13. DOCTOR가 미배정 환자 접근 실패
def test_doctor_cannot_access_unassigned_patient(db_session):
    seed(db_session)
    doctor = _user(db_session, DOCTOR_EMAIL)
    unassigned_patient = _patient(db_session, "SYN-0002")  # 정형외과 의사 담당, 같은 의사 아님

    assert can_access_patient(doctor, unassigned_patient.id, db_session) is False


# 14. NURSE가 배정 환자 접근 성공
def test_nurse_can_access_assigned_patient(db_session):
    seed(db_session)
    nurse = _user(db_session, NURSE_EMAIL)
    assigned_patient = _patient(db_session, "SYN-0001")  # nurse1의 담당(PRIMARY_NURSE) 환자

    assert can_access_patient(nurse, assigned_patient.id, db_session) is True


# 15. NURSE가 미배정 환자 접근 실패
def test_nurse_cannot_access_unassigned_patient(db_session):
    seed(db_session)
    nurse = _user(db_session, NURSE_EMAIL)
    unassigned_patient = _patient(db_session, "SYN-0002")

    assert can_access_patient(nurse, unassigned_patient.id, db_session) is False


# 16. ADMIN_STAFF의 임상 환자 접근 실패 (진료과/배정과 무관하게 항상 거부)
def test_admin_staff_cannot_access_any_clinical_patient_data(db_session):
    seed(db_session)
    admin_staff = _user(db_session, ADMIN_STAFF_EMAIL)
    any_patient = _patient(db_session, "SYN-0001")

    assert can_access_patient(admin_staff, any_patient.id, db_session) is False


# 17. SYSTEM_ADMIN의 임상 환자 접근 실패
def test_system_admin_cannot_access_any_clinical_patient_data(db_session):
    seed(db_session)
    system_admin = _user(db_session, SYSTEM_ADMIN_EMAIL)
    any_patient = _patient(db_session, "SYN-0001")

    assert can_access_patient(system_admin, any_patient.id, db_session) is False


# 진료과가 같다는 이유만으로는 접근이 허용되지 않아야 한다 — PatientAssignment
# 관계가 실제로 있어야 한다 (같은 진료과의 다른 의사는 배정 전까지 접근 불가).
def test_same_department_alone_does_not_grant_access(db_session):
    from datetime import date

    seed(db_session)
    doctor = _user(db_session, DOCTOR_EMAIL)  # ENDOCRINOLOGY 소속

    from app.models import Department

    same_department_but_unassigned = Patient(
        mrn="SYN-9001", full_name="합성환자-미배정", birth_date=date(1999, 1, 1), sex="F"
    )
    db_session.add(same_department_but_unassigned)
    db_session.commit()

    assert doctor.department == Department.ENDOCRINOLOGY
    assert can_access_patient(doctor, same_department_but_unassigned.id, db_session) is False

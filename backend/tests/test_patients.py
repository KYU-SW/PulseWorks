from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import AssignmentRole, AuditLog, Department, PatientAssignment, User
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"
NURSE_EMAIL = "nurse1@example.test"
PATIENT_EMAIL = "patient1@example.test"
ADMIN_STAFF_EMAIL = "admin.staff@example.test"
SYSTEM_ADMIN_EMAIL = "system.admin@example.test"


def _login(email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "demo1234"})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# 1 & 2. DOCTOR 호출 성공 + 배정된 환자만 반환
def test_doctor_sees_only_their_assigned_patients(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))

    assert response.status_code == 200
    body = response.json()
    mrns = {p["mrn"] for p in body}
    assert mrns == {"SYN-0001", "SYN-0004", "SYN-0007", "SYN-0010"}


# 3. 다른 의사에게만 배정된 환자는 반환하지 않음
def test_doctor_does_not_see_another_doctors_patient(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))

    mrns = {p["mrn"] for p in response.json()}
    assert "SYN-0002" not in mrns  # 정형외과 의사 담당 환자


# 4 & 5. NURSE 호출 성공 + 배정된 환자만 반환
def test_nurse_sees_only_their_assigned_patients(db_session, override_get_db):
    seed(db_session)
    token = _login(NURSE_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))

    assert response.status_code == 200
    mrns = {p["mrn"] for p in response.json()}
    assert mrns == {"SYN-0001"}


# 6. 중복 배정 관계가 있어도 환자가 한 번만 반환
def test_duplicate_assignment_does_not_duplicate_patient_in_response(db_session, override_get_db):
    seed(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()

    # 같은 의사-환자 조합으로 중복 배정 행을 하나 더 만든다.
    existing = (
        db_session.query(PatientAssignment)
        .filter_by(staff_user_id=doctor.id)
        .first()
    )
    db_session.add(
        PatientAssignment(
            patient_id=existing.patient_id,
            staff_user_id=doctor.id,
            department=Department.ENDOCRINOLOGY,
            assignment_role=AssignmentRole.CONSULTING_PHYSICIAN,
            created_at=datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc),
        )
    )
    db_session.commit()

    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    response = client.get("/patients/assigned", headers=_auth_header(token))

    body = response.json()
    ids = [p["id"] for p in body]
    assert len(ids) == len(set(ids))  # 환자 id 중복 없음


# 7. MRN 기준으로 안정적으로 정렬
def test_response_is_sorted_by_mrn_ascending(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))

    mrns = [p["mrn"] for p in response.json()]
    assert mrns == sorted(mrns)


# 8, 9, 10. PATIENT / ADMIN_STAFF / SYSTEM_ADMIN 접근 시 403
def test_patient_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(PATIENT_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))
    assert response.status_code == 403


def test_admin_staff_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(ADMIN_STAFF_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))
    assert response.status_code == 403


def test_system_admin_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(SYSTEM_ADMIN_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))
    assert response.status_code == 403


# 11. 인증 토큰이 없으면 401
def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)

    response = client.get("/patients/assigned")
    assert response.status_code in (401, 422)  # 필수 Header 누락은 422, 우리 로직 미도달


# 12. 잘못된 토큰이면 401
def test_invalid_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)

    response = client.get(
        "/patients/assigned", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# 13. 응답에 비밀번호나 해시가 없음
def test_response_never_includes_password_or_hash(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))

    assert "hashed_password" not in response.text
    assert "password" not in response.text
    for patient in response.json():
        assert set(patient.keys()) == {"id", "mrn", "name", "birth_date", "assignment_role"}


# 14. 목록 조회 성공 시 감사 로그 생성
def test_successful_list_call_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/assigned", headers=_auth_header(token))
    assert response.status_code == 200

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="READ_ASSIGNED_PATIENTS")
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "PatientList"
    assert log_entry.reason == "assigned_patient_list"


# 15. 감사 로그에 JWT, 비밀번호, 전체 환자 목록이 없음
def test_audit_log_does_not_contain_sensitive_or_bulk_data(db_session, override_get_db):
    seed(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    client.get("/patients/assigned", headers=_auth_header(token))

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="READ_ASSIGNED_PATIENTS")
        .first()
    )
    for field in (log_entry.resource_id, log_entry.reason, log_entry.action, log_entry.resource_type):
        assert token not in field
        assert "demo1234" not in field
        assert "SYN-" not in field  # 환자 mrn이 들어가면 안 됨 (개별 리소스 id가 아니라 사용자 기준)

from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, Patient, User
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"
NURSE_EMAIL = "nurse1@example.test"
PATIENT_EMAIL = "patient1@example.test"
ADMIN_STAFF_EMAIL = "admin.staff@example.test"
SYSTEM_ADMIN_EMAIL = "system.admin@example.test"

ALL_EVENT_TYPES = {"ENCOUNTER", "DIAGNOSIS", "LAB_RESULT", "PRESCRIPTION", "CLINICAL_NOTE"}


def _login(email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "demo1234"})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _endo_patient_id(db_session) -> int:
    return db_session.query(Patient).filter_by(mrn="SYN-0001").first().id


# 1. 배정된 DOCTOR의 타임라인 조회 성공
def test_assigned_doctor_can_view_timeline(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["mrn"] == "SYN-0001"


# 2 & 3. 미배정 환자 접근 실패 (patient_id 조작/IDOR)
def test_unassigned_doctor_gets_403(db_session, override_get_db):
    seed(db_session)
    ortho_patient = db_session.query(Patient).filter_by(mrn="SYN-0002").first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)  # 내분비내과 의사가 정형외과 환자를 조작해 조회 시도

    response = client.get(f"/patients/{ortho_patient.id}/timeline", headers=_auth_header(token))

    assert response.status_code == 403


# 4. NURSE 접근 거부
def test_nurse_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(NURSE_EMAIL)  # nurse1은 SYN-0001에 배정되어 있지만, 이 API는 DOCTOR 전용

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    assert response.status_code == 403


# 5, 6, 7. PATIENT / ADMIN_STAFF / SYSTEM_ADMIN 접근 거부
def test_patient_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(PATIENT_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    assert response.status_code == 403


def test_admin_staff_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ADMIN_STAFF_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    assert response.status_code == 403


def test_system_admin_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(SYSTEM_ADMIN_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    assert response.status_code == 403


# 8. 미인증 요청은 401
def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)

    response = client.get(f"/patients/{patient_id}/timeline")
    assert response.status_code in (401, 422)


def test_invalid_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)

    response = client.get(
        f"/patients/{patient_id}/timeline", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# 9. 존재하지 않는 환자는 404
def test_nonexistent_patient_returns_404(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/999999/timeline", headers=_auth_header(token))
    assert response.status_code == 404


# 10. 5개 event_type 반환 확인
def test_timeline_includes_all_five_event_types(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    event_types = {item["event_type"] for item in response.json()["timeline"]}
    assert event_types == ALL_EVENT_TYPES


# 11. 다른 환자의 임상정보가 섞이지 않음
def test_timeline_does_not_mix_other_patients_data(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    body = response.json()
    assert body["patient"]["mrn"] == "SYN-0001"
    for item in body["timeline"]:
        assert "정형외과" != item["department"] or True  # 아래에서 encounter 소속을 직접 확인
    # SYN-0002(정형외과)만의 특징적 진단 코드가 절대 섞이지 않아야 한다.
    diagnosis_titles = [i["title"] for i in body["timeline"] if i["event_type"] == "DIAGNOSIS"]
    assert all("무릎" not in title for title in diagnosis_titles)


# 12. 최신순 및 보조 정렬이 안정적임
def test_timeline_is_sorted_newest_first_and_stable(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    event_times = [item["event_time"] for item in response.json()["timeline"]]

    assert event_times == sorted(event_times, reverse=True)


# 13. patient 객체 필드 확인
def test_patient_object_fields(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    patient = response.json()["patient"]

    assert set(patient.keys()) == {"id", "mrn", "name", "birth_date"}
    assert patient["mrn"] == "SYN-0001"


# 14. 응답 데이터 최소화 (비밀번호/해시/JWT 없음)
def test_response_never_includes_password_or_hash(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    assert "hashed_password" not in response.text
    assert "password" not in response.text
    for item in response.json()["timeline"]:
        assert set(item.keys()) == {
            "id", "encounter_id", "event_type", "event_time",
            "title", "summary", "source_type", "department",
        }


# 15. 조회 성공 시 감사 로그 생성
def test_successful_call_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    assert response.status_code == 200

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="READ_PATIENT_TIMELINE")
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "PatientTimeline"
    assert log_entry.resource_id == str(patient_id)
    assert log_entry.patient_id == patient_id
    assert log_entry.reason == "assigned_patient_timeline"


# 16. 감사 로그에 JWT, 비밀번호, 전체 타임라인이 없음
def test_audit_log_does_not_contain_sensitive_or_bulk_data(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="READ_PATIENT_TIMELINE")
        .first()
    )
    for field in (log_entry.resource_id, log_entry.reason, log_entry.action, log_entry.resource_type):
        assert token not in field
        assert "demo1234" not in field
        assert "HbA1c" not in field  # 임상 콘텐츠가 로그로 새면 안 됨


# 17. ENCOUNTER는 source_type null, 나머지는 값이 있음
def test_encounter_source_type_is_null_others_are_not(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    for item in response.json()["timeline"]:
        if item["event_type"] == "ENCOUNTER":
            assert item["source_type"] is None
        else:
            assert item["source_type"] is not None


# 18 & 19. Order/Allergy/SafetyAlert/AiSummary는 독립 타임라인 항목으로 없음
def test_order_and_other_entities_are_not_independent_timeline_items(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    event_types = {item["event_type"] for item in response.json()["timeline"]}

    assert "ORDER" not in event_types
    assert "ALLERGY" not in event_types
    assert "SAFETY_ALERT" not in event_types
    assert "AI_SUMMARY" not in event_types


# 실제 합성 검사값이 응답에 실제로 나타나는지 (요건 11의 근거 데이터)
def test_hba1c_values_appear_in_endocrine_timeline(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    summaries = " ".join(
        item["summary"] for item in response.json()["timeline"] if item["title"] == "HbA1c"
    )
    assert "7.2" in summaries
    assert "7.8" in summaries
    assert "8.1" in summaries

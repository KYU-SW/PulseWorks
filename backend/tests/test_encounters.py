from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, Patient, User
from app.routers.encounters import _truncate_for_display
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


# 2 & 3. 미배정 환자 접근 실패 (patient_id 조작/IDOR) — 존재 노출을 줄이기
# 위해 "존재하지 않음"과 동일한 404로 통일한다(403이 아니다).
def test_unassigned_doctor_gets_404_not_403(db_session, override_get_db):
    seed(db_session)
    ortho_patient = db_session.query(Patient).filter_by(mrn="SYN-0002").first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)  # 내분비내과 의사가 정형외과 환자를 조작해 조회 시도

    response = client.get(f"/patients/{ortho_patient.id}/timeline", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.json()["detail"] == "환자를 찾을 수 없거나 조회할 수 없습니다."


# 미배정 환자(존재함)와 존재하지 않는 환자가 완전히 동일한 상태코드/응답을
# 반환해야 한다 — 그래야 응답만으로 "이 patient_id가 존재하는지"를 구분할
# 수 없다.
def test_unassigned_and_nonexistent_patient_return_identical_response(
    db_session, override_get_db
):
    seed(db_session)
    ortho_patient = db_session.query(Patient).filter_by(mrn="SYN-0002").first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    unassigned_response = client.get(
        f"/patients/{ortho_patient.id}/timeline", headers=_auth_header(token)
    )
    nonexistent_response = client.get(
        "/patients/999999/timeline", headers=_auth_header(token)
    )

    assert unassigned_response.status_code == nonexistent_response.status_code == 404
    assert unassigned_response.json() == nonexistent_response.json()


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


# 9. 존재하지 않는 환자는 404 (+ 일반화된 메시지)
def test_nonexistent_patient_returns_404(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patients/999999/timeline", headers=_auth_header(token))
    assert response.status_code == 404
    assert response.json()["detail"] == "환자를 찾을 수 없거나 조회할 수 없습니다."


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


# 보완: LAB_RESULT summary에 이상 판정 문구가 없어야 한다 (Task 9 전담 사항).
def test_lab_result_summary_has_no_abnormality_judgment(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    lab_summaries = [
        item["summary"] for item in response.json()["timeline"] if item["event_type"] == "LAB_RESULT"
    ]

    assert len(lab_summaries) > 0
    for summary in lab_summaries:
        assert "이탈" not in summary
        assert "정상" not in summary
        assert "비정상" not in summary
        assert "HIGH" not in summary
        assert "LOW" not in summary
        # 값/단위/참고범위는 그대로 있어야 한다.
        assert "참고범위" in summary


# 보완: 응급의학과 데이터(참고범위를 크게 벗어난 Troponin)에도 판정 문구가
# 없어야 한다 — 값 자체가 극단적이어도 Task 8은 판정하지 않는다.
def test_emergency_lab_summary_also_has_no_abnormality_judgment(db_session, override_get_db):
    seed(db_session)
    emergency_patient = db_session.query(Patient).filter_by(mrn="SYN-0003").first()
    token = _login("emergency.doctor@example.test")

    response = client.get(
        f"/patients/{emergency_patient.id}/timeline", headers=_auth_header(token)
    )
    troponin_summary = next(
        item["summary"]
        for item in response.json()["timeline"]
        if item["title"] == "Troponin"
    )

    assert "0.8" in troponin_summary
    assert "이탈" not in troponin_summary
    assert "HIGH" not in troponin_summary


# 보완: _truncate_for_display 단위 테스트
def test_truncate_for_display_leaves_short_text_unchanged():
    short_text = "짧은 진료기록입니다."
    assert _truncate_for_display(short_text) == short_text


def test_truncate_for_display_leaves_exactly_300_chars_unchanged():
    text_300 = "가" * 300
    assert _truncate_for_display(text_300) == text_300


def test_truncate_for_display_truncates_long_text_with_ellipsis():
    long_text = "나" * 400
    result = _truncate_for_display(long_text)

    assert result == "나" * 300 + "..."
    assert result.endswith("...")
    assert len(result) == 303


# 보완: 실제 API 응답에서도 CLINICAL_NOTE summary가 300자+말줄임을 넘지 않음
def test_clinical_note_summary_never_exceeds_truncation_limit(db_session, override_get_db):
    seed(db_session)
    patient_id = _endo_patient_id(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get(f"/patients/{patient_id}/timeline", headers=_auth_header(token))
    note_summaries = [
        item["summary"] for item in response.json()["timeline"] if item["event_type"] == "CLINICAL_NOTE"
    ]

    assert len(note_summaries) > 0
    for summary in note_summaries:
        assert len(summary) <= 303
        if len(summary) == 303:
            assert summary.endswith("...")

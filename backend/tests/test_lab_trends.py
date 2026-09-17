from app.main import app
from app.models import AuditLog, Patient, User
from app.services.safety_rules import evaluate_lab_abnormal
from fastapi.testclient import TestClient
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"
EMERGENCY_DOCTOR_EMAIL = "emergency.doctor@example.test"
NURSE_EMAIL = "nurse1@example.test"
PATIENT_EMAIL = "patient1@example.test"
ADMIN_STAFF_EMAIL = "admin.staff@example.test"
SYSTEM_ADMIN_EMAIL = "system.admin@example.test"


def _login(email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "demo1234"})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _patient_id(db_session, mrn: str) -> int:
    return db_session.query(Patient).filter_by(mrn=mrn).first().id


def _get_trends(patient_id: int, token: str):
    return client.get(f"/patients/{patient_id}/lab-trends", headers=_auth_header(token))


def _group(body: dict, test_name: str) -> dict:
    return next(g for g in body["trends"] if g["test_name"] == test_name)


# 1. 담당 의사의 정상 조회
def test_assigned_doctor_can_view_lab_trends(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)

    assert response.status_code == 200
    assert response.json()["patient"]["mrn"] == "SYN-0001"


# 2 & 미배정/미존재 동일 404
def test_unassigned_doctor_gets_404_not_403(db_session, override_get_db):
    seed(db_session)
    ortho_patient_id = _patient_id(db_session, "SYN-0002")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(ortho_patient_id, token)

    assert response.status_code == 404
    assert response.json()["detail"] == "환자를 찾을 수 없거나 조회할 수 없습니다."


def test_unassigned_and_nonexistent_patient_return_identical_response(db_session, override_get_db):
    seed(db_session)
    ortho_patient_id = _patient_id(db_session, "SYN-0002")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    unassigned = _get_trends(ortho_patient_id, token)
    nonexistent = _get_trends(999999, token)

    assert unassigned.status_code == nonexistent.status_code == 404
    assert unassigned.json() == nonexistent.json()


def test_nonexistent_patient_returns_404(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(999999, token)
    assert response.status_code == 404


# 3. 다른 역할 접근 차단
def test_nurse_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(NURSE_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 403


def test_patient_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(PATIENT_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 403


def test_admin_staff_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ADMIN_STAFF_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 403


def test_system_admin_forbidden(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(SYSTEM_ADMIN_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 403


def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")

    response = client.get(f"/patients/{patient_id}/lab-trends")
    assert response.status_code in (401, 422)


def test_invalid_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")

    response = client.get(
        f"/patients/{patient_id}/lab-trends", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# 4. 다른 환자 데이터 미혼합
def test_does_not_mix_other_patients_data(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    body = response.json()

    test_names = {g["test_name"] for g in body["trends"]}
    assert "Heart Rate" not in test_names  # SYN-0003 소속
    assert "Troponin" not in test_names  # SYN-0003 소속


# 5. 검사명/단위 그룹화 — 서로 다른 test_name은 분리된 그룹
def test_groups_by_test_name_and_unit(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    body = response.json()
    test_names = [g["test_name"] for g in body["trends"]]

    assert len(test_names) == len(set(test_names))  # 그룹당 test_name 중복 없음
    assert "HbA1c" in test_names
    assert "Fasting Glucose" in test_names
    assert "자가측정 혈당 (합성 데이터, 환자 입력)" in test_names  # 다른 test_name -> 별도 그룹

    hba1c_group = _group(body, "HbA1c")
    assert hba1c_group["unit"] == "%"
    assert all(point["unit"] == "%" for point in hba1c_group["points"])


# 6. 시간순 정렬
def test_points_are_sorted_ascending_by_measured_at(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    hba1c_group = _group(response.json(), "HbA1c")
    measured_times = [p["measured_at"] for p in hba1c_group["points"]]

    assert measured_times == sorted(measured_times)
    assert [p["value"] for p in hba1c_group["points"]] == [7.2, 7.8, 8.1]


def test_fasting_glucose_values_and_order(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    glucose_group = _group(response.json(), "Fasting Glucose")

    assert [p["value"] for p in glucose_group["points"]] == [130, 145, 160]


# 7. evaluate_lab_abnormal() 결과 일치
def test_status_matches_evaluate_lab_abnormal(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    hba1c_group = _group(response.json(), "HbA1c")

    for point in hba1c_group["points"]:
        expected = evaluate_lab_abnormal(
            point["value"], point["reference_low"], point["reference_high"], point["unit"]
        )
        assert point["status"] == expected.status.value
        assert point["rule_id"] == expected.rule_id


# 8. 0건, 1건, 여러 건 처리
def test_patient_with_no_lab_results_returns_empty_trends(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0002")  # 정형외과: LabResult 없음(X-ray는 Order+Note)
    token = _login(ORTHOPEDIC_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 200
    assert response.json()["trends"] == []


def test_single_measurement_test_has_exactly_one_point(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0003")
    token = _login(EMERGENCY_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    body = response.json()
    heart_rate_group = _group(body, "Heart Rate")
    troponin_group = _group(body, "Troponin")

    assert len(heart_rate_group["points"]) == 1
    assert heart_rate_group["points"][0]["value"] == 118.0
    assert len(troponin_group["points"]) == 1
    assert troponin_group["points"][0]["value"] == 0.8


def test_multiple_measurement_test_has_all_points(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    hba1c_group = _group(response.json(), "HbA1c")
    assert len(hba1c_group["points"]) == 3


# 응답 필드 최소화 확인
def test_point_fields_are_exactly_the_specified_set(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    hba1c_group = _group(response.json(), "HbA1c")

    for point in hba1c_group["points"]:
        assert set(point.keys()) == {
            "value", "unit", "reference_low", "reference_high", "measured_at",
            "status", "rule_id", "encounter_id", "source_type",
        }
    assert "hashed_password" not in response.text
    assert "password" not in response.text


# encounter_id/source_type 값 확인 (PATIENT_REPORTED 자가측정값)
def test_patient_reported_point_has_correct_source_type(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    self_reported_group = _group(response.json(), "자가측정 혈당 (합성 데이터, 환자 입력)")

    assert len(self_reported_group["points"]) == 1
    assert self_reported_group["points"][0]["source_type"] == "PATIENT_REPORTED"


# 9. 감사 로그
def test_successful_call_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    patient_id = _patient_id(db_session, "SYN-0001")
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _get_trends(patient_id, token)
    assert response.status_code == 200

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="READ_LAB_TRENDS")
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "LabTrends"
    assert log_entry.resource_id == str(patient_id)
    assert log_entry.patient_id == patient_id
    assert log_entry.reason == "assigned_patient_lab_trends"

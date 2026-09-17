import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, Encounter, Patient, Prescription, SafetyAlert, User
from app.routers import prescriptions as prescriptions_router
from app.services.safety_rules import AllergyConflictResult
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


def _endo_patient(db_session) -> Patient:
    return db_session.query(Patient).filter_by(mrn="SYN-0001").first()


def _ortho_patient(db_session) -> Patient:
    return db_session.query(Patient).filter_by(mrn="SYN-0002").first()


def _endo_encounter_id(db_session) -> int:
    patient = _endo_patient(db_session)
    return db_session.query(Encounter).filter_by(patient_id=patient.id).first().id


def _post(url_patient_id: int, token: str, **body_overrides) -> "Response":
    body = {
        "encounter_id": body_overrides.pop("encounter_id"),
        "medication_name": body_overrides.pop("medication_name", "Metformin"),
        "dosage": body_overrides.pop("dosage", "500mg"),
    }
    body.update(body_overrides)
    return client.post(
        f"/patients/{url_patient_id}/prescriptions", json=body, headers=_auth_header(token)
    )


# 1, 2, 3, 4. 담당 DOCTOR가 충돌 없는 처방 생성 성공 -> 201, SafetyAlert 없음, 로그 1건만
def test_non_conflicting_prescription_succeeds_without_safety_alert(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Ibuprofen")

    assert response.status_code == 201
    body = response.json()
    assert body["allergy_conflict"]["has_conflict"] is False
    assert body["safety_alert_created"] is False

    prescription_id = body["prescription"]["id"]
    assert db_session.query(SafetyAlert).filter_by(prescription_id=prescription_id).first() is None

    logs = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, resource_id=str(prescription_id)
    ).all()
    assert {log.action for log in logs} == {"CREATE_PRESCRIPTION"}


# 5, 6, 7, 8, 9, 10, 11, 12, 13. 충돌하는 처방 생성 -> 201 저장 + SafetyAlert 생성
def test_conflicting_prescription_still_succeeds_and_creates_safety_alert(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")

    assert response.status_code == 201
    body = response.json()
    assert body["allergy_conflict"]["has_conflict"] is True
    assert body["allergy_conflict"]["priority"] == "HIGH"
    assert body["safety_alert_created"] is True

    prescription_id = body["prescription"]["id"]
    assert db_session.query(Prescription).filter_by(id=prescription_id).first() is not None

    alert = db_session.query(SafetyAlert).filter_by(prescription_id=prescription_id).first()
    assert alert is not None
    assert alert.encounter_id == encounter_id
    assert alert.lab_result_id is None
    assert alert.rule_id == "ALLERGY_MEDICATION_CONFLICT"


# 14. 동일 Prescription에 동일 rule_id의 Alert는 최대 1개
def test_calling_alert_creation_twice_for_same_prescription_does_not_duplicate(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")
    prescription_id = response.json()["prescription"]["id"]

    conflict = AllergyConflictResult(
        has_conflict=True,
        rule_id="ALLERGY_MEDICATION_CONFLICT",
        matched_allergy_id=1,
        matched_allergy_name="Penicillin",
        medication_name="Penicillin V",
        priority="HIGH",
        explanation="테스트용 재호출",
    )
    second_call_result = prescriptions_router._create_safety_alert_if_missing(
        db_session, encounter_id, prescription_id, conflict
    )
    db_session.commit()

    assert second_call_result is None
    alerts = db_session.query(SafetyAlert).filter_by(prescription_id=prescription_id).all()
    assert len(alerts) == 1


# 15. 서로 다른 Prescription이면 각각 Alert 생성 가능
def test_different_prescriptions_can_each_get_their_own_alert(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    first = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")
    second = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin VK")

    assert first.json()["safety_alert_created"] is True
    assert second.json()["safety_alert_created"] is True
    assert first.json()["prescription"]["id"] != second.json()["prescription"]["id"]

    alerts = db_session.query(SafetyAlert).filter(
        SafetyAlert.prescription_id.in_(
            [first.json()["prescription"]["id"], second.json()["prescription"]["id"]]
        )
    ).all()
    assert len(alerts) == 2


# 16. prescribed_by_user_id가 현재 로그인 의사 ID
def test_prescribed_by_user_id_is_current_doctor(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id)

    assert response.json()["prescription"]["prescribed_by_user_id"] == doctor.id


# 17. 요청 body로 prescribed_by_user_id를 보내면 422
def test_client_supplied_prescribed_by_user_id_is_rejected(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(
        patient.id, token, encounter_id=encounter_id, prescribed_by_user_id=999999
    )
    assert response.status_code == 422


# 18. 요청 body로 patient_id를 보내면 422
def test_client_supplied_patient_id_in_body_is_rejected(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, patient_id=999999)
    assert response.status_code == 422


# 19. 요청 body로 SafetyAlert 필드를 보내면 422
def test_client_supplied_safety_alert_fields_are_rejected(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, priority="HIGH")
    assert response.status_code == 422


# 20. medication_name이 공백이면 422
def test_blank_medication_name_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="   ")
    assert response.status_code == 422


# 21. dosage가 공백이면 422
def test_blank_dosage_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, dosage="  ")
    assert response.status_code == 422


# 22. 존재하지 않는 encounter_id는 일반화된 404
def test_nonexistent_encounter_id_returns_404(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _post(patient.id, token, encounter_id=999999)
    assert response.status_code == 404


# 23. 다른 환자의 encounter_id를 사용하면 일반화된 404 (Encounter 조작 방지)
def test_other_patients_encounter_id_returns_404(db_session, override_get_db):
    seed(db_session)
    endo_patient = _endo_patient(db_session)
    ortho_patient = _ortho_patient(db_session)
    ortho_encounter_id = (
        db_session.query(Encounter).filter_by(patient_id=ortho_patient.id).first().id
    )
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    before = db_session.query(Prescription).filter_by(encounter_id=ortho_encounter_id).count()

    response = _post(endo_patient.id, token, encounter_id=ortho_encounter_id)

    assert response.status_code == 404
    after = db_session.query(Prescription).filter_by(encounter_id=ortho_encounter_id).count()
    assert after == before


# 24, 25, 26. 미배정·미존재 환자는 동일한 404
def test_unassigned_and_nonexistent_patient_return_identical_404(db_session, override_get_db):
    seed(db_session)
    ortho_patient = _ortho_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)  # 내분비내과 의사가 정형외과 환자를 조작
    ortho_encounter_id = (
        db_session.query(Encounter).filter_by(patient_id=ortho_patient.id).first().id
    )

    unassigned_response = _post(ortho_patient.id, token, encounter_id=ortho_encounter_id)
    nonexistent_response = _post(999999, token, encounter_id=ortho_encounter_id)

    assert unassigned_response.status_code == nonexistent_response.status_code == 404
    assert unassigned_response.json() == nonexistent_response.json()


# 27, 28, 29, 30. NURSE / PATIENT / ADMIN_STAFF / SYSTEM_ADMIN 접근 거부
@pytest.mark.parametrize(
    "email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL]
)
def test_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _endo_encounter_id(db_session)
    token = _login(email)

    response = _post(patient.id, token, encounter_id=encounter_id)
    assert response.status_code == 403


# 31. 인증 토큰이 없으면 401
def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _endo_encounter_id(db_session)

    response = client.post(
        f"/patients/{patient.id}/prescriptions",
        json={"encounter_id": encounter_id, "medication_name": "Metformin", "dosage": "500mg"},
    )
    assert response.status_code in (401, 422)


# 32. 변조된 JWT면 401
def test_tampered_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, "not-a-real-token", encounter_id=encounter_id)
    assert response.status_code == 401


# 33. 응답에 password와 hashed_password가 없음
def test_response_never_includes_password_or_hash(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id)
    assert "hashed_password" not in response.text
    assert "password" not in response.text


# 34. 응답에 JWT와 JWT_SECRET이 없음
def test_response_never_includes_jwt_or_secret(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id)
    assert token not in response.text
    assert "JWT_SECRET" not in response.text


# 35. 다른 환자의 Allergy 정보가 응답/충돌판정에 섞이지 않음
def test_other_patients_allergy_does_not_affect_conflict_check(db_session, override_get_db):
    seed(db_session)
    ortho_patient = _ortho_patient(db_session)  # SYN-0002: Allergy 없음 (Penicillin은 SYN-0001 소유)
    ortho_encounter_id = (
        db_session.query(Encounter).filter_by(patient_id=ortho_patient.id).first().id
    )
    token = _login(ORTHOPEDIC_DOCTOR_EMAIL)

    response = _post(
        ortho_patient.id, token, encounter_id=ortho_encounter_id, medication_name="Penicillin V"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["allergy_conflict"]["has_conflict"] is False
    assert body["safety_alert_created"] is False
    assert "Penicillin" not in response.text.replace("Penicillin V", "")


# 36. 충돌 시 CREATE_SAFETY_ALERT 감사 로그 생성
def test_conflict_writes_safety_alert_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")
    prescription_id = response.json()["prescription"]["id"]

    alert_log = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="CREATE_SAFETY_ALERT", patient_id=patient.id
    ).order_by(AuditLog.id.desc()).first()

    assert alert_log is not None
    assert alert_log.resource_type == "SafetyAlert"
    assert alert_log.reason == "allergy_medication_conflict"

    prescription_log = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="CREATE_PRESCRIPTION", resource_id=str(prescription_id)
    ).first()
    assert prescription_log is not None
    assert prescription_log.reason == "assigned_patient_prescription"


# 37. 감사 로그에 JWT·비밀번호·요청 body 전체가 없음
def test_audit_log_does_not_contain_sensitive_or_bulk_data(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")

    logs = db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).all()
    for log in logs:
        for field in (log.resource_id, log.reason, log.action, log.resource_type):
            assert token not in field
            assert "demo1234" not in field


# 38, 39, 40. 검증 실패 시 Prescription/SafetyAlert/감사 로그가 남지 않음
def test_encounter_mismatch_leaves_no_prescription_alert_or_audit_log(
    db_session, override_get_db
):
    seed(db_session)
    endo_patient = _endo_patient(db_session)
    ortho_patient = _ortho_patient(db_session)
    ortho_encounter_id = (
        db_session.query(Encounter).filter_by(patient_id=ortho_patient.id).first().id
    )
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    before_prescriptions = db_session.query(Prescription).count()
    before_alerts = db_session.query(SafetyAlert).count()
    before_logs = db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).count()

    response = _post(endo_patient.id, token, encounter_id=ortho_encounter_id)
    assert response.status_code == 404

    assert db_session.query(Prescription).count() == before_prescriptions
    assert db_session.query(SafetyAlert).count() == before_alerts
    assert db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).count() == before_logs


# 트랜잭션 원자성: 감사 로그 작성 단계에서 예상치 못한 오류가 나면 전체 rollback
def test_unexpected_failure_during_audit_log_rolls_back_everything(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    before_prescriptions = db_session.query(Prescription).count()
    before_alerts = db_session.query(SafetyAlert).count()
    before_logs = db_session.query(AuditLog).count()

    def _broken_write_audit_log(*args, **kwargs):
        raise RuntimeError("의도적으로 주입한 오류 (테스트 전용)")

    monkeypatch.setattr(prescriptions_router, "write_audit_log", _broken_write_audit_log)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")

    assert response.status_code == 500
    assert db_session.query(Prescription).count() == before_prescriptions
    assert db_session.query(SafetyAlert).count() == before_alerts
    assert db_session.query(AuditLog).count() == before_logs


# 500 응답에 내부 예외/SQL이 노출되지 않음
def test_500_response_does_not_leak_internal_exception_details(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _endo_encounter_id(db_session)

    def _broken_write_audit_log(*args, **kwargs):
        raise RuntimeError("SELECT * FROM users WHERE secret_column = 1")

    monkeypatch.setattr(prescriptions_router, "write_audit_log", _broken_write_audit_log)

    response = _post(patient.id, token, encounter_id=encounter_id, medication_name="Penicillin V")

    assert response.status_code == 500
    assert "SELECT" not in response.text
    assert "secret_column" not in response.text

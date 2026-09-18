from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    AssignmentRole,
    AuditLog,
    ClinicalReport,
    Department,
    Encounter,
    Patient,
    PatientAssignment,
    User,
)
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


def _first_encounter_id(db_session, patient_id: int) -> int:
    return (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .first()
        .id
    )


def _post_report(patient_id: int, token: str, **overrides) -> "Response":
    body = {
        "report_type": "DOCTOR_REFERENCE",
        "scope_type": "SINGLE_ENCOUNTER",
        "encounter_ids": overrides.pop("encounter_ids"),
    }
    body.update(overrides)
    return client.post(
        f"/patients/{patient_id}/reports", json=body, headers=_auth_header(token)
    )


def _assign_second_doctor(db_session, patient_id: int, doctor: User) -> None:
    db_session.add(
        PatientAssignment(
            patient_id=patient_id,
            staff_user_id=doctor.id,
            department=Department.ENDOCRINOLOGY,
            assignment_role=AssignmentRole.CONSULTING_PHYSICIAN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    db_session.commit()


# 18, 19, 20, 21, 22, 23. 담당 DOCTOR 생성 성공
def test_assigned_doctor_creates_draft_report_with_snapshot(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)

    response = _post_report(patient.id, token, encounter_ids=[encounter_id])

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["created_by_user_id"] == doctor.id
    assert body["last_modified_by_user_id"] == doctor.id
    assert body["encounter_id"] == encounter_id
    assert body["scope_encounter_ids"] == [encounter_id]
    assert body["content"]["emr_snapshot"]["patient"]["mrn"] == "SYN-0001"
    assert len(body["content"]["emr_snapshot"]["diagnoses"]) == 1
    assert body["content"]["narrative"] is None
    assert body["reviewed_by_user_id"] is None
    assert body["supersedes_report_id"] is None


# 24, 25, 26, 27. 동일 DRAFT 재요청 시 재사용
def test_duplicate_request_reuses_existing_draft(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)

    first = _post_report(patient.id, token, encounter_ids=[encounter_id])
    before_count = db_session.query(ClinicalReport).count()
    before_logs = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="CREATE_REPORT"
    ).count()

    second = _post_report(patient.id, token, encounter_ids=[encounter_id])

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert db_session.query(ClinicalReport).count() == before_count
    after_logs = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="CREATE_REPORT"
    ).count()
    assert after_logs == before_logs


# 28. 다른 담당 의사는 별도 DRAFT 생성 가능
def test_different_assigned_doctor_gets_separate_draft(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    second_doctor = db_session.query(User).filter_by(email=ORTHOPEDIC_DOCTOR_EMAIL).first()
    _assign_second_doctor(db_session, patient.id, second_doctor)
    encounter_id = _first_encounter_id(db_session, patient.id)

    first_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    second_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)

    first = _post_report(patient.id, first_token, encounter_ids=[encounter_id])
    second = _post_report(patient.id, second_token, encounter_ids=[encounter_id])

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


# 29, 30, 31, 32. 역할별 403
@pytest.mark.parametrize(
    "email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL]
)
def test_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)
    token = _login(email)

    response = _post_report(patient.id, token, encounter_ids=[encounter_id])
    assert response.status_code == 403


# 33. 미인증 401
def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)

    response = client.post(
        f"/patients/{patient.id}/reports",
        json={
            "report_type": "DOCTOR_REFERENCE",
            "scope_type": "SINGLE_ENCOUNTER",
            "encounter_ids": [encounter_id],
        },
    )
    assert response.status_code in (401, 422)


def test_tampered_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)

    response = _post_report(patient.id, "not-a-real-token", encounter_ids=[encounter_id])
    assert response.status_code == 401


# 34. 미배정·미존재 환자 동일 404
def test_unassigned_and_nonexistent_patient_return_identical_404(db_session, override_get_db):
    seed(db_session)
    ortho_patient = _ortho_patient(db_session)
    ortho_encounter_id = _first_encounter_id(db_session, ortho_patient.id)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    unassigned = _post_report(ortho_patient.id, token, encounter_ids=[ortho_encounter_id])
    nonexistent = _post_report(999999, token, encounter_ids=[ortho_encounter_id])

    assert unassigned.status_code == nonexistent.status_code == 404
    assert unassigned.json() == nonexistent.json()
    assert unassigned.json()["detail"] == "환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다."


# 35. Encounter 없음과 다른 환자 Encounter 동일 404
def test_nonexistent_and_other_patients_encounter_return_identical_404(
    db_session, override_get_db
):
    seed(db_session)
    endo_patient = _endo_patient(db_session)
    ortho_patient = _ortho_patient(db_session)
    ortho_encounter_id = _first_encounter_id(db_session, ortho_patient.id)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    nonexistent_encounter = _post_report(endo_patient.id, token, encounter_ids=[999999])
    other_patients_encounter = _post_report(
        endo_patient.id, token, encounter_ids=[ortho_encounter_id]
    )

    assert nonexistent_encounter.status_code == other_patients_encounter.status_code == 404
    assert nonexistent_encounter.json() == other_patients_encounter.json()


# 36. encounter_ids 0개 또는 2개 이상 422
def test_zero_encounter_ids_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _post_report(patient.id, token, encounter_ids=[])
    assert response.status_code == 422


def test_multiple_encounter_ids_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounters = (
        db_session.query(Encounter).filter_by(patient_id=patient.id).order_by(Encounter.start_time).all()
    )

    response = _post_report(patient.id, token, encounter_ids=[encounters[0].id, encounters[1].id])
    assert response.status_code == 422


# 37. 지원하지 않는 report_type 422
def test_unsupported_report_type_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _post_report(
        patient.id, token, encounter_ids=[encounter_id], report_type="HANDOFF"
    )
    assert response.status_code == 422


# 38. 지원하지 않는 scope_type 422
def test_unsupported_scope_type_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _post_report(
        patient.id, token, encounter_ids=[encounter_id], scope_type="FULL_HISTORY"
    )
    assert response.status_code == 422


# 39. extra 필드 422
def test_extra_field_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    encounter_id = _first_encounter_id(db_session, patient.id)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = _post_report(
        patient.id, token, encounter_ids=[encounter_id], status="APPROVED"
    )
    assert response.status_code == 422


# 40. CREATE_REPORT 감사 로그
def test_create_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)

    response = _post_report(patient.id, token, encounter_ids=[encounter_id])
    report_id = response.json()["id"]

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="CREATE_REPORT", resource_id=str(report_id))
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "ClinicalReport"
    assert log_entry.patient_id == patient.id
    assert log_entry.reason == "single_encounter_report_created"


# 41, 45, 46. 담당 DOCTOR 조회 성공, 저장된 스냅샷 반환, 재수집 안 함
def test_assigned_doctor_can_view_report(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)

    created = _post_report(patient.id, token, encounter_ids=[encounter_id])
    report_id = created.json()["id"]

    response = client.get(f"/reports/{report_id}", headers=_auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == report_id
    assert body["content"] == created.json()["content"]  # 저장된 스냅샷 그대로


# 42. 다른 담당 DOCTOR도 조회 가능
def test_another_assigned_doctor_can_also_view_report(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    second_doctor = db_session.query(User).filter_by(email=ORTHOPEDIC_DOCTOR_EMAIL).first()
    _assign_second_doctor(db_session, patient.id, second_doctor)
    encounter_id = _first_encounter_id(db_session, patient.id)

    creator_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    viewer_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)

    created = _post_report(patient.id, creator_token, encounter_ids=[encounter_id])
    report_id = created.json()["id"]

    response = client.get(f"/reports/{report_id}", headers=_auth_header(viewer_token))
    assert response.status_code == 200
    assert response.json()["id"] == report_id


# 43. 미배정 DOCTOR는 동일 404 & 44. 없는 report ID도 동일 404
def test_unassigned_doctor_and_nonexistent_report_return_identical_404(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    creator_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _post_report(patient.id, creator_token, encounter_ids=[encounter_id])
    report_id = created.json()["id"]

    unassigned_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)  # SYN-0001에 미배정
    unassigned_response = client.get(
        f"/reports/{report_id}", headers=_auth_header(unassigned_token)
    )
    nonexistent_response = client.get(
        "/reports/999999", headers=_auth_header(creator_token)
    )

    assert unassigned_response.status_code == nonexistent_response.status_code == 404
    assert unassigned_response.json() == nonexistent_response.json()
    assert (
        unassigned_response.json()["detail"]
        == "환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다."
    )


# 47. VIEW_REPORT 감사 로그 1건
def test_view_writes_exactly_one_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _post_report(patient.id, token, encounter_ids=[encounter_id])
    report_id = created.json()["id"]

    client.get(f"/reports/{report_id}", headers=_auth_header(token))

    logs = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="VIEW_REPORT", resource_id=str(report_id)
    ).all()
    assert len(logs) == 1
    assert logs[0].resource_type == "ClinicalReport"
    assert logs[0].reason == "assigned_patient_report_view"


# 48. 응답과 감사 로그에 비밀정보 없음
def test_response_and_audit_log_never_contain_secrets(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)

    created = _post_report(patient.id, token, encounter_ids=[encounter_id])
    report_id = created.json()["id"]
    get_response = client.get(f"/reports/{report_id}", headers=_auth_header(token))

    assert "hashed_password" not in created.text
    assert "hashed_password" not in get_response.text
    assert token not in created.text
    assert token not in get_response.text

    logs = db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).all()
    for log in logs:
        for field in (log.resource_id, log.reason, log.action, log.resource_type):
            assert token not in field
            assert "demo1234" not in field

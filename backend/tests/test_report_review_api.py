from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, ClinicalReport, ClinicalReportStatus, Encounter, Patient, User
from app.routers import clinical_reports as clinical_reports_router
from scripts.seed_synthetic_data import seed

client = TestClient(app)


def _same_instant(a: str, b: str) -> bool:
    # SQLite는 재조회 시 timezone 오프셋을 보존하지 않는다(conftest.py 설명
    # 참고) — naive/aware 표기 차이가 아니라 실제 시각이 같은지로 비교한다.
    return datetime.fromisoformat(a).replace(tzinfo=None) == datetime.fromisoformat(b).replace(
        tzinfo=None
    )

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


def _first_encounter_id(db_session, patient_id: int) -> int:
    return (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .first()
        .id
    )


def _create_report(token: str, patient_id: int, encounter_id: int) -> dict:
    response = client.post(
        f"/patients/{patient_id}/reports",
        json={
            "report_type": "DOCTOR_REFERENCE",
            "scope_type": "SINGLE_ENCOUNTER",
            "encounter_ids": [encounter_id],
        },
        headers=_auth_header(token),
    )
    return response.json()


def _generate_narrative(report_id: int, token: str) -> dict:
    return client.post(
        f"/reports/{report_id}/generate-narrative", headers=_auth_header(token)
    ).json()


def _patch(report_id: int, token: str, body: dict):
    return client.patch(f"/reports/{report_id}", json=body, headers=_auth_header(token))


def _approve(report_id: int, token: str):
    return client.post(f"/reports/{report_id}/approve", headers=_auth_header(token))


def _reject(report_id: int, token: str):
    return client.post(f"/reports/{report_id}/reject", headers=_auth_header(token))


def _report_with_narrative(db_session, token: str, patient_id: int, encounter_id: int) -> dict:
    created = _create_report(token, patient_id, encounter_id)
    return _generate_narrative(created["id"], token)


# ============================== PATCH ======================================


def test_patch_partially_updates_draft_and_leaves_other_fields_unchanged(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {"narrative": "의사가 직접 작성한 설명입니다."})

    assert response.status_code == 200
    body = response.json()
    assert body["content"]["narrative"] == "의사가 직접 작성한 설명입니다."
    assert body["content"]["handoff_note"] is None
    assert body["content"]["patient_guidance"] is None
    assert body["status"] == "DRAFT"


def test_patch_only_sent_field_changes_others_stay_as_they_were(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _patch(created["id"], token, {"handoff_note": "인수인계 메모"})

    response = _patch(created["id"], token, {"narrative": "새 설명"})

    body = response.json()
    assert body["content"]["narrative"] == "새 설명"
    assert body["content"]["handoff_note"] == "인수인계 메모"  # 이전 PATCH에서 남은 값 유지


def test_patch_null_clears_a_field(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _patch(created["id"], token, {"narrative": "지워질 내용"})

    response = _patch(created["id"], token, {"narrative": None})

    assert response.status_code == 200
    assert response.json()["content"]["narrative"] is None


def test_patch_whitespace_only_string_is_normalized_to_none(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {"patient_guidance": "   \n  "})

    assert response.status_code == 200
    assert response.json()["content"]["patient_guidance"] is None


def test_empty_patch_body_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {})
    assert response.status_code == 422


def test_over_length_string_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {"narrative": "가" * 10001})
    assert response.status_code == 422


def test_extra_field_in_patch_returns_422(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {"narrative": "x", "status": "APPROVED"})
    assert response.status_code == 422

    response2 = _patch(created["id"], token, {"emr_snapshot": {}})
    assert response2.status_code == 422


def test_patch_never_changes_emr_snapshot(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    original_snapshot = created["content"]["emr_snapshot"]

    response = _patch(created["id"], token, {"narrative": "테스트"})

    assert response.json()["content"]["emr_snapshot"] == original_snapshot


def test_patch_on_rejected_report_returns_to_draft_and_clears_reviewed_fields(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _reject(created["id"], token)

    response = _patch(created["id"], token, {"narrative": "반려 후 재작성"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["reviewed_by_user_id"] is None
    assert body["reviewed_at"] is None


def test_patch_on_approved_report_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _approve(created["id"], token)

    response = _patch(created["id"], token, {"narrative": "승인 후 시도"})
    assert response.status_code == 409


def test_patch_updates_last_modified_fields(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], token, {"narrative": "x"})

    body = response.json()
    assert body["last_modified_by_user_id"] == doctor.id
    assert body["last_modified_at"] != created["last_modified_at"]


def test_patch_writes_update_report_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    _patch(created["id"], token, {"narrative": "x"})

    log = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="UPDATE_REPORT")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.reason == "clinical_report_content_updated"
    assert log.resource_type == "ClinicalReport"
    assert log.resource_id == str(created["id"])


def test_patch_on_rejected_report_uses_the_returned_to_draft_reason(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _reject(created["id"], token)

    _patch(created["id"], token, {"narrative": "재작성"})

    log = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="UPDATE_REPORT")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log.reason == "rejected_report_returned_to_draft"


def test_patch_rolls_back_everything_on_unexpected_failure(db_session, override_get_db, monkeypatch):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    def _broken(*args, **kwargs):
        raise RuntimeError("의도적으로 주입한 오류 (테스트 전용)")

    monkeypatch.setattr(clinical_reports_router, "write_audit_log", _broken)

    response = _patch(created["id"], token, {"narrative": "실패해야 함"})

    assert response.status_code == 500
    unchanged = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert unchanged.content["narrative"] is None
    assert unchanged.status == ClinicalReportStatus.DRAFT


@pytest.mark.parametrize("email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL])
def test_patch_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _patch(created["id"], _login(email), {"narrative": "x"})
    assert response.status_code == 403


def test_patch_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = client.patch(f"/reports/{created['id']}", json={"narrative": "x"})
    assert response.status_code in (401, 422)


def test_patch_unassigned_and_nonexistent_report_return_identical_404(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    unassigned = _patch(created["id"], _login(ORTHOPEDIC_DOCTOR_EMAIL), {"narrative": "x"})
    nonexistent = _patch(999999, token, {"narrative": "x"})

    assert unassigned.status_code == nonexistent.status_code == 404
    assert unassigned.json() == nonexistent.json()


# ============================== approve ====================================


def test_approve_draft_with_narrative_succeeds(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    response = _approve(created["id"], token)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["reviewed_by_user_id"] == doctor.id
    assert body["reviewed_at"] is not None
    assert _same_instant(body["last_modified_at"], created["last_modified_at"])  # last_modified 불변


def test_author_can_approve_their_own_report(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    response = _approve(created["id"], token)  # 작성자 본인이 승인
    assert response.status_code == 200


def test_a_different_assigned_doctor_can_approve(db_session, override_get_db):
    from app.models import AssignmentRole, Department, PatientAssignment

    seed(db_session)
    patient = _endo_patient(db_session)
    author_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, author_token, patient.id, encounter_id)

    second_doctor = db_session.query(User).filter_by(email=ORTHOPEDIC_DOCTOR_EMAIL).first()
    db_session.add(
        PatientAssignment(
            patient_id=patient.id,
            staff_user_id=second_doctor.id,
            department=Department.ENDOCRINOLOGY,
            assignment_role=AssignmentRole.CONSULTING_PHYSICIAN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    db_session.commit()

    response = _approve(created["id"], _login(ORTHOPEDIC_DOCTOR_EMAIL))
    assert response.status_code == 200


def test_approve_without_narrative_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)  # narrative 없음

    response = _approve(created["id"], token)

    assert response.status_code == 409
    assert response.json()["detail"] == "설명문을 작성하거나 생성한 후 승인할 수 있습니다."


def test_approve_with_whitespace_only_narrative_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    content = dict(report.content)
    content["narrative"] = "   "
    report.content = content
    db_session.commit()

    response = _approve(created["id"], token)
    assert response.status_code == 409


def test_approve_already_approved_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _approve(created["id"], token)

    response = _approve(created["id"], token)
    assert response.status_code == 409


def test_approve_rejected_report_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _reject(created["id"], token)

    response = _approve(created["id"], token)
    assert response.status_code == 409


def test_approve_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    _approve(created["id"], token)

    log = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="APPROVE_REPORT"
    ).first()
    assert log is not None
    assert log.reason == "clinical_report_approved"
    assert log.resource_id == str(created["id"])


@pytest.mark.parametrize("email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL])
def test_approve_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    response = _approve(created["id"], _login(email))
    assert response.status_code == 403


def test_approve_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    response = client.post(f"/reports/{created['id']}/approve")
    assert response.status_code in (401, 422)


def test_approve_unassigned_and_nonexistent_report_return_identical_404(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)

    unassigned = _approve(created["id"], _login(ORTHOPEDIC_DOCTOR_EMAIL))
    nonexistent = _approve(999999, token)

    assert unassigned.status_code == nonexistent.status_code == 404
    assert unassigned.json() == nonexistent.json()


# ============================== reject =====================================


def test_reject_draft_succeeds(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _reject(created["id"], token)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["reviewed_by_user_id"] == doctor.id
    assert body["reviewed_at"] is not None
    assert _same_instant(body["last_modified_at"], created["last_modified_at"])


def test_reject_does_not_require_narrative(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)  # narrative 없음

    response = _reject(created["id"], token)
    assert response.status_code == 200  # 반려는 narrative 요구사항 없음


def test_reject_approved_report_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _report_with_narrative(db_session, token, patient.id, encounter_id)
    _approve(created["id"], token)

    response = _reject(created["id"], token)
    assert response.status_code == 409


def test_reject_already_rejected_returns_409(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _reject(created["id"], token)

    response = _reject(created["id"], token)
    assert response.status_code == 409


def test_reject_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    _reject(created["id"], token)

    log = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="REJECT_REPORT"
    ).first()
    assert log is not None
    assert log.reason == "clinical_report_rejected"
    assert log.resource_id == str(created["id"])


@pytest.mark.parametrize("email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL])
def test_reject_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _reject(created["id"], _login(email))
    assert response.status_code == 403


def test_reject_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = client.post(f"/reports/{created['id']}/reject")
    assert response.status_code in (401, 422)


def test_reject_unassigned_and_nonexistent_report_return_identical_404(
    db_session, override_get_db
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    unassigned = _reject(created["id"], _login(ORTHOPEDIC_DOCTOR_EMAIL))
    nonexistent = _reject(999999, token)

    assert unassigned.status_code == nonexistent.status_code == 404
    assert unassigned.json() == nonexistent.json()


def test_reject_rolls_back_everything_on_unexpected_failure(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    def _broken(*args, **kwargs):
        raise RuntimeError("의도적으로 주입한 오류 (테스트 전용)")

    monkeypatch.setattr(clinical_reports_router, "write_audit_log", _broken)

    response = _reject(created["id"], token)

    assert response.status_code == 500
    unchanged = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert unchanged.status == ClinicalReportStatus.DRAFT
    assert unchanged.reviewed_at is None


# ============================== 비밀정보 ====================================


def test_no_endpoint_ever_leaks_secrets(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    patch_response = _patch(created["id"], token, {"narrative": "x"})
    approve_response = _approve(created["id"], token)

    for response in (patch_response, approve_response):
        assert "hashed_password" not in response.text
        assert token not in response.text

    logs = db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).all()
    for log in logs:
        for field in (log.resource_id, log.reason, log.action, log.resource_type):
            assert token not in field

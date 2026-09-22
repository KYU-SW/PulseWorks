from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AiSummary, AuditLog, ClinicalReport, ClinicalReportStatus, Encounter, Patient, User
from app.routers import clinical_reports as clinical_reports_router
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


def _first_encounter_id(db_session, patient_id: int) -> int:
    return (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .first()
        .id
    )


def _create_report(db_session, token: str, patient_id: int, encounter_id: int) -> dict:
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


def _generate(report_id: int, token: str):
    return client.post(f"/reports/{report_id}/generate-narrative", headers=_auth_header(token))


# 담당 DOCTOR 생성 성공 & narrative만 갱신 & emr_snapshot 불변
def test_assigned_doctor_generates_narrative_and_only_narrative_changes(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)
    original_emr_snapshot = report["content"]["emr_snapshot"]

    response = _generate(report["id"], token)

    assert response.status_code == 200
    body = response.json()
    assert body["content"]["narrative"] is not None
    # Task 20C 후속 보완: 환자에게도 그대로 공개되는 narrative라서, 기존의
    # "초안이며 의료진의 검토가 필요합니다" 문구는 승인 후 상태와
    # 모순되므로 제거됐다 — 승인 후에도 모순되지 않는 안내로 끝난다.
    assert (
        "검사결과와 처방의 의미는 담당 의료진 또는 약사에게 확인하세요."
        in body["content"]["narrative"]
    )
    assert body["content"]["emr_snapshot"] == original_emr_snapshot
    assert body["content"]["handoff_note"] is None
    assert body["content"]["patient_guidance"] is None


# AiSummary 생성 및 필드 일치
def test_generates_an_ai_summary_with_matching_fields(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    response = _generate(report["id"], token)
    narrative = response.json()["content"]["narrative"]

    summary = db_session.query(AiSummary).filter_by(
        patient_id=patient.id, encounter_id=encounter_id
    ).first()
    assert summary is not None
    assert summary.status.value == "DRAFT"
    assert summary.summary_text == narrative
    assert summary.reviewed_by_user_id is None
    assert summary.reviewed_at is None
    assert summary.generated_at is not None


# 재호출 시 narrative, AiSummary 수, 감사 로그 및 수정 시각 불변
def test_recall_is_idempotent_and_changes_nothing(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    first_response = _generate(report["id"], token)
    first_body = first_response.json()

    before_summary_count = db_session.query(AiSummary).count()
    before_log_count = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="GENERATE_REPORT_NARRATIVE"
    ).count()

    second_response = _generate(report["id"], token)
    second_body = second_response.json()

    assert second_response.status_code == 200
    assert second_body["content"]["narrative"] == first_body["content"]["narrative"]
    # SQLite는 재조회 시 timezone 오프셋을 보존하지 않는다(conftest.py 설명
    # 참고) — naive/aware 표기 차이가 아니라 실제 시각이 같은지로 비교한다.
    first_modified = datetime.fromisoformat(first_body["last_modified_at"]).replace(tzinfo=None)
    second_modified = datetime.fromisoformat(second_body["last_modified_at"]).replace(tzinfo=None)
    assert second_modified == first_modified
    assert db_session.query(AiSummary).count() == before_summary_count
    after_log_count = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="GENERATE_REPORT_NARRATIVE"
    ).count()
    assert after_log_count == before_log_count


# APPROVED와 REJECTED는 409
@pytest.mark.parametrize("status", [ClinicalReportStatus.APPROVED, ClinicalReportStatus.REJECTED])
def test_approved_or_rejected_report_returns_409(db_session, override_get_db, status):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(db_session, token, patient.id, encounter_id)

    # Task 17이 아직 없으므로 승인/반려는 테스트에서 직접 fixture로 만든다.
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    report.status = status
    report.reviewed_at = datetime.now(timezone.utc)
    db_session.commit()

    response = _generate(created["id"], token)
    assert response.status_code == 409


# 미배정 및 미존재 보고서는 동일 404
def test_unassigned_and_nonexistent_report_return_identical_404(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    creator_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, creator_token, patient.id, encounter_id)

    unassigned_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    unassigned_response = _generate(report["id"], unassigned_token)
    nonexistent_response = _generate(999999, creator_token)

    assert unassigned_response.status_code == nonexistent_response.status_code == 404
    assert unassigned_response.json() == nonexistent_response.json()


# 다른 역할 403
@pytest.mark.parametrize("email", [NURSE_EMAIL, PATIENT_EMAIL, ADMIN_STAFF_EMAIL, SYSTEM_ADMIN_EMAIL])
def test_non_doctor_roles_forbidden(db_session, override_get_db, email):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    other_token = _login(email)
    response = _generate(report["id"], other_token)
    assert response.status_code == 403


# 미인증 401
def test_missing_token_is_unauthorized(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    response = client.post(f"/reports/{report['id']}/generate-narrative")
    assert response.status_code in (401, 422)


# 트랜잭션 실패 시 전체 rollback
def test_unexpected_failure_rolls_back_everything(db_session, override_get_db, monkeypatch):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    before_summary_count = db_session.query(AiSummary).count()
    before_log_count = db_session.query(AuditLog).count()

    def _broken_write_audit_log(*args, **kwargs):
        raise RuntimeError("의도적으로 주입한 오류 (테스트 전용)")

    monkeypatch.setattr(clinical_reports_router, "write_audit_log", _broken_write_audit_log)

    response = _generate(report["id"], token)

    assert response.status_code == 500
    assert db_session.query(AiSummary).count() == before_summary_count
    assert db_session.query(AuditLog).count() == before_log_count
    unchanged_report = db_session.query(ClinicalReport).filter_by(id=report["id"]).first()
    assert unchanged_report.content["narrative"] is None


# 원본 EMR 재조회 없음 (collect_report_data가 호출되지 않아야 함)
def test_does_not_recollect_original_emr_data(db_session, override_get_db, monkeypatch):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("generate-narrative must not call collect_report_data()")

    monkeypatch.setattr(clinical_reports_router, "collect_report_data", _fail_if_called)

    response = _generate(report["id"], token)
    assert response.status_code == 200


# 감사 로그 확인
def test_generate_writes_audit_log_with_expected_fields(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    _generate(report["id"], token)

    log_entry = db_session.query(AuditLog).filter_by(
        actor_user_id=doctor.id, action="GENERATE_REPORT_NARRATIVE"
    ).first()
    assert log_entry is not None
    assert log_entry.resource_type == "ClinicalReport"
    assert log_entry.resource_id == str(report["id"])
    assert log_entry.patient_id == patient.id
    assert log_entry.reason == "deterministic_mock_narrative"


# 비밀정보 미노출
def test_response_and_audit_log_never_contain_secrets(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    doctor = db_session.query(User).filter_by(email=ENDOCRINE_DOCTOR_EMAIL).first()
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    report = _create_report(db_session, token, patient.id, encounter_id)

    response = _generate(report["id"], token)

    assert "hashed_password" not in response.text
    assert token not in response.text

    logs = db_session.query(AuditLog).filter_by(actor_user_id=doctor.id).all()
    for log in logs:
        for field in (log.resource_id, log.reason, log.action, log.resource_type):
            assert token not in field

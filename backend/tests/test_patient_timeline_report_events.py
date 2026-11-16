from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, ClinicalReport, Encounter, Patient
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
PATIENT_EMAIL = "patient1@example.test"

REPORT_LIFECYCLE_EVENT_TYPES = {
    "REPORT_CREATED",
    "REPORT_UPDATED",
    "REPORT_APPROVED",
    "REPORT_REJECTED",
}
CLINICAL_EVENT_TYPES = (
    "ENCOUNTER",
    "VITAL_SIGN",
    "LAB_RESULT",
    "DIAGNOSIS",
    "PRESCRIPTION",
    "CLINICAL_NOTE",
)


def _login(email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "demo1234"})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _patient(db_session, mrn: str) -> Patient:
    return db_session.query(Patient).filter_by(mrn=mrn).first()


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


def _edit_narrative(token: str, report_id: int, narrative: str) -> None:
    client.patch(
        f"/reports/{report_id}",
        json={"narrative": narrative},
        headers=_auth_header(token),
    )


def _approved_report(db_session, token: str, patient_id: int) -> dict:
    created = _create_report(token, patient_id, _first_encounter_id(db_session, patient_id))
    _edit_narrative(token, created["id"], "의료진이 검토한 설명문")
    client.post(f"/reports/{created['id']}/approve", headers=_auth_header(token))
    return created


def _rejected_report(db_session, token: str, patient_id: int) -> dict:
    created = _create_report(token, patient_id, _first_encounter_id(db_session, patient_id))
    client.post(f"/reports/{created['id']}/reject", headers=_auth_header(token))
    return created


def _timeline(patient_id: int, token: str) -> dict:
    return client.get(
        f"/patients/{patient_id}/timeline", headers=_auth_header(token)
    ).json()


def _event_types(timeline: dict) -> set[str]:
    return {item["event_type"] for item in timeline["timeline"]}


# ===== 임상 타임라인에는 보고서 lifecycle 이벤트가 하나도 없다 =====


def test_approved_report_does_not_appear_in_clinical_timeline(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _approved_report(db_session, token, patient.id)

    timeline = _timeline(patient.id, token)

    assert "REPORT_APPROVED" not in _event_types(timeline)
    assert _event_types(timeline).isdisjoint(REPORT_LIFECYCLE_EVENT_TYPES)


def test_rejected_report_does_not_appear_in_clinical_timeline(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _rejected_report(db_session, token, patient.id)

    timeline = _timeline(patient.id, token)

    assert "REPORT_REJECTED" not in _event_types(timeline)
    assert _event_types(timeline).isdisjoint(REPORT_LIFECYCLE_EVENT_TYPES)


def test_draft_and_edited_report_add_no_lifecycle_event_to_clinical_timeline(
    db_session, override_get_db
):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    _edit_narrative(token, created["id"], "의료진이 수정한 설명문")

    timeline = _timeline(patient.id, token)

    assert _event_types(timeline).isdisjoint(REPORT_LIFECYCLE_EVENT_TYPES)


# ===== 타임라인에서 숨겨도 보고서 원본·상태·감사기록·목록은 그대로다 =====


def test_hidden_reports_keep_rows_statuses_and_timestamps(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(db_session, token, patient.id)
    rejected = _rejected_report(db_session, token, patient.id)

    _timeline(patient.id, token)

    approved_row = db_session.query(ClinicalReport).filter_by(id=approved["id"]).first()
    rejected_row = db_session.query(ClinicalReport).filter_by(id=rejected["id"]).first()
    assert approved_row.status.value == "APPROVED"
    assert rejected_row.status.value == "REJECTED"
    for row in (approved_row, rejected_row):
        assert row.created_at is not None
        assert row.last_modified_at is not None
        assert row.reviewed_at is not None


def test_hidden_reports_keep_audit_log_doctor_report_list_and_patient_access(
    db_session, override_get_db
):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(db_session, token, patient.id)
    rejected = _rejected_report(db_session, token, patient.id)

    _timeline(patient.id, token)

    approved_actions = {
        row.action
        for row in db_session.query(AuditLog).filter_by(resource_id=str(approved["id"])).all()
    }
    rejected_actions = {
        row.action
        for row in db_session.query(AuditLog).filter_by(resource_id=str(rejected["id"])).all()
    }
    assert {"CREATE_REPORT", "UPDATE_REPORT", "APPROVE_REPORT"} <= approved_actions
    assert {"CREATE_REPORT", "REJECT_REPORT"} <= rejected_actions

    listed = {
        item["id"]: item["status"]
        for item in client.get("/reports", headers=_auth_header(token)).json()["items"]
    }
    assert listed[approved["id"]] == "APPROVED"
    assert listed[rejected["id"]] == "REJECTED"

    patient_token = _login(PATIENT_EMAIL)
    patient_report_ids = [
        item["id"]
        for item in client.get("/patient/reports", headers=_auth_header(patient_token)).json()
    ]
    assert approved["id"] in patient_report_ids
    assert rejected["id"] not in patient_report_ids


# ===== 임상 이벤트·보안·정렬 회귀 =====


def test_all_clinical_event_types_remain_in_timeline(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _approved_report(db_session, token, patient.id)
    _rejected_report(db_session, token, patient.id)

    event_types = _event_types(_timeline(patient.id, token))

    for event_type in CLINICAL_EVENT_TYPES:
        assert event_type in event_types, event_type


def test_timeline_never_exposes_report_narrative_or_content(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    _edit_narrative(token, created["id"], "이 문장은 타임라인에 절대 노출되면 안 된다.")
    client.post(f"/reports/{created['id']}/approve", headers=_auth_header(token))

    timeline = _timeline(patient.id, token)

    assert "이 문장은 타임라인에 절대 노출되면 안 된다" not in str(timeline)
    for item in timeline["timeline"]:
        assert "content" not in item
        assert "narrative" not in item
        assert "emr_snapshot" not in item


def test_timeline_ordering_stays_deterministic_with_hidden_reports(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _approved_report(db_session, token, patient.id)
    _rejected_report(db_session, token, patient.id)

    first_call = _timeline(patient.id, token)
    second_call = _timeline(patient.id, token)

    first_order = [(item["event_type"], item["id"]) for item in first_call["timeline"]]
    second_order = [(item["event_type"], item["id"]) for item in second_call["timeline"]]
    assert first_order == second_order

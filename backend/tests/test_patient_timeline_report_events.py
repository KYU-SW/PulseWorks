from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import ClinicalReport, Encounter, Patient
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"


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


def _timeline(patient_id: int, token: str) -> dict:
    return client.get(
        f"/patients/{patient_id}/timeline", headers=_auth_header(token)
    ).json()


def _items_of_type(timeline: dict, event_type: str) -> list[dict]:
    return [item for item in timeline["timeline"] if item["event_type"] == event_type]


def test_report_created_event_appears_with_created_at_timestamp(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    timeline = _timeline(patient.id, token)
    created_events = _items_of_type(timeline, "REPORT_CREATED")

    assert len(created_events) == 1
    event = created_events[0]
    assert event["encounter_id"] == encounter_id
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert datetime.fromisoformat(event["event_time"]).replace(tzinfo=None) == report.created_at.replace(
        tzinfo=None
    )
    assert "narrative" not in event["summary"]


def test_report_approved_event_uses_reviewed_at(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    client.post(f"/reports/{created['id']}/generate-narrative", headers=_auth_header(token))
    client.post(f"/reports/{created['id']}/approve", headers=_auth_header(token))

    timeline = _timeline(patient.id, token)
    approved_events = _items_of_type(timeline, "REPORT_APPROVED")

    assert len(approved_events) == 1
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert datetime.fromisoformat(
        approved_events[0]["event_time"]
    ).replace(tzinfo=None) == report.reviewed_at.replace(tzinfo=None)
    # REJECTED event must not also appear for an approved report.
    assert _items_of_type(timeline, "REPORT_REJECTED") == []


def test_report_rejected_event_uses_reviewed_at(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    client.post(f"/reports/{created['id']}/reject", headers=_auth_header(token))

    timeline = _timeline(patient.id, token)
    rejected_events = _items_of_type(timeline, "REPORT_REJECTED")

    assert len(rejected_events) == 1
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert datetime.fromisoformat(
        rejected_events[0]["event_time"]
    ).replace(tzinfo=None) == report.reviewed_at.replace(tzinfo=None)
    assert _items_of_type(timeline, "REPORT_APPROVED") == []


def test_timeline_never_exposes_report_narrative_or_content(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    client.patch(
        f"/reports/{created['id']}",
        json={"narrative": "이 문장은 타임라인에 절대 노출되면 안 된다."},
        headers=_auth_header(token),
    )

    timeline = _timeline(patient.id, token)
    serialized = str(timeline)
    assert "이 문장은 타임라인에 절대 노출되면 안 된다" not in serialized
    assert "content" not in timeline["timeline"][0]


def test_other_patients_report_events_do_not_leak_into_this_timeline(db_session, override_get_db):
    seed(db_session)
    endo_patient = _patient(db_session, "SYN-0001")
    ortho_patient = _patient(db_session, "SYN-0002")
    endo_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    endo_encounter_id = _first_encounter_id(db_session, endo_patient.id)
    ortho_encounter_id = _first_encounter_id(db_session, ortho_patient.id)
    _create_report(endo_token, endo_patient.id, endo_encounter_id)
    ortho_created = _create_report(ortho_token, ortho_patient.id, ortho_encounter_id)

    timeline = _timeline(endo_patient.id, endo_token)
    created_events = _items_of_type(timeline, "REPORT_CREATED")

    assert len(created_events) == 1
    assert created_events[0]["encounter_id"] == endo_encounter_id
    assert all(event["encounter_id"] != ortho_encounter_id for event in created_events)
    assert ortho_created["id"] not in [event["id"] for event in created_events]


def test_existing_timeline_event_types_are_unaffected(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    _create_report(token, patient.id, encounter_id)

    timeline = _timeline(patient.id, token)

    assert len(_items_of_type(timeline, "ENCOUNTER")) >= 1
    assert len(_items_of_type(timeline, "VITAL_SIGN")) >= 1


def test_timeline_ordering_stays_deterministic_with_report_events(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    _create_report(token, patient.id, encounter_id)

    first_call = _timeline(patient.id, token)
    second_call = _timeline(patient.id, token)

    first_order = [(item["event_type"], item["id"]) for item in first_call["timeline"]]
    second_order = [(item["event_type"], item["id"]) for item in second_call["timeline"]]
    assert first_order == second_order

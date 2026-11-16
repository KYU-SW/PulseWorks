from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, ClinicalReport, Encounter, Patient
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"

CLINICAL_EVENT_TYPES = ("ENCOUNTER", "VITAL_SIGN", "LAB_RESULT", "DIAGNOSIS")


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


def _timeline(patient_id: int, token: str) -> dict:
    return client.get(
        f"/patients/{patient_id}/timeline", headers=_auth_header(token)
    ).json()


def _items_of_type(timeline: dict, event_type: str) -> list[dict]:
    return [item for item in timeline["timeline"] if item["event_type"] == event_type]


def _as_naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


# ===== 저가치 문서 작업 이벤트(생성/수정)는 임상 타임라인에 올리지 않는다 =====


def test_draft_report_creation_does_not_add_report_created_event(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))

    timeline = _timeline(patient.id, token)

    assert _items_of_type(timeline, "REPORT_CREATED") == []


def test_report_edit_does_not_add_report_updated_event(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    _edit_narrative(token, created["id"], "의료진이 수정한 설명문")

    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    # 전제: 실제로 수정되어 last_modified_at이 created_at과 달라졌다.
    assert report.last_modified_at != report.created_at

    timeline = _timeline(patient.id, token)

    assert _items_of_type(timeline, "REPORT_UPDATED") == []


# ===== 공식 상태 전이(승인/반려)는 계속 임상 타임라인에 남긴다 =====


def test_approved_report_keeps_only_approved_event_with_reviewed_at(db_session, override_get_db):
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
    assert approved_events[0]["encounter_id"] == encounter_id
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert _as_naive(datetime.fromisoformat(approved_events[0]["event_time"])) == _as_naive(
        report.reviewed_at
    )
    assert _items_of_type(timeline, "REPORT_REJECTED") == []
    assert _items_of_type(timeline, "REPORT_CREATED") == []
    assert _items_of_type(timeline, "REPORT_UPDATED") == []


def test_rejected_report_keeps_only_rejected_event_with_reviewed_at(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    client.post(f"/reports/{created['id']}/reject", headers=_auth_header(token))

    timeline = _timeline(patient.id, token)
    rejected_events = _items_of_type(timeline, "REPORT_REJECTED")

    assert len(rejected_events) == 1
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert _as_naive(datetime.fromisoformat(rejected_events[0]["event_time"])) == _as_naive(
        report.reviewed_at
    )
    assert _items_of_type(timeline, "REPORT_APPROVED") == []
    assert _items_of_type(timeline, "REPORT_CREATED") == []
    assert _items_of_type(timeline, "REPORT_UPDATED") == []


# ===== 원본 데이터·감사 로그·보고서 목록은 그대로 보존된다 =====


def test_hidden_lifecycle_events_keep_report_timestamps_audit_log_and_report_list(
    db_session, override_get_db
):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    _edit_narrative(token, created["id"], "의료진이 수정한 설명문")

    _timeline(patient.id, token)

    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert report.created_at is not None
    assert report.last_modified_at is not None
    audited_actions = {
        row.action
        for row in db_session.query(AuditLog).filter_by(resource_id=str(created["id"])).all()
    }
    assert {"CREATE_REPORT", "UPDATE_REPORT"} <= audited_actions
    listed_ids = [
        item["id"]
        for item in client.get("/reports", headers=_auth_header(token)).json()["items"]
    ]
    assert created["id"] in listed_ids


# ===== 보안·격리·회귀 =====


def test_timeline_never_exposes_report_narrative_or_content(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    _edit_narrative(token, created["id"], "이 문장은 타임라인에 절대 노출되면 안 된다.")
    client.post(f"/reports/{created['id']}/approve", headers=_auth_header(token))

    timeline = _timeline(patient.id, token)
    serialized = str(timeline)

    assert "이 문장은 타임라인에 절대 노출되면 안 된다" not in serialized
    for item in timeline["timeline"]:
        assert "content" not in item
        assert "narrative" not in item
        assert "emr_snapshot" not in item


def test_other_patients_report_events_do_not_leak_into_this_timeline(db_session, override_get_db):
    seed(db_session)
    endo_patient = _patient(db_session, "SYN-0001")
    ortho_patient = _patient(db_session, "SYN-0002")
    endo_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    endo_encounter_id = _first_encounter_id(db_session, endo_patient.id)
    ortho_encounter_id = _first_encounter_id(db_session, ortho_patient.id)
    endo_created = _create_report(endo_token, endo_patient.id, endo_encounter_id)
    ortho_created = _create_report(ortho_token, ortho_patient.id, ortho_encounter_id)
    client.post(f"/reports/{endo_created['id']}/reject", headers=_auth_header(endo_token))
    client.post(f"/reports/{ortho_created['id']}/reject", headers=_auth_header(ortho_token))

    timeline = _timeline(endo_patient.id, endo_token)
    rejected_events = _items_of_type(timeline, "REPORT_REJECTED")

    assert len(rejected_events) == 1
    assert rejected_events[0]["encounter_id"] == endo_encounter_id
    assert ortho_created["id"] not in [event["id"] for event in rejected_events]


def test_clinical_timeline_event_types_are_unaffected(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))

    timeline = _timeline(patient.id, token)

    for event_type in CLINICAL_EVENT_TYPES:
        assert len(_items_of_type(timeline, event_type)) >= 1, event_type


def test_timeline_ordering_stays_deterministic_with_report_events(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(token, patient.id, _first_encounter_id(db_session, patient.id))
    client.post(f"/reports/{created['id']}/reject", headers=_auth_header(token))

    first_call = _timeline(patient.id, token)
    second_call = _timeline(patient.id, token)

    first_order = [(item["event_type"], item["id"]) for item in first_call["timeline"]]
    second_order = [(item["event_type"], item["id"]) for item in second_call["timeline"]]
    assert first_order == second_order

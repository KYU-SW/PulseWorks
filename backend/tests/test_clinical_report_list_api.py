from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import ClinicalReport, Encounter, Patient
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


def _set_created_at(db_session, report_id: int, when: datetime) -> None:
    report = db_session.query(ClinicalReport).filter_by(id=report_id).first()
    report.created_at = when
    report.last_modified_at = when
    db_session.commit()


def _list_reports(token: str, **params) -> "Response":
    return client.get("/reports", params=params, headers=_auth_header(token))


# ======================= 권한 범위 =======================


def test_doctor_sees_report_for_own_assigned_patient(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _list_reports(token)

    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert created["id"] in ids


def test_doctor_does_not_see_report_for_unassigned_patient(db_session, override_get_db):
    seed(db_session)
    ortho_patient = _patient(db_session, "SYN-0002")
    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    ortho_encounter_id = _first_encounter_id(db_session, ortho_patient.id)
    created = _create_report(ortho_token, ortho_patient.id, ortho_encounter_id)

    endo_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    response = _list_reports(endo_token)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


def test_other_doctors_assigned_patient_report_is_not_exposed(db_session, override_get_db):
    seed(db_session)
    endo_patient = _patient(db_session, "SYN-0001")
    endo_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    endo_encounter_id = _first_encounter_id(db_session, endo_patient.id)
    created = _create_report(endo_token, endo_patient.id, endo_encounter_id)

    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    response = _list_reports(ortho_token)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


def test_patient_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(PATIENT_EMAIL)
    response = _list_reports(token)
    assert response.status_code == 403


def test_nurse_role_forbidden_consistent_with_existing_report_policy(db_session, override_get_db):
    seed(db_session)
    token = _login(NURSE_EMAIL)
    response = _list_reports(token)
    assert response.status_code == 403


def test_admin_staff_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(ADMIN_STAFF_EMAIL)
    response = _list_reports(token)
    assert response.status_code == 403


def test_system_admin_role_forbidden(db_session, override_get_db):
    seed(db_session)
    token = _login(SYSTEM_ADMIN_EMAIL)
    response = _list_reports(token)
    assert response.status_code == 403


# ======================= Filters =======================


def test_status_filter_returns_only_matching_status(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _list_reports(token, status="DRAFT")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] in ids

    response = _list_reports(token, status="APPROVED")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


def test_from_date_filter_excludes_earlier_reports(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _set_created_at(db_session, created["id"], datetime(2020, 1, 1, tzinfo=timezone.utc))

    response = _list_reports(token, from_date="2025-01-01")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


def test_to_date_filter_excludes_later_reports(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _set_created_at(db_session, created["id"], datetime(2030, 1, 1, tzinfo=timezone.utc))

    response = _list_reports(token, to_date="2025-01-01")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


def test_status_and_date_combined_filter(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _set_created_at(db_session, created["id"], datetime(2025, 6, 15, tzinfo=timezone.utc))

    response = _list_reports(
        token, status="DRAFT", from_date="2025-06-01", to_date="2025-06-30"
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] in ids

    response = _list_reports(
        token, status="APPROVED", from_date="2025-06-01", to_date="2025-06-30"
    )
    ids = [item["id"] for item in response.json()["items"]]
    assert created["id"] not in ids


# ======================= 정렬/Pagination =======================


def test_results_are_sorted_newest_first_with_id_tiebreak(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_ids = (
        db_session.query(Encounter)
        .filter_by(patient_id=patient.id)
        .order_by(Encounter.start_time)
        .all()
    )
    assert len(encounter_ids) >= 2
    first = _create_report(token, patient.id, encounter_ids[0].id)
    second = _create_report(token, patient.id, encounter_ids[1].id)
    same_instant = datetime(2025, 3, 1, tzinfo=timezone.utc)
    _set_created_at(db_session, first["id"], same_instant)
    _set_created_at(db_session, second["id"], same_instant)

    response = _list_reports(token)
    items = response.json()["items"]
    ordered_ids = [item["id"] for item in items if item["id"] in (first["id"], second["id"])]
    # 동일 created_at이면 id DESC로 결정적으로 정렬된다.
    assert ordered_ids == sorted([first["id"], second["id"]], reverse=True)


def test_pagination_returns_requested_page(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_ids = [
        e.id
        for e in db_session.query(Encounter).filter_by(patient_id=patient.id).all()
    ]
    created_ids = []
    for i, encounter_id in enumerate(encounter_ids[:3]):
        created = _create_report(token, patient.id, encounter_id)
        _set_created_at(
            db_session, created["id"], datetime(2025, 1, 1 + i, tzinfo=timezone.utc)
        )
        created_ids.append(created["id"])

    page1 = _list_reports(token, page=1, page_size=2).json()
    assert len(page1["items"]) == 2
    assert page1["page"] == 1
    assert page1["page_size"] == 2
    assert page1["total"] >= 3

    page2 = _list_reports(token, page=2, page_size=2).json()
    page1_ids = {item["id"] for item in page1["items"]}
    page2_ids = {item["id"] for item in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_page_size_above_max_is_rejected(db_session, override_get_db):
    seed(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    response = _list_reports(token, page_size=101)
    assert response.status_code == 422


# ======================= Response 내용 =======================


def test_list_response_never_includes_full_content_or_narrative(db_session, override_get_db):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    _create_report(token, patient.id, encounter_id)

    response = _list_reports(token)
    body = response.json()
    assert len(body["items"]) >= 1
    for item in body["items"]:
        assert "content" not in item
        assert "narrative" not in item
        assert "emr_snapshot" not in item

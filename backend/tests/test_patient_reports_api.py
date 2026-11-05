from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.main import app
from app.models import (
    AuditLog,
    ClinicalReport,
    Encounter,
    LabResult,
    Patient,
    Prescription,
    Role,
    SafetyAlert,
    SafetyAlertPriority,
    User,
)
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"
ORTHOPEDIC_DOCTOR_EMAIL = "orthopedic.doctor@example.test"
PATIENT1_EMAIL = "patient1@example.test"  # SYN-0001, 내분비내과
PATIENT2_EMAIL = "patient2@example.test"  # SYN-0002, 정형외과


def _login(email: str, password: str = "demo1234") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _patient_by_mrn(db_session, mrn: str) -> Patient:
    return db_session.query(Patient).filter_by(mrn=mrn).first()


def _encounter_ids(db_session, patient_id: int) -> list[int]:
    rows = (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .all()
    )
    return [e.id for e in rows]


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


def _approve(report_id: int, token: str) -> dict:
    return client.post(f"/reports/{report_id}/approve", headers=_auth_header(token)).json()


def _reject(report_id: int, token: str) -> dict:
    return client.post(f"/reports/{report_id}/reject", headers=_auth_header(token)).json()


def _approved_report(token: str, patient_id: int, encounter_id: int) -> dict:
    created = _create_report(token, patient_id, encounter_id)
    _generate_narrative(created["id"], token)
    return _approve(created["id"], token)


# ============================== 목록 GET /patient/reports ===================


def test_list_returns_only_own_approved_reports(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_ids = _encounter_ids(db_session, patient.id)
    approved = _approved_report(doctor_token, patient.id, encounter_ids[0])

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get("/patient/reports", headers=_auth_header(patient_token))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == approved["id"]
    assert body[0]["report_type"] == "DOCTOR_REFERENCE"
    assert set(body[0].keys()) == {"id", "report_type", "department", "encounter_date", "reviewed_at"}


def test_list_excludes_draft_and_rejected(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_ids = _encounter_ids(db_session, patient.id)

    approved = _approved_report(doctor_token, patient.id, encounter_ids[0])
    draft = _create_report(doctor_token, patient.id, encounter_ids[1])
    rejected_created = _create_report(doctor_token, patient.id, encounter_ids[2])
    _reject(rejected_created["id"], doctor_token)

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get("/patient/reports", headers=_auth_header(patient_token))

    ids = [item["id"] for item in response.json()]
    assert ids == [approved["id"]]
    assert draft["id"] not in ids
    assert rejected_created["id"] not in ids


def test_list_excludes_other_patients_reports(db_session, override_get_db):
    seed(db_session)
    patient1 = _patient_by_mrn(db_session, "SYN-0001")
    patient2 = _patient_by_mrn(db_session, "SYN-0002")
    endo_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)

    _approved_report(endo_token, patient1.id, _encounter_ids(db_session, patient1.id)[0])
    other_report = _approved_report(
        ortho_token, patient2.id, _encounter_ids(db_session, patient2.id)[0]
    )

    patient1_token = _login(PATIENT1_EMAIL)
    response = client.get("/patient/reports", headers=_auth_header(patient1_token))

    ids = [item["id"] for item in response.json()]
    assert other_report["id"] not in ids


def test_list_sorted_by_reviewed_at_descending(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_ids = _encounter_ids(db_session, patient.id)

    first_approved = _approved_report(doctor_token, patient.id, encounter_ids[0])
    second_approved = _approved_report(doctor_token, patient.id, encounter_ids[1])

    # 두 승인 시각이 같은 초 안에 몰릴 수 있으므로, 실제 reviewed_at을
    # 강제로 벌려 정렬 검증이 시각 우연에 좌우되지 않게 한다.
    first_row = db_session.query(ClinicalReport).filter_by(id=first_approved["id"]).first()
    second_row = db_session.query(ClinicalReport).filter_by(id=second_approved["id"]).first()
    first_row.reviewed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    second_row.reviewed_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    db_session.commit()

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get("/patient/reports", headers=_auth_header(patient_token))

    ids = [item["id"] for item in response.json()]
    assert ids == [second_approved["id"], first_approved["id"]]


def test_list_is_empty_for_a_patient_role_account_with_no_linked_patient(
    db_session, override_get_db
):
    seed(db_session)
    orphan = User(
        email="orphan.patient@example.test",
        hashed_password=hash_password("demo1234"),
        full_name="연결되지 않은 환자 계정",
        role=Role.PATIENT,
        patient_id=None,
    )
    db_session.add(orphan)
    db_session.commit()

    token = _login("orphan.patient@example.test")
    response = client.get("/patient/reports", headers=_auth_header(token))

    assert response.status_code == 200
    assert response.json() == []


def test_list_never_writes_an_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    _approved_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])
    # 로그인 자체도 감사 로그를 남기므로(app/routers/auth.py), 로그인까지
    # 끝낸 뒤에 기준선을 잡아야 "목록 조회 자체는 로그를 남기지 않는다"만
    # 정확히 검증된다.
    patient_token = _login(PATIENT1_EMAIL)
    before = db_session.query(AuditLog).count()

    client.get("/patient/reports", headers=_auth_header(patient_token))

    assert db_session.query(AuditLog).count() == before


def test_list_requires_patient_role(db_session, override_get_db):
    seed(db_session)
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)

    response = client.get("/patient/reports", headers=_auth_header(doctor_token))

    assert response.status_code == 403


def test_list_requires_authentication(db_session, override_get_db):
    seed(db_session)

    response = client.get("/patient/reports")

    assert response.status_code in (401, 422)


# ============================== 상세 GET /patient/reports/{id} ==============


def test_detail_success_returns_expected_top_level_fields(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "id", "department", "encounter_type", "encounter_date", "reviewed_at", "narrative",
        "patient_guidance", "diagnoses", "lab_results", "lab_trends", "prescriptions",
        "allergies", "evidence", "safety_notice",
    }
    assert body["department"] == "ENDOCRINOLOGY"
    assert body["encounter_type"] == "OUTPATIENT"
    assert body["narrative"] is not None
    assert body["safety_notice"] == (
        "검사결과와 참고범위만으로 건강상태를 판단하지 마세요.\n"
        "자세한 의미는 담당 의료진에게 확인하세요."
    )


def test_detail_never_exposes_internal_fields_anywhere(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _encounter_ids(db_session, patient.id)[0]

    # 이 응답에서 절대 나오면 안 되는 SafetyAlert를 실제로 하나 만들어
    # "원래 없어서 안 보이는 것"이 아니라 "있어도 걸러진다"를 검증한다.
    prescription = db_session.query(Prescription).filter_by(encounter_id=encounter_id).first()
    db_session.add(
        SafetyAlert(
            encounter_id=encounter_id,
            prescription_id=prescription.id,
            lab_result_id=None,
            rule_id="ALLERGY_DRUG_CONFLICT",
            evidence={"substance": "Penicillin"},
            priority=SafetyAlertPriority.HIGH,
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    approved = _approved_report(doctor_token, patient.id, encounter_id)
    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))
    raw_text = response.text

    # 여기서는 응답의 "구조"(JSON 키)에 내부 필드가 없는지를 검사한다.
    # narrative는 의사가 이미 검토·승인한 자유 서술형 텍스트라서(Task 17),
    # 그 문장 안에 우연히 이런 단어가 들어 있어도(Mock 생성기가 SafetyAlert
    # 사실을 문장으로 풀어썼을 수 있음) 이 Task가 그 승인된 텍스트를 다시
    # 검열·수정하지 않는다 — "narrative는 새 설명을 생성하거나 수정하지
    # 않는다"는 확정 정책 그대로다. 따라서 raw_text 전체가 아니라 구조화된
    # 필드 키만 검사한다.
    for forbidden_key in [
        "source_record_ids", "handoff_note", "rule_id", "source_type",
        "created_by_user_id", "last_modified_by_user_id", "reviewed_by_user_id",
        "safety_alerts", "clinical_notes", "preview_text", "prescribed_by_user_id",
        # Task D1: narrative 출처 메타데이터는 의사 화면 전용이다.
        "narrative_source", "narrative_edited_by_clinician", "provider", "vendor", "model",
        # Task F4-A: 이 Encounter에 실제로 VitalSign·BMI가 있는데도(위에서
        # seed된 7종 + BMI 계산 가능 사례) 환자 화면에는 전혀 노출되지
        # 않아야 한다 — EmrSnapshot 자체에 아직 연결되지 않았기 때문이다.
        "vital_type", "vital_signs", "value_secondary", "quality_warnings", "bmi",
    ]:
        assert f'"{forbidden_key}"' not in raw_text

    body = response.json()
    for diagnosis in body["diagnoses"]:
        assert set(diagnosis.keys()) == {"description", "diagnosed_at"}
    for lab in body["lab_results"]:
        assert set(lab.keys()) == {
            "test_name", "value", "unit", "reference_low", "reference_high", "measured_at", "status"
        }
    for prescription_out in body["prescriptions"]:
        assert set(prescription_out.keys()) == {"medication_name", "dosage", "prescribed_at"}
    for allergy_out in body["allergies"]:
        assert set(allergy_out.keys()) == {"substance", "reaction", "severity"}


def test_detail_404_for_nonexistent_report(db_session, override_get_db):
    seed(db_session)
    token = _login(PATIENT1_EMAIL)

    response = client.get("/patient/reports/999999", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.json()["detail"] == "보고서를 찾을 수 없거나 조회할 수 없습니다."


def test_detail_404_for_another_patients_report(db_session, override_get_db):
    seed(db_session)
    patient2 = _patient_by_mrn(db_session, "SYN-0002")
    ortho_token = _login(ORTHOPEDIC_DOCTOR_EMAIL)
    other_report = _approved_report(
        ortho_token, patient2.id, _encounter_ids(db_session, patient2.id)[0]
    )

    patient1_token = _login(PATIENT1_EMAIL)
    response = client.get(
        f"/patient/reports/{other_report['id']}", headers=_auth_header(patient1_token)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "보고서를 찾을 수 없거나 조회할 수 없습니다."


def test_detail_404_for_own_draft_report(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    draft = _create_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{draft['id']}", headers=_auth_header(patient_token))

    assert response.status_code == 404
    assert response.json()["detail"] == "보고서를 찾을 수 없거나 조회할 수 없습니다."


def test_detail_404_for_own_rejected_report(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    created = _create_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])
    rejected = _reject(created["id"], doctor_token)

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{rejected['id']}", headers=_auth_header(patient_token))

    assert response.status_code == 404
    assert response.json()["detail"] == "보고서를 찾을 수 없거나 조회할 수 없습니다."


def test_detail_requires_patient_role(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])

    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(doctor_token))

    assert response.status_code == 403


def test_detail_requires_authentication(db_session, override_get_db):
    seed(db_session)

    response = client.get("/patient/reports/1")

    assert response.status_code in (401, 422)


# ============================== 근거 변환 ====================================


def test_detail_evidence_uses_the_required_phrasing(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    first_encounter_id = _encounter_ids(db_session, patient.id)[0]
    approved = _approved_report(doctor_token, patient.id, first_encounter_id)

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))
    evidence = response.json()["evidence"]

    assert "2026년 3월 10일 내분비내과 진료 방문" in evidence
    assert "2026년 3월 10일 내분비내과 진단 기록" in evidence
    assert "2026년 3월 10일 내분비내과 HbA1c 검사" in evidence
    assert "2026년 3월 10일 내분비내과 Fasting Glucose 검사" in evidence
    assert "2026년 3월 10일 내분비내과 처방 기록" in evidence
    assert "2026년 1월 1일 알레르기 기록" in evidence  # 환자 레벨 Allergy.recorded_at


def test_detail_evidence_excludes_clinical_note_and_safety_alert(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _encounter_ids(db_session, patient.id)[0]
    prescription = db_session.query(Prescription).filter_by(encounter_id=encounter_id).first()
    db_session.add(
        SafetyAlert(
            encounter_id=encounter_id,
            prescription_id=prescription.id,
            lab_result_id=None,
            rule_id="ALLERGY_DRUG_CONFLICT",
            evidence={"substance": "Penicillin"},
            priority=SafetyAlertPriority.HIGH,
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    approved = _approved_report(doctor_token, patient.id, encounter_id)
    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))
    evidence = response.json()["evidence"]

    # ClinicalNote/SafetyAlert 관련 문구가 근거 목록에 전혀 없어야 한다 —
    # 이 스코프의 clinical_note/safety_alert record는 seed와 위에서 만든
    # SafetyAlert를 합쳐 반드시 존재하므로, "애초에 없어서 안 보이는 것"이
    # 아니라 "있어도 걸러진다"를 검증한다.
    assert not any("안전" in item or "진료기록 미리보기" in item for item in evidence)
    assert len(evidence) == len(set(evidence))  # 중복 제거 확인


def test_detail_evidence_never_leaks_a_raw_internal_id_on_lookup_failure(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])

    report = db_session.query(ClinicalReport).filter_by(id=approved["id"]).first()
    tampered_content = dict(report.content)
    tampered_content["emr_snapshot"] = dict(tampered_content["emr_snapshot"])
    tampered_content["emr_snapshot"]["source_record_ids"] = [
        *tampered_content["emr_snapshot"]["source_record_ids"],
        "lab_result:999999",  # 스냅샷 안 어디에도 없는 존재하지 않는 id
    ]
    report.content = tampered_content
    db_session.commit()

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))

    assert response.status_code == 200
    assert "999999" not in response.text


# ============================== 스냅샷 전용 처리 =============================


def test_detail_uses_the_frozen_snapshot_not_a_fresh_db_query(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _encounter_ids(db_session, patient.id)[0]
    approved = _approved_report(doctor_token, patient.id, encounter_id)

    # 승인 이후 원본 LabResult 값을 직접 바꾼다 — 응답이 그대로면 저장된
    # 스냅샷만 쓴다는 뜻이고, 바뀐 값이 나오면 원본을 재조회한다는 뜻이다.
    lab_result = db_session.query(LabResult).filter_by(encounter_id=encounter_id, test_name="HbA1c").first()
    original_value = lab_result.value
    lab_result.value = 999.0
    db_session.commit()

    patient_token = _login(PATIENT1_EMAIL)
    response = client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))

    body = response.json()
    hba1c = next(lr for lr in body["lab_results"] if lr["test_name"] == "HbA1c")
    assert hba1c["value"] == original_value
    assert hba1c["value"] != 999.0


# ============================== 감사 로그 ====================================


def test_detail_success_writes_exactly_one_view_report_audit_log(db_session, override_get_db):
    seed(db_session)
    patient = _patient_by_mrn(db_session, "SYN-0001")
    doctor_token = _login(ENDOCRINE_DOCTOR_EMAIL)
    approved = _approved_report(doctor_token, patient.id, _encounter_ids(db_session, patient.id)[0])
    patient_user = db_session.query(User).filter_by(email=PATIENT1_EMAIL).first()

    patient_token = _login(PATIENT1_EMAIL)
    before = db_session.query(AuditLog).count()
    client.get(f"/patient/reports/{approved['id']}", headers=_auth_header(patient_token))

    logs = (
        db_session.query(AuditLog)
        .filter_by(action="VIEW_REPORT", resource_id=str(approved["id"]))
        .order_by(AuditLog.id.desc())
        .all()
    )
    assert db_session.query(AuditLog).count() == before + 1
    newest = logs[0]
    assert newest.actor_user_id == patient_user.id
    assert newest.resource_type == "ClinicalReport"
    assert newest.patient_id == patient.id
    assert newest.reason == "patient_report_view"


def test_detail_failed_lookup_writes_no_audit_log(db_session, override_get_db):
    seed(db_session)
    token = _login(PATIENT1_EMAIL)
    before = db_session.query(AuditLog).count()

    client.get("/patient/reports/999999", headers=_auth_header(token))

    assert db_session.query(AuditLog).count() == before

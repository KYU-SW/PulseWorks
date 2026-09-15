import re

from app.models import (
    Allergy,
    ClinicalNote,
    Department,
    Diagnosis,
    Encounter,
    EncounterType,
    LabResult,
    Order,
    Patient,
    PatientAssignment,
    Prescription,
    Role,
    SourceType,
    User,
)
from scripts.seed_synthetic_data import seed

# A crude but real check for Korean resident-registration-number-shaped
# strings (YYMMDD-NXXXXXX), to catch anything that looks like it could be
# a real person's RRN if it ever slipped into a synthetic text field.
_RRN_PATTERN = re.compile(r"\d{6}-[1-4]\d{6}")


def _all_text_fields(db_session):
    fields = []
    for patient in db_session.query(Patient).all():
        fields.append(patient.full_name)
    for user in db_session.query(User).all():
        fields.append(user.full_name)
        fields.append(user.email)
    for diagnosis in db_session.query(Diagnosis).all():
        fields.append(diagnosis.description)
    for note in db_session.query(ClinicalNote).all():
        fields.append(note.note_text)
    return fields


# 1. 합성 사용자와 5개 역할이 생성되는지
def test_seed_creates_a_user_for_every_role(db_session):
    seed(db_session)

    roles_present = {u.role for u in db_session.query(User).all()}
    assert roles_present == {
        Role.DOCTOR,
        Role.NURSE,
        Role.ADMIN_STAFF,
        Role.SYSTEM_ADMIN,
        Role.PATIENT,
    }


# 2 & 3. 합성 환자가 최소 10명 생성되는지, MRN이 SYN- 형식인지
def test_seed_creates_at_least_ten_patients_with_syn_mrn(db_session):
    seed(db_session)

    patients = db_session.query(Patient).all()
    assert len(patients) >= 10
    assert all(p.mrn.startswith("SYN-") for p in patients)


# 4. 이메일이 example.test 도메인을 사용하는지
def test_seed_user_emails_use_example_test_domain(db_session):
    seed(db_session)

    users = db_session.query(User).all()
    assert len(users) > 0
    assert all(u.email.endswith("@example.test") for u in users)


# 5 & 6. Patient-Encounter, Encounter-(Diagnosis/Order/LabResult/Prescription/ClinicalNote) 관계
def test_endocrinology_core_patient_has_full_encounter_chain(db_session):
    seed(db_session)

    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    assert patient is not None

    encounters = (
        db_session.query(Encounter)
        .filter_by(patient_id=patient.id, department=Department.ENDOCRINOLOGY)
        .all()
    )
    assert len(encounters) == 3

    for encounter in encounters:
        assert encounter.patient_id == patient.id
        diagnoses = db_session.query(Diagnosis).filter_by(encounter_id=encounter.id).all()
        orders = db_session.query(Order).filter_by(encounter_id=encounter.id).all()
        lab_results = db_session.query(LabResult).filter_by(encounter_id=encounter.id).all()
        assert len(diagnoses) >= 1
        assert len(orders) >= 1
        assert len(lab_results) >= 1
        for lab in lab_results:
            if lab.order_id is not None:
                assert lab.order_id in {o.id for o in orders}

    prescriptions = (
        db_session.query(Prescription)
        .join(Encounter, Prescription.encounter_id == Encounter.id)
        .filter(Encounter.patient_id == patient.id)
        .all()
    )
    notes = (
        db_session.query(ClinicalNote)
        .join(Encounter, ClinicalNote.encounter_id == Encounter.id)
        .filter(Encounter.patient_id == patient.id)
        .all()
    )
    assert len(prescriptions) >= 1
    assert len(notes) >= 1


# 7. Allergy가 Encounter가 아니라 Patient에 연결되는지
def test_allergy_is_linked_to_patient_not_encounter(db_session):
    seed(db_session)

    assert not hasattr(Allergy, "encounter_id")

    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    allergies = db_session.query(Allergy).filter_by(patient_id=patient.id).all()
    assert len(allergies) >= 1
    assert all(a.patient_id == patient.id for a in allergies)


# 8. PatientAssignment가 의료진과 환자를 연결하는지
def test_patient_assignment_links_doctor_and_nurse_to_core_patient(db_session):
    seed(db_session)

    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    doctor = db_session.query(User).filter_by(email="endocrine.doctor@example.test").first()
    nurse = db_session.query(User).filter_by(email="nurse1@example.test").first()
    assert doctor is not None
    assert nurse is not None

    assignments = db_session.query(PatientAssignment).filter_by(patient_id=patient.id).all()
    staff_ids = {a.staff_user_id for a in assignments}
    assert doctor.id in staff_ids
    assert nurse.id in staff_ids


# 9. 내분비내과 환자에게 시계열 HbA1c 데이터가 존재하는지 (연속 상승)
def test_endocrinology_patient_has_rising_hba1c_series(db_session):
    seed(db_session)

    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    hba1c_results = (
        db_session.query(LabResult)
        .join(Encounter, LabResult.encounter_id == Encounter.id)
        .filter(Encounter.patient_id == patient.id, LabResult.test_name == "HbA1c")
        .order_by(LabResult.measured_at)
        .all()
    )
    assert len(hba1c_results) == 3
    values = [r.value for r in hba1c_results]
    assert values == sorted(values)
    assert values[0] < values[-1]
    assert all(r.is_abnormal for r in hba1c_results)


# 10. 정형외과 시나리오 데이터가 존재하는지
def test_orthopedics_scenario_data_exists(db_session):
    seed(db_session)

    patient = db_session.query(Patient).filter_by(mrn="SYN-0002").first()
    assert patient is not None

    encounter = (
        db_session.query(Encounter)
        .filter_by(patient_id=patient.id, department=Department.ORTHOPEDICS)
        .first()
    )
    assert encounter is not None

    diagnosis = db_session.query(Diagnosis).filter_by(encounter_id=encounter.id).first()
    imaging_order = (
        db_session.query(Order)
        .filter(Order.encounter_id == encounter.id, Order.test_name.ilike("%X-ray%"))
        .first()
    )
    imaging_note = (
        db_session.query(ClinicalNote)
        .filter(ClinicalNote.encounter_id == encounter.id, ClinicalNote.note_text.contains("영상검사"))
        .first()
    )
    prescription = db_session.query(Prescription).filter_by(encounter_id=encounter.id).first()

    assert diagnosis is not None
    assert imaging_order is not None
    assert imaging_note is not None
    assert prescription is not None


# 11. 응급의학과 시나리오 데이터가 존재하는지
def test_emergency_scenario_data_exists(db_session):
    seed(db_session)

    patient = db_session.query(Patient).filter_by(mrn="SYN-0003").first()
    assert patient is not None

    encounter = (
        db_session.query(Encounter)
        .filter_by(
            patient_id=patient.id,
            department=Department.EMERGENCY_MEDICINE,
            encounter_type=EncounterType.EMERGENCY,
        )
        .first()
    )
    assert encounter is not None

    lab_results = db_session.query(LabResult).filter_by(encounter_id=encounter.id).all()
    assert any(lr.is_abnormal for lr in lab_results)
    assert len(lab_results) >= 2  # 활력징후성 측정 + 우선 확인 필요 검사

    diagnosis = db_session.query(Diagnosis).filter_by(encounter_id=encounter.id).first()
    note = db_session.query(ClinicalNote).filter_by(encounter_id=encounter.id).first()
    assert diagnosis is not None
    assert note is not None


# 12. 모든 DateTime 데이터가 timezone-aware인지
#
# 이 검증은 SQLite 라운드트립이 아니라 seed 스크립트 소스 자체를 정적으로
# 검사한다. 이유: SQLAlchemy 2.0의 SQLite bulk-insert(RETURNING 기반
# insertmanyvalues) 최적화는, 같은 테이블에 여러 행을 한 번에 넣을 때 SQLite가
# timezone 오프셋을 저장/반환하지 않는 탓에 이미 명시적으로 tzinfo를 넣은
# Python 값까지도 다시 읽어오면서 naive로 덮어써 버린다(실측 확인됨). 즉 이
# 손실은 seed 스크립트의 버그가 아니라 테스트용 SQLite 저장 계층의 한계이며,
# 실제 PostgreSQL은 `timestamp with time zone`을 올바르게 보존한다(Task 3에서
# 이미 확인, 이번 Task의 실제 Postgres 실행 단계에서 재확인함).
#
# 따라서 여기서는 "seed 스크립트가 naive datetime을 만들지 않는지"를 실제로
# 의미 있게 검증하기 위해, 소스 코드에서 `datetime(` 생성자가 쓰인 모든 곳이
# `tzinfo=`를 포함하는지 정적으로 확인한다.
def test_seed_script_never_constructs_naive_datetime(db_session):
    import inspect
    import re

    import scripts.seed_synthetic_data as seed_module

    source = inspect.getsource(seed_module)
    # date(...)처럼 다른 호출과 섞이지 않도록 `datetime(` 호출만 검사한다.
    # (seed 스크립트에서 datetime(...)을 직접 부르는 곳은 _utc() 헬퍼 정의
    # 한 곳뿐이어야 하며, 나머지는 전부 _utc(...)를 거쳐야 한다.)
    bare_datetime_calls = re.findall(r"\bdatetime\(([^)]*)\)", source)
    assert bare_datetime_calls, "seed 스크립트에서 datetime( 호출을 찾을 수 없음 — 테스트가 무의미해짐"
    for call_args in bare_datetime_calls:
        assert "tzinfo=" in call_args, f"naive datetime( 생성자 발견: datetime({call_args})"


# 12-b. 실제로 seed()가 만들어내는 값도(SQLite 라운드트립 전, 커밋 직전 시점에서)
# timezone-aware인지 최소 한 군데는 실행 시점에 직접 확인한다.
def test_utc_helper_returns_timezone_aware_datetime():
    from scripts.seed_synthetic_data import _utc

    result = _utc(2026, 1, 1, 9, 0)
    assert result.tzinfo is not None
    from datetime import timezone

    assert result.utcoffset() == timezone.utc.utcoffset(None)


# 13. source_type이 데이터 생성 주체에 맞게 설정되어 있는지 (전부 동일값이면 안 됨)
def test_source_type_distinguishes_patient_reported_from_institution_generated(db_session):
    seed(db_session)

    all_source_types = set()
    for model in (Diagnosis, Order, LabResult, Prescription, ClinicalNote, Allergy):
        for row in db_session.query(model).all():
            all_source_types.add(row.source_type)

    assert SourceType.INSTITUTION_GENERATED in all_source_types
    assert SourceType.PATIENT_REPORTED in all_source_types

    patient_reported_lab = (
        db_session.query(LabResult).filter_by(source_type=SourceType.PATIENT_REPORTED).first()
    )
    assert patient_reported_lab is not None
    assert patient_reported_lab.order_id is None  # 환자 자가측정은 institution Order가 없음


# 14. Seed를 두 번 실행해도 레코드가 중복되지 않는지 (idempotent)
def test_running_seed_twice_does_not_duplicate_records(db_session):
    seed(db_session)

    counts_after_first_run = {
        "users": db_session.query(User).count(),
        "patients": db_session.query(Patient).count(),
        "assignments": db_session.query(PatientAssignment).count(),
        "encounters": db_session.query(Encounter).count(),
        "diagnoses": db_session.query(Diagnosis).count(),
        "orders": db_session.query(Order).count(),
        "lab_results": db_session.query(LabResult).count(),
        "prescriptions": db_session.query(Prescription).count(),
        "notes": db_session.query(ClinicalNote).count(),
        "allergies": db_session.query(Allergy).count(),
    }
    assert all(v > 0 for v in counts_after_first_run.values())

    seed(db_session)

    counts_after_second_run = {
        "users": db_session.query(User).count(),
        "patients": db_session.query(Patient).count(),
        "assignments": db_session.query(PatientAssignment).count(),
        "encounters": db_session.query(Encounter).count(),
        "diagnoses": db_session.query(Diagnosis).count(),
        "orders": db_session.query(Order).count(),
        "lab_results": db_session.query(LabResult).count(),
        "prescriptions": db_session.query(Prescription).count(),
        "notes": db_session.query(ClinicalNote).count(),
        "allergies": db_session.query(Allergy).count(),
    }

    assert counts_after_second_run == counts_after_first_run


# 15. 실제 환자정보(주민등록번호 형태 등)로 의심되는 데이터가 없는지
def test_no_resident_registration_number_shaped_data(db_session):
    seed(db_session)

    for text in _all_text_fields(db_session):
        assert not _RRN_PATTERN.search(text), f"RRN-like pattern found in: {text!r}"

    # 스키마 자체에도 주민등록번호 필드가 없어야 한다.
    assert not hasattr(Patient, "ssn")
    assert not hasattr(Patient, "resident_registration_number")

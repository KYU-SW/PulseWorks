from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enums import Department, Role, SourceType, SafetyAlertPriority
from app.models.user import User
from app.models.patient import Patient
from app.models.encounter import Encounter, EncounterType
from app.models.clinical import Diagnosis
from app.models.safety_alert import SafetyAlert


def test_create_patient_encounter_and_user(db_session):
    patient = Patient(
        mrn="SYN-0001",
        full_name="홍길동",
        birth_date=date(1970, 1, 1),
        sex="M",
    )
    db_session.add(patient)
    db_session.flush()

    doctor = User(
        email="doctor1@example.org",
        hashed_password="x",
        full_name="김의사",
        role=Role.DOCTOR,
        department=Department.ENDOCRINOLOGY,
    )
    db_session.add(doctor)
    db_session.flush()

    encounter = Encounter(
        patient_id=patient.id,
        department=Department.ENDOCRINOLOGY,
        encounter_type=EncounterType.OUTPATIENT,
        start_time=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        created_by_user_id=doctor.id,
    )
    db_session.add(encounter)
    db_session.commit()

    assert encounter.id is not None
    assert encounter.patient_id == patient.id
    assert doctor.role == Role.DOCTOR


def _make_patient_and_encounter(db_session):
    patient = Patient(
        mrn="SYN-1000", full_name="정환자", birth_date=date(1965, 3, 20), sex="F"
    )
    db_session.add(patient)
    db_session.flush()

    doctor = User(
        email="doctor2@example.org",
        hashed_password="x",
        full_name="이의사",
        role=Role.DOCTOR,
        department=Department.ENDOCRINOLOGY,
    )
    db_session.add(doctor)
    db_session.flush()

    encounter = Encounter(
        patient_id=patient.id,
        department=Department.ENDOCRINOLOGY,
        encounter_type=EncounterType.OUTPATIENT,
        start_time=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
        created_by_user_id=doctor.id,
    )
    db_session.add(encounter)
    db_session.commit()
    return patient, doctor, encounter


def test_clinical_record_has_source_type_and_audit_timestamps(db_session):
    """모든 임상 레코드(source_type을 가진 6개 테이블)는 source_type과
    created_at/updated_at(레코드 자체의 생성·수정 시각)을 가져야 한다."""
    _, _, encounter = _make_patient_and_encounter(db_session)

    diagnosis = Diagnosis(
        encounter_id=encounter.id,
        code="E11.9",
        description="2형 당뇨병 (합성 데이터)",
        diagnosed_at=datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc),
        source_type=SourceType.INSTITUTION_GENERATED,
    )
    db_session.add(diagnosis)
    db_session.commit()
    db_session.refresh(diagnosis)

    assert diagnosis.source_type == SourceType.INSTITUTION_GENERATED
    assert diagnosis.created_at is not None
    assert diagnosis.updated_at is not None


def test_deleting_patient_with_encounter_is_restricted(db_session):
    """Encounter.patient_id는 NOT NULL FK이므로 ON DELETE RESTRICT다 —
    담당 Encounter가 있는 Patient는 실수로 삭제될 수 없어야 한다."""
    patient, _, _encounter = _make_patient_and_encounter(db_session)

    db_session.delete(patient)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_safety_alert_requires_at_least_one_evidence_link(db_session):
    """SafetyAlert는 prescription_id 또는 lab_result_id 중 최소 하나는
    있어야 한다 (근거 없는 안전 알림 방지) — CHECK 제약으로 강제."""
    _, _, encounter = _make_patient_and_encounter(db_session)

    alert = SafetyAlert(
        encounter_id=encounter.id,
        prescription_id=None,
        lab_result_id=None,
        rule_id="ALLERGY_DRUG_CONFLICT",
        evidence={},
        priority=SafetyAlertPriority.HIGH,
        created_at=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(alert)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

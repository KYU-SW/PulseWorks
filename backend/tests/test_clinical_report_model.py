from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    ClinicalReport,
    ClinicalReportScopeType,
    ClinicalReportStatus,
    ClinicalReportType,
    Encounter,
    Patient,
    User,
)
from scripts.seed_synthetic_data import seed

_MINIMAL_CONTENT = {
    "emr_snapshot": {
        "patient": {}, "encounters": [], "diagnoses": [], "lab_results": [],
        "lab_trends": [], "prescriptions": [], "allergies": [],
        "safety_alerts": [], "clinical_notes": [], "source_record_ids": [],
    },
    "narrative": None, "handoff_note": None, "patient_guidance": None,
}


def _ids(db_session):
    seed(db_session)
    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    encounter = db_session.query(Encounter).filter_by(patient_id=patient.id).first()
    doctor = db_session.query(User).filter_by(email="endocrine.doctor@example.test").first()
    return patient.id, encounter.id, doctor.id


def _draft(patient_id, base_encounter_id, doctor_id, **overrides) -> ClinicalReport:
    now = datetime.now(timezone.utc)
    fields = dict(
        patient_id=patient_id,
        encounter_id=base_encounter_id,
        report_type=ClinicalReportType.DOCTOR_REFERENCE,
        scope_type=ClinicalReportScopeType.SINGLE_ENCOUNTER,
        scope_encounter_ids=[base_encounter_id],
        status=ClinicalReportStatus.DRAFT,
        content=_MINIMAL_CONTENT,
        created_by_user_id=doctor_id,
        created_at=now,
        last_modified_by_user_id=doctor_id,
        last_modified_at=now,
        reviewed_by_user_id=None,
        reviewed_at=None,
        supersedes_report_id=None,
    )
    fields.update(overrides)
    return ClinicalReport(**fields)


# 1. 전체 컬럼과 Enum 확인
def test_all_columns_and_enums_round_trip(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(patient_id, encounter_id, doctor_id)
    db_session.add(report)
    db_session.commit()

    fetched = db_session.query(ClinicalReport).filter_by(id=report.id).first()
    assert fetched.patient_id == patient_id
    assert fetched.encounter_id == encounter_id
    assert fetched.report_type == ClinicalReportType.DOCTOR_REFERENCE
    assert fetched.scope_type == ClinicalReportScopeType.SINGLE_ENCOUNTER
    assert fetched.scope_encounter_ids == [encounter_id]
    assert fetched.status == ClinicalReportStatus.DRAFT
    assert fetched.content == _MINIMAL_CONTENT
    assert fetched.created_by_user_id == doctor_id
    assert fetched.last_modified_by_user_id == doctor_id
    assert fetched.reviewed_by_user_id is None
    assert fetched.reviewed_at is None
    assert fetched.supersedes_report_id is None


# 2. 모든 FK와 삭제정책 확인 (RESTRICT 쪽)
def test_patient_with_report_cannot_be_deleted(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    db_session.add(_draft(patient_id, encounter_id, doctor_id))
    db_session.commit()

    patient = db_session.query(Patient).filter_by(id=patient_id).first()
    db_session.delete(patient)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_created_by_user_with_report_cannot_be_deleted(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    db_session.add(_draft(patient_id, encounter_id, doctor_id))
    db_session.commit()

    doctor = db_session.query(User).filter_by(id=doctor_id).first()
    db_session.delete(doctor)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 3. DRAFT는 reviewed 필드 없이 저장 가능
def test_draft_without_reviewed_fields_is_valid(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(patient_id, encounter_id, doctor_id)
    db_session.add(report)
    db_session.commit()  # 예외 없이 통과해야 함


# 4. APPROVED인데 reviewed_at이 없으면 CHECK 실패
def test_approved_without_reviewed_at_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        status=ClinicalReportStatus.APPROVED, reviewed_at=None,
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 5. REJECTED인데 reviewed_at이 없으면 CHECK 실패
def test_rejected_without_reviewed_at_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        status=ClinicalReportStatus.REJECTED, reviewed_at=None,
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 6. DRAFT인데 reviewed_at이 있으면 CHECK 실패
def test_draft_with_reviewed_at_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        status=ClinicalReportStatus.DRAFT, reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# APPROVED + reviewed_at 있으면 정상 저장 (CHECK가 과하게 막지 않는지 확인)
def test_approved_with_reviewed_at_is_valid(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    now = datetime.now(timezone.utc)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        status=ClinicalReportStatus.APPROVED,
        reviewed_by_user_id=doctor_id,
        reviewed_at=now,
    )
    db_session.add(report)
    db_session.commit()  # 예외 없이 통과해야 함


# 7. reviewed_by User 삭제 시 SET NULL 가능 & 8. 검토자 계정 삭제 후 보고서 유지
def test_reviewer_deletion_sets_null_and_report_survives(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    now = datetime.now(timezone.utc)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        status=ClinicalReportStatus.APPROVED,
        reviewed_by_user_id=doctor_id,
        reviewed_at=now,
        created_by_user_id=doctor_id,
        last_modified_by_user_id=doctor_id,
    )
    db_session.add(report)
    db_session.commit()
    report_id = report.id

    # created_by_user_id도 이 doctor를 참조하므로, 검토자 SET NULL만 따로
    # 확인하려면 reviewed_by_user_id만 다른(삭제 가능한) 계정으로 바꿔야
    # 한다 — 별도 의사 계정을 만들어 검토자로 지정한다.
    from app.models import Role

    reviewer = User(
        email="reviewer-only@example.test",
        hashed_password="x",
        full_name="검토자용 임시 계정",
        role=Role.DOCTOR,
    )
    db_session.add(reviewer)
    db_session.flush()
    report.reviewed_by_user_id = reviewer.id
    db_session.commit()

    db_session.delete(reviewer)
    db_session.commit()  # SET NULL이므로 예외 없이 성공해야 함
    # ON DELETE SET NULL은 DB가 직접 적용하는 것이라 ORM의 이미 로드된
    # 객체(session identity map)는 갱신되지 않는다(conftest의
    # expire_on_commit=False) — 명시적으로 새로 읽어와야 한다.
    db_session.expire_all()

    survived = db_session.query(ClinicalReport).filter_by(id=report_id).first()
    assert survived is not None
    assert survived.reviewed_by_user_id is None
    # SQLite는 DATETIME에 timezone 오프셋을 보존하지 않는다(conftest.py 설명
    # 참고) — expire_all() 이후 다시 읽은 값은 naive이므로 naive로 비교한다.
    assert survived.reviewed_at.replace(tzinfo=None) == now.replace(tzinfo=None)


# 9. SINGLE_ENCOUNTER인데 encounter_id가 없으면 CHECK 실패
def test_single_encounter_without_encounter_id_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        scope_type=ClinicalReportScopeType.SINGLE_ENCOUNTER,
        encounter_id=None,
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 10. PERIOD 또는 FULL_HISTORY인데 encounter_id가 있으면 CHECK 실패
def test_period_with_encounter_id_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        scope_type=ClinicalReportScopeType.PERIOD,
        encounter_id=encounter_id,
        scope_encounter_ids=[encounter_id],
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_full_history_with_encounter_id_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(
        patient_id, encounter_id, doctor_id,
        scope_type=ClinicalReportScopeType.FULL_HISTORY,
        encounter_id=encounter_id,
        scope_encounter_ids=[encounter_id],
    )
    db_session.add(report)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 11. supersedes_report_id 자기 자신 참조 실패
def test_self_supersede_violates_check(db_session):
    patient_id, encounter_id, doctor_id = _ids(db_session)
    report = _draft(patient_id, encounter_id, doctor_id)
    db_session.add(report)
    db_session.flush()

    report.supersedes_report_id = report.id
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

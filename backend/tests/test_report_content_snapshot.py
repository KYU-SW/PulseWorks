from app.models import Encounter, Patient
from app.schemas.clinical_report import EmrSnapshot, ReportContentSnapshot
from app.services.report_data import collect_report_data
from scripts.seed_synthetic_data import seed


def _first_encounter_report_data(db_session):
    seed(db_session)
    patient = db_session.query(Patient).filter_by(mrn="SYN-0001").first()
    encounter = (
        db_session.query(Encounter)
        .filter_by(patient_id=patient.id)
        .order_by(Encounter.start_time)
        .first()
    )
    return collect_report_data(db_session, patient.id, [encounter.id])


# 12. ReportContentSnapshot 전체 검증
def test_report_content_snapshot_validates_full_report_data(db_session):
    report_data = _first_encounter_report_data(db_session)

    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data),
        narrative=None,
        handoff_note=None,
        patient_guidance=None,
    )

    assert snapshot.emr_snapshot.patient.mrn == "SYN-0001"
    assert len(snapshot.emr_snapshot.diagnoses) == 1
    assert {lr.test_name for lr in snapshot.emr_snapshot.lab_results} == {
        "HbA1c", "Fasting Glucose",
    }


# 13. date와 datetime JSON 직렬화
def test_date_and_datetime_serialize_to_iso_strings(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )

    dumped = snapshot.model_dump(mode="json")

    assert isinstance(dumped["emr_snapshot"]["patient"]["birth_date"], str)
    assert isinstance(dumped["emr_snapshot"]["diagnoses"][0]["diagnosed_at"], str)
    # ISO 8601 형식(연-월-일)인지 최소 확인
    assert dumped["emr_snapshot"]["patient"]["birth_date"][:1].isdigit()
    assert "T" in dumped["emr_snapshot"]["diagnoses"][0]["diagnosed_at"]


# 14. nested list JSON round-trip
def test_nested_lists_round_trip_through_json(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )

    dumped = snapshot.model_dump(mode="json")
    reparsed = ReportContentSnapshot.model_validate(dumped)

    assert len(reparsed.emr_snapshot.lab_results) == len(report_data.lab_results)
    assert len(reparsed.emr_snapshot.lab_trends) == len(report_data.lab_trends)
    hba1c_group = next(g for g in reparsed.emr_snapshot.lab_trends if g.test_name == "HbA1c")
    assert [p.value for p in hba1c_group.points] == [7.2]
    assert reparsed.emr_snapshot.source_record_ids == report_data.source_record_ids


# 15. 저장 후 재조회 및 재검증 (JSON dict를 다시 검증)
def test_stored_dict_can_be_reparsed_after_round_trip(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )
    stored_dict = snapshot.model_dump(mode="json")  # DB JSON 컬럼에 저장될 형태

    reloaded = ReportContentSnapshot.model_validate(stored_dict)
    assert reloaded.emr_snapshot.patient.id == report_data.patient.id


# 16. narrative, handoff_note, patient_guidance 초기값 None
def test_narrative_fields_default_to_none(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )

    assert snapshot.narrative is None
    assert snapshot.handoff_note is None
    assert snapshot.patient_guidance is None

    dumped = snapshot.model_dump(mode="json")
    assert dumped["narrative"] is None
    assert dumped["handoff_note"] is None
    assert dumped["patient_guidance"] is None


# Task D1: narrative_source/narrative_edited_by_clinician - 선택적
# 메타데이터라 Migration 없이 기존 JSON도 기본값으로 파싱된다.
def test_narrative_source_and_edited_default_when_absent_from_stored_json(db_session):
    report_data = _first_encounter_report_data(db_session)
    # 이 필드들이 아예 없는 "기존 저장 데이터" 모양을 그대로 흉내낸다.
    legacy_stored_dict = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    ).model_dump(mode="json")
    del legacy_stored_dict["narrative_source"]
    del legacy_stored_dict["narrative_edited_by_clinician"]

    reparsed = ReportContentSnapshot.model_validate(legacy_stored_dict)

    assert reparsed.narrative_source is None
    assert reparsed.narrative_edited_by_clinician is False


# Task F4-B: VitalSign이 EmrSnapshot에 동결된다.
def test_vital_signs_are_included_in_the_snapshot(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = EmrSnapshot.model_validate(report_data)

    assert len(snapshot.vital_signs) == 7
    assert {v.vital_type for v in snapshot.vital_signs} == {
        "BLOOD_PRESSURE", "BODY_HEIGHT", "BODY_WEIGHT", "BODY_TEMPERATURE",
        "HEART_RATE", "RESPIRATORY_RATE", "PULSE_OXIMETRY",
    }


def test_vital_signs_round_trip_through_json_preserving_decimal_precision(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )

    dumped = snapshot.model_dump(mode="json")
    reparsed = ReportContentSnapshot.model_validate(dumped)

    bp = next(v for v in reparsed.emr_snapshot.vital_signs if v.vital_type == "BLOOD_PRESSURE")
    # Numeric(10,3) 컬럼이 저장 시 소수점 3자리로 맞추므로 "120.000"이다 —
    # 정밀도 보존(F4-A에서 이미 확인된 Decimal API 계약).
    assert str(bp.value) == "120.000"
    assert str(bp.value_secondary) == "80.000"
    assert bp.unit == "mmHg"


# Task F4-B: vital_signs가 아예 없는 과거 Snapshot도 기본값([])으로 파싱된다
# (Task D1의 narrative_source/narrative_edited_by_clinician과 동일한 원칙).
def test_vital_signs_defaults_to_empty_list_when_absent_from_stored_json(db_session):
    report_data = _first_encounter_report_data(db_session)
    legacy_stored_dict = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    ).model_dump(mode="json")
    del legacy_stored_dict["emr_snapshot"]["vital_signs"]

    reparsed = ReportContentSnapshot.model_validate(legacy_stored_dict)

    assert reparsed.emr_snapshot.vital_signs == []


def test_narrative_source_and_edited_round_trip_through_json(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative="x",
        handoff_note=None, patient_guidance=None,
        narrative_source="llm", narrative_edited_by_clinician=True,
    )

    reparsed = ReportContentSnapshot.model_validate(snapshot.model_dump(mode="json"))

    assert reparsed.narrative_source == "llm"
    assert reparsed.narrative_edited_by_clinician is True


# 17. 비밀번호와 비밀정보가 content에 없음
def test_content_never_contains_secrets(db_session):
    report_data = _first_encounter_report_data(db_session)
    snapshot = ReportContentSnapshot(
        emr_snapshot=EmrSnapshot.model_validate(report_data), narrative=None,
        handoff_note=None, patient_guidance=None,
    )
    dumped_text = str(snapshot.model_dump(mode="json"))

    assert "hashed_password" not in dumped_text
    assert "password" not in dumped_text
    assert "JWT_SECRET" not in dumped_text

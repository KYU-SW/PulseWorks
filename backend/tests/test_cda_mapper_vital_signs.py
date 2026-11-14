"""HL7-4A §13/§14: VitalSign mapper + Blood Pressure organizer TDD."""

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.clinical_report import SnapshotVitalSign
from app.services.cda.errors import CdaWarning
from app.services.cda.models import CdaObservation, CdaOrganizer
from app.services.cda.mapper import build_blood_pressure_entry, map_vital_signs

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
_TS = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)


def _vs(**overrides) -> SnapshotVitalSign:
    base = dict(
        id=1,
        encounter_id=10,
        vital_type="BODY_TEMPERATURE",
        value=Decimal("36.5"),
        value_secondary=None,
        unit="Cel",
        measured_at=_TS,
    )
    base.update(overrides)
    return SnapshotVitalSign.model_validate(base)


class TestSingleValueVitalSigns:
    def test_each_of_the_six_single_value_types_maps_to_an_observation(self):
        cases = [
            ("BODY_HEIGHT", "cm", "8302-2"),
            ("BODY_WEIGHT", "kg", "29463-7"),
            ("BODY_TEMPERATURE", "Cel", "8310-5"),
            ("HEART_RATE", "/min", "8867-4"),
            ("RESPIRATORY_RATE", "/min", "9279-1"),
            ("PULSE_OXIMETRY", "%", "2708-6"),
        ]
        for vital_type, unit, expected_loinc in cases:
            entries, warnings = map_vital_signs(
                (_vs(id=7, vital_type=vital_type, value=Decimal("1"), unit=unit),),
                entry_id_root=_ROOT,
            )
            assert warnings == ()
            assert len(entries) == 1
            obs = entries[0]
            assert isinstance(obs, CdaObservation)
            assert obs.code.code == expected_loinc
            assert obs.identifier.extension == "vital_sign:7"

    def test_unit_is_normalized(self):
        entries, _ = map_vital_signs((_vs(id=8, unit="Cel"),), entry_id_root=_ROOT)
        assert entries[0].value.unit == "Cel"

    def test_effective_time_matches_measured_at(self):
        entries, _ = map_vital_signs((_vs(id=9),), entry_id_root=_ROOT)
        assert entries[0].effective_time.value == _TS


class TestBloodPressureComplete:
    def test_complete_bp_produces_organizer_with_two_observations(self):
        bp = _vs(
            id=20,
            vital_type="BLOOD_PRESSURE",
            value=Decimal("120"),
            value_secondary=Decimal("80"),
            unit="mmHg",
        )
        entries, warnings = map_vital_signs((bp,), entry_id_root=_ROOT)
        assert warnings == ()
        assert len(entries) == 1
        organizer = entries[0]
        assert isinstance(organizer, CdaOrganizer)
        assert organizer.code.code == "85354-9"
        systolic, diastolic = organizer.components
        assert systolic.code.code == "8480-6"
        assert systolic.value.value == "120"
        assert systolic.value.unit == "mm[Hg]"
        assert diastolic.code.code == "8462-4"
        assert diastolic.value.value == "80"
        assert systolic.identifier.extension == "vital_sign:20:systolic"
        assert diastolic.identifier.extension == "vital_sign:20:diastolic"
        assert systolic.effective_time.value == diastolic.effective_time.value == _TS

    def test_same_source_row_derives_deterministic_identifiers_on_repeat_mapping(self):
        bp = _vs(id=21, vital_type="BLOOD_PRESSURE", value=Decimal("110"), value_secondary=Decimal("70"), unit="mmHg")
        entries_a, _ = map_vital_signs((bp,), entry_id_root=_ROOT)
        entries_b, _ = map_vital_signs((bp,), entry_id_root=_ROOT)
        assert entries_a == entries_b


class TestBloodPressureIncomplete:
    """HL7-4A §14의 명시적 정책: 하나라도 없으면 Organizer도, 단일
    systolic/diastolic Observation으로의 재해석도 하지 않고, 해당 BP
    Entry 전체를 생략한다(structured warning만 반환). 이는 HL7-2 초안의
    "단일 Observation으로 승격" 권고보다 더 보수적인, 이번 HL7-4A가
    명시적으로 지정한 정책이다."""

    def test_missing_diastolic_omits_entry_entirely_with_warning(self):
        bp = _vs(id=22, vital_type="BLOOD_PRESSURE", value=Decimal("130"), value_secondary=None, unit="mmHg")
        entries, warnings = map_vital_signs((bp,), entry_id_root=_ROOT)
        assert entries == ()
        assert len(warnings) == 1
        assert isinstance(warnings[0], CdaWarning)
        assert warnings[0].code == "INCOMPLETE_BLOOD_PRESSURE"
        assert warnings[0].source_record_id == "vital_sign:22"
        # 환자 식별정보/실제 측정값이 warning 메시지에 섞이지 않는다.
        assert "SYN" not in warnings[0].message
        assert "130" not in warnings[0].message

    def test_missing_primary_value_omits_bp_entry_entirely_with_warning(self):
        # SnapshotVitalSign.value는 DB NOT NULL이라 실제 데이터로는 이
        # 경우가 생기지 않는다 - 그래서 map_vital_signs()가 아니라 그
        # 아래의 build_blood_pressure_entry() 자체를 직접 호출해 방어적
        # 동작을 확인한다(값이 전혀 없는 수축기를 "발명"하지 않는지).
        entry, warning = build_blood_pressure_entry(
            value=None,
            value_secondary=Decimal("70"),
            source_record_id="vital_sign:23",
            entry_id_root=_ROOT,
            unit="mmHg",
            measured_at=_TS,
        )
        assert entry is None
        assert warning is not None
        assert warning.code == "INCOMPLETE_BLOOD_PRESSURE"

    def test_complete_and_incomplete_do_not_leak_entries_across_rows(self):
        complete = _vs(id=30, vital_type="BLOOD_PRESSURE", value=Decimal("115"), value_secondary=Decimal("75"), unit="mmHg")
        incomplete = _vs(id=31, vital_type="BLOOD_PRESSURE", value=Decimal("140"), value_secondary=None, unit="mmHg")
        entries, warnings = map_vital_signs((complete, incomplete), entry_id_root=_ROOT)
        assert len(entries) == 1
        assert isinstance(entries[0], CdaOrganizer)
        assert len(warnings) == 1
        assert warnings[0].source_record_id == "vital_sign:31"

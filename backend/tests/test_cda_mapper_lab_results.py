"""HL7-4A §16: LabResult mapper TDD."""

import dataclasses
from datetime import datetime, timezone

from app.schemas.clinical_report import SnapshotLabResult
from app.services.cda.mapper import build_reference_range, map_lab_results
from app.services.cda.models import CdaObservation, PhysicalQuantity

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
_TS = datetime(2026, 3, 10, 9, 5, tzinfo=timezone.utc)


def _lab(**overrides) -> SnapshotLabResult:
    base = dict(
        id=1,
        encounter_id=10,
        test_name="HbA1c",
        value=7.2,
        unit="%",
        reference_low=4.0,
        reference_high=6.0,
        measured_at=_TS,
        source_type="DOCTOR",
        status="HIGH",
        rule_id="r1",
    )
    base.update(overrides)
    return SnapshotLabResult.model_validate(base)


class TestLabResultMapper:
    def test_maps_core_fields(self):
        entries = map_lab_results((_lab(),), entry_id_root=_ROOT)
        assert len(entries) == 1
        obs = entries[0]
        assert isinstance(obs, CdaObservation)
        assert obs.identifier.extension == "lab_result:1"
        assert obs.effective_time.value == _TS
        assert obs.value.value == "7.2"

    def test_terminology_is_unknown_with_original_text(self):
        entries = map_lab_results((_lab(test_name="공복혈당"),), entry_id_root=_ROOT)
        code = entries[0].code
        assert code.state == "unknown"
        assert code.null_flavor == "UNK"
        assert code.original_text == "공복혈당"
        # 가짜 code/codeSystem을 넣지 않는다.
        assert code.code is None
        assert code.code_system is None

    def test_full_reference_range_is_included(self):
        entries = map_lab_results((_lab(reference_low=4.0, reference_high=6.0),), entry_id_root=_ROOT)
        obs = entries[0]
        assert obs.reference_range_low == PhysicalQuantity(value="4.0", unit="%")
        assert obs.reference_range_high == PhysicalQuantity(value="6.0", unit="%")

    def test_missing_reference_range_is_not_fabricated(self):
        # SnapshotLabResult.reference_low/high는 DB NOT NULL이라 실제
        # 데이터로는 None이 될 수 없다 - build_reference_range()를 직접
        # 호출해 방어적 동작(거짓 범위를 만들지 않음)을 확인한다.
        low, high = build_reference_range(None, None, unit="%")
        assert low is None
        assert high is None

    def test_partial_reference_range_is_not_fabricated(self):
        low, high = build_reference_range(4.0, None, unit="%")
        assert low is None
        assert high is None

    def test_unknown_unit_is_preserved_raw(self):
        entries = map_lab_results((_lab(unit="mg/dL"),), entry_id_root=_ROOT)
        assert entries[0].value.unit == "mg/dL"

    def test_status_never_leaks_into_structured_entry(self):
        # LabResult.status(LOW/NORMAL/HIGH/UNKNOWN)는 CDA statusCode와
        # 구조적으로 분리되어야 한다 - CdaObservation 타입 자체에
        # status_code/interpretation_code 필드가 없어 leak이 구조적으로
        # 불가능함을 확인한다.
        field_names = {f.name for f in dataclasses.fields(CdaObservation)}
        assert "status_code" not in field_names
        assert "interpretation_code" not in field_names

        entries = map_lab_results((_lab(status="HIGH"),), entry_id_root=_ROOT)
        obs_field_names = {f.name for f in dataclasses.fields(entries[0])}
        assert "status_code" not in obs_field_names

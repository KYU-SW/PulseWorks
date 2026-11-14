"""HL7-4A §17: Diagnosis mapper TDD."""

from datetime import datetime, timezone

from app.schemas.clinical_report import SnapshotDiagnosis
from app.services.cda.mapper import map_diagnoses

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
_TS = datetime(2026, 3, 10, 9, 10, tzinfo=timezone.utc)


def _dx(**overrides) -> SnapshotDiagnosis:
    base = dict(
        id=1,
        encounter_id=10,
        code="E11.9",
        description="2형 당뇨병",
        diagnosed_at=_TS,
        source_type="DOCTOR",
    )
    base.update(overrides)
    return SnapshotDiagnosis.model_validate(base)


class TestDiagnosisMapper:
    def test_raw_code_is_preserved_without_code_system_fabrication(self):
        entries = map_diagnoses((_dx(),), entry_id_root=_ROOT)
        value = entries[0].value
        assert value.state == "raw_unverified"
        assert value.raw_code == "E11.9"
        # KCD/ICD-10/SNOMED 중 하나로 추측하지 않는다 - code_system이
        # 전혀 없다.
        assert value.code_system is None

    def test_description_is_preserved(self):
        entries = map_diagnoses((_dx(description="무릎 관절증"),), entry_id_root=_ROOT)
        assert entries[0].value.original_text == "무릎 관절증"

    def test_diagnosed_at_is_preserved(self):
        entries = map_diagnoses((_dx(),), entry_id_root=_ROOT)
        assert entries[0].effective_time.value == _TS

    def test_observation_kind_code_is_unknown_not_a_fabricated_meta_code(self):
        entries = map_diagnoses((_dx(),), entry_id_root=_ROOT)
        kind_code = entries[0].code
        assert kind_code.state == "unknown"
        assert kind_code.code is None

    def test_same_source_row_yields_same_identifier(self):
        dx = _dx(id=42)
        entries_a = map_diagnoses((dx,), entry_id_root=_ROOT)
        entries_b = map_diagnoses((dx,), entry_id_root=_ROOT)
        assert entries_a[0].identifier == entries_b[0].identifier
        assert entries_a[0].identifier.extension == "diagnosis:42"

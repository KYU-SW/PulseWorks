"""HL7-4A §18: Patient/Encounter/Header mapper TDD."""

from datetime import date, datetime, timezone

import pytest

from app.core.config import Settings
from app.schemas.clinical_report import SnapshotEncounter, SnapshotPatient
from app.services.cda.adapter import CdaExportInput
from app.services.cda.mapper import map_document_header

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
_OTHER_ROOT = "2c5f39cb-3fb2-22e3-994a-1027e4ddb538"


def _settings() -> Settings:
    return Settings(
        cda_enabled=True,
        cda_document_id_root=_ROOT,
        cda_patient_id_root=_ROOT,
        cda_encounter_id_root=_ROOT,
        cda_author_id_root=_ROOT,
        cda_custodian_id_root=_OTHER_ROOT,
        cda_entry_id_root=_ROOT,
        cda_custodian_id_extension="synthetic-facility-1",
        cda_custodian_name="EMR Synthetic Demonstration Facility",
        cda_language_code="ko-KR",
    )


def _input(**overrides) -> CdaExportInput:
    base = dict(
        report_id=77,
        report_type="DOCTOR_REFERENCE",
        scope_type="SINGLE_ENCOUNTER",
        status="APPROVED",
        created_by_user_id=5,
        created_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
        reviewed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        narrative="narrative",
        patient=SnapshotPatient(id=1, mrn="SYN-0001", name="김합성", birth_date=date(1990, 1, 1)),
        encounter=SnapshotEncounter(
            id=10,
            department="ENDOCRINOLOGY",
            encounter_type="OUTPATIENT",
            start_time=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            end_time=None,
        ),
        vital_signs=(),
        lab_results=(),
        diagnoses=(),
    )
    base.update(overrides)
    return CdaExportInput(**base)


class TestMapDocumentHeader:
    def test_patient_identifier_uses_mrn_as_extension(self):
        document = map_document_header(_input(), _settings())
        assert document.patient.identifier.root == _ROOT
        assert document.patient.identifier.extension == "SYN-0001"
        assert document.patient.name == "김합성"
        assert document.patient.birth_time == date(1990, 1, 1)

    def test_patient_has_no_administrative_gender_code_field(self):
        import dataclasses

        from app.services.cda.models import CdaPatient

        field_names = {f.name for f in dataclasses.fields(CdaPatient)}
        assert "administrative_gender_code" not in field_names
        assert "sex" not in field_names

    def test_encounter_effective_time_is_open_ended_when_no_end_time(self):
        document = map_document_header(_input(), _settings())
        assert document.encounter.identifier.extension == "10"
        assert document.encounter.effective_time.high is None

    def test_encounter_effective_time_has_high_when_end_time_present(self):
        encounter = SnapshotEncounter(
            id=10,
            department="ENDOCRINOLOGY",
            encounter_type="OUTPATIENT",
            start_time=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 10, 9, 40, tzinfo=timezone.utc),
        )
        document = map_document_header(_input(encounter=encounter), _settings())
        assert document.encounter.effective_time.high.value == datetime(
            2026, 3, 10, 9, 40, tzinfo=timezone.utc
        )

    def test_author_uses_created_by_user_id_and_created_at(self):
        document = map_document_header(_input(), _settings())
        assert document.author.identifier.extension == "5"
        assert document.author.time.value == datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc)

    def test_custodian_uses_settings_values(self):
        document = map_document_header(_input(), _settings())
        assert document.custodian.identifier.root == _OTHER_ROOT
        assert document.custodian.identifier.extension == "synthetic-facility-1"
        assert document.custodian.organization_name == "EMR Synthetic Demonstration Facility"

    def test_document_effective_time_uses_reviewed_at_not_now(self):
        document = map_document_header(_input(), _settings())
        assert document.effective_time.value == datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)

    def test_missing_reviewed_at_is_rejected_rather_than_falling_back_to_now(self):
        with pytest.raises(ValueError, match="reviewed_at"):
            map_document_header(_input(reviewed_at=None), _settings())

    def test_document_id_uses_report_id(self):
        document = map_document_header(_input(report_id=999), _settings())
        assert document.document_id.extension == "999"

    def test_confidentiality_and_document_code_use_mvp_constants(self):
        document = map_document_header(_input(), _settings())
        assert document.confidentiality_code.code == "N"
        assert document.code.null_flavor == "UNK"

    def test_language_code_comes_from_settings(self):
        document = map_document_header(_input(), _settings())
        assert document.language_code == "ko-KR"

    def test_no_legal_authenticator_or_authenticator_field_exists(self):
        import dataclasses

        from app.services.cda.models import CdaDocument

        field_names = {f.name for f in dataclasses.fields(CdaDocument)}
        assert "legal_authenticator" not in field_names
        assert "authenticator" not in field_names
        assert "realm_code" not in field_names
        assert "set_id" not in field_names
        assert "version_number" not in field_names

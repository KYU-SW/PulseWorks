"""HL7-4A §19/§20/§21/§25: Section narrative fallback + 전체 문서 조립 TDD."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.schemas.clinical_report import (
    SnapshotDiagnosis,
    SnapshotEncounter,
    SnapshotLabResult,
    SnapshotPatient,
    SnapshotVitalSign,
)
from app.services.cda.adapter import CdaExportInput
from app.services.cda.mapper import map_document

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"


def _settings() -> Settings:
    return Settings(
        cda_enabled=True,
        cda_document_id_root=_ROOT,
        cda_patient_id_root=_ROOT,
        cda_encounter_id_root=_ROOT,
        cda_author_id_root=_ROOT,
        cda_custodian_id_root=_ROOT,
        cda_entry_id_root=_ROOT,
        cda_custodian_id_extension="synthetic-facility-1",
        cda_custodian_name="EMR Synthetic Demonstration Facility",
        cda_language_code="ko-KR",
    )


def _input(**overrides) -> CdaExportInput:
    base = dict(
        report_id=1,
        report_type="DOCTOR_REFERENCE",
        scope_type="SINGLE_ENCOUNTER",
        status="APPROVED",
        created_by_user_id=5,
        created_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
        reviewed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        narrative="환자는 2형 당뇨병이 신규로 진단되었습니다.",
        patient=SnapshotPatient(id=1, mrn="SYN-0001", name="김합성", birth_date=date(1990, 1, 1)),
        encounter=SnapshotEncounter(
            id=10,
            department="ENDOCRINOLOGY",
            encounter_type="OUTPATIENT",
            start_time=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            end_time=None,
        ),
        vital_signs=(
            SnapshotVitalSign.model_validate(
                dict(
                    id=300,
                    encounter_id=10,
                    vital_type="BODY_TEMPERATURE",
                    value=Decimal("36.5"),
                    value_secondary=None,
                    unit="Cel",
                    measured_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
                )
            ),
        ),
        lab_results=(
            SnapshotLabResult.model_validate(
                dict(
                    id=200,
                    encounter_id=10,
                    test_name="HbA1c",
                    value=7.2,
                    unit="%",
                    reference_low=4.0,
                    reference_high=6.0,
                    measured_at=datetime(2026, 3, 10, 9, 5, tzinfo=timezone.utc),
                    source_type="DOCTOR",
                    status="HIGH",
                    rule_id="r1",
                )
            ),
        ),
        diagnoses=(
            SnapshotDiagnosis.model_validate(
                dict(
                    id=100,
                    encounter_id=10,
                    code="E11.9",
                    description="2형 당뇨병",
                    diagnosed_at=datetime(2026, 3, 10, 9, 10, tzinfo=timezone.utc),
                    source_type="DOCTOR",
                )
            ),
        ),
    )
    base.update(overrides)
    return CdaExportInput(**base)


class TestMapDocumentSectionOrder:
    def test_four_sections_in_fixed_order(self):
        document, warnings = map_document(_input(), _settings())
        titles = [section.title for section in document.sections]
        assert titles == ["생체 징후", "검사결과", "문제 목록", "환자 서술"]
        assert warnings == ()

    def test_vital_signs_section_narrative_matches_structured_entry_value(self):
        document, _ = map_document(_input(), _settings())
        vital_section = document.sections[0]
        assert len(vital_section.entries) == 1
        # Narrative row와 Structured Entry가 같은 IR 값에서 나온다 - 같은
        # "36.5"라는 문자열이 양쪽에 그대로 나타난다.
        assert any("36.5" in row[1] for row in vital_section.narrative.rows)
        assert vital_section.entries[0].value.value == "36.5"

    def test_results_section_contains_lab_result_entry_and_row(self):
        document, _ = map_document(_input(), _settings())
        results_section = document.sections[1]
        assert len(results_section.entries) == 1
        assert any("HbA1c" in row[0] for row in results_section.narrative.rows)

    def test_problems_section_preserves_raw_diagnosis_code_in_narrative(self):
        document, _ = map_document(_input(), _settings())
        problems_section = document.sections[2]
        assert len(problems_section.entries) == 1
        assert any("E11.9" in row[0] for row in problems_section.narrative.rows)

    def test_patient_narrative_section_uses_plain_text_paragraph(self):
        document, _ = map_document(_input(), _settings())
        narrative_section = document.sections[3]
        assert narrative_section.entries == ()
        assert narrative_section.narrative.paragraph == "환자는 2형 당뇨병이 신규로 진단되었습니다."

    def test_blood_pressure_warning_propagates_to_document_level_warnings(self):
        incomplete_bp = SnapshotVitalSign.model_validate(
            dict(
                id=301,
                encounter_id=10,
                vital_type="BLOOD_PRESSURE",
                value=Decimal("130"),
                value_secondary=None,
                unit="mmHg",
                measured_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            )
        )
        document, warnings = map_document(_input(vital_signs=(incomplete_bp,)), _settings())
        assert len(warnings) == 1
        assert warnings[0].code == "INCOMPLETE_BLOOD_PRESSURE"
        # 생략된 BP는 Vital Signs Section의 entries에도 없다.
        assert document.sections[0].entries == ()


class TestEmptySections:
    def test_empty_vital_signs_section_has_no_entries_and_placeholder_row(self):
        document, _ = map_document(_input(vital_signs=()), _settings())
        vital_section = document.sections[0]
        assert vital_section.entries == ()
        assert len(vital_section.narrative.rows) == 1

    def test_empty_results_section_has_no_entries_and_placeholder_row(self):
        document, _ = map_document(_input(lab_results=()), _settings())
        results_section = document.sections[1]
        assert results_section.entries == ()
        assert len(results_section.narrative.rows) == 1

    def test_empty_problems_section_has_no_entries_and_placeholder_row(self):
        document, _ = map_document(_input(diagnoses=()), _settings())
        problems_section = document.sections[2]
        assert problems_section.entries == ()
        assert len(problems_section.narrative.rows) == 1


class TestDeterministicOrdering:
    def test_repeated_mapping_produces_identical_document(self):
        export_input = _input()
        settings = _settings()
        document_a, warnings_a = map_document(export_input, settings)
        document_b, warnings_b = map_document(export_input, settings)
        assert document_a == document_b
        assert warnings_a == warnings_b

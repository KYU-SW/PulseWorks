"""HL7-4A §21/§22/§23: CDA Exporter TDD.

중요: 이 테스트는 XML well-formedness만 확인한다. 공식 CDA R2.0 XSD에
대한 schema validation은 하지 않는다(Gate C 미해결, HL7-3A) - lxml의
XMLSchema validation은 이번 작업에서 전혀 쓰지 않는다.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from lxml import etree

from app.core.config import Settings
from app.schemas.clinical_report import (
    SnapshotDiagnosis,
    SnapshotEncounter,
    SnapshotLabResult,
    SnapshotPatient,
    SnapshotVitalSign,
)
from app.services.cda.adapter import CdaExportInput
from app.services.cda.exporter import export_document
from app.services.cda.mapper import map_document

_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
_CDA_NS = "urn:hl7-org:v3"


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
        narrative="환자 상태: <script>alert(1)</script> & 특이사항 없음",
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
                    vital_type="BLOOD_PRESSURE",
                    value=Decimal("120"),
                    value_secondary=Decimal("80"),
                    unit="mmHg",
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


def _export_bytes() -> bytes:
    document, _warnings = map_document(_input(), _settings())
    return export_document(document)


class TestWellFormedness:
    def test_output_is_well_formed_xml(self):
        root = etree.fromstring(_export_bytes())
        assert root is not None

    def test_root_element_is_clinical_document_in_cda_namespace(self):
        root = etree.fromstring(_export_bytes())
        assert root.tag == f"{{{_CDA_NS}}}ClinicalDocument"

    def test_xsi_namespace_is_declared(self):
        root = etree.fromstring(_export_bytes())
        assert root.nsmap.get("xsi") == "http://www.w3.org/2001/XMLSchema-instance"

    def test_utf8_encoding_declared(self):
        assert b"encoding='UTF-8'" in _export_bytes() or b'encoding="UTF-8"' in _export_bytes()


class TestEscaping:
    def test_script_tag_in_narrative_is_escaped_not_executable_markup(self):
        xml_bytes = _export_bytes()
        # 이스케이프된 상태로만 존재해야 한다 - 실제 <script> 엘리먼트로
        # 파싱되면 안 된다.
        assert b"<script>" not in xml_bytes
        root = etree.fromstring(xml_bytes)
        script_elements = root.findall(f".//{{{_CDA_NS}}}script")
        assert script_elements == []
        # 파싱 후 텍스트 내용으로는 원본 문자열이 그대로 남아 있어야
        # 한다(정보 손실 없음).
        serialized_text = etree.tostring(root, encoding="unicode")
        assert "<script>alert(1)</script>" in serialized_text or "&lt;script&gt;" in xml_bytes.decode("utf-8")

    def test_ampersand_is_escaped(self):
        xml_bytes = _export_bytes()
        assert b"& " not in xml_bytes.replace(b"&amp;", b"")


class TestSectionOrder:
    def test_sections_appear_in_fixed_order(self):
        root = etree.fromstring(_export_bytes())
        titles = [
            el.text
            for el in root.findall(f".//{{{_CDA_NS}}}section/{{{_CDA_NS}}}title")
        ]
        assert titles == ["생체 징후", "검사결과", "문제 목록", "환자 서술"]


class TestBloodPressureOrganizer:
    def test_organizer_contains_two_observation_components(self):
        root = etree.fromstring(_export_bytes())
        organizers = root.findall(f".//{{{_CDA_NS}}}organizer")
        assert len(organizers) == 1
        observations = organizers[0].findall(f".//{{{_CDA_NS}}}observation")
        assert len(observations) == 2


class TestTerminologyRendering:
    def test_confidentiality_code_is_rendered(self):
        root = etree.fromstring(_export_bytes())
        node = root.find(f"{{{_CDA_NS}}}confidentialityCode")
        assert node.get("code") == "N"
        assert node.get("codeSystem") == "2.16.840.1.113883.5.25"

    def test_document_code_uses_null_flavor_not_a_fabricated_code(self):
        root = etree.fromstring(_export_bytes())
        node = root.find(f"{{{_CDA_NS}}}code")
        assert node.get("nullFlavor") == "UNK"
        assert node.get("code") is None

    def test_diagnosis_raw_unverified_value_has_no_code_system_attribute(self):
        root = etree.fromstring(_export_bytes())
        value_nodes = root.findall(f".//{{{_CDA_NS}}}entry//{{{_CDA_NS}}}value")
        raw_code_nodes = [n for n in value_nodes if n.get("code") == "E11.9"]
        assert len(raw_code_nodes) == 1
        assert raw_code_nodes[0].get("codeSystem") is None


class TestDeterminism:
    def test_repeated_export_produces_identical_bytes(self):
        first = _export_bytes()
        second = _export_bytes()
        assert first == second

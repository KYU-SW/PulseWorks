"""HL7-4A: CDA terminology/unit 모듈 테스트.

HL7-3 §13 결정: VitalSign LOINC/UCUM 매핑은 .env가 아니라 코드 상수다.
HL7-3A Gate A/B 결정: confidentialityCode="N", document code는
nullFlavor="UNK"+originalText다.
"""

from app.models.enums import VitalType
from app.services.cda.terminology import (
    CDA_CONFIDENTIALITY_CODE,
    CDA_DOCUMENT_CODE_ORIGINAL_TEXT,
    VITAL_TYPE_LOINC,
    normalize_unit,
)


class TestUnitNormalization:
    def test_known_vital_sign_units_map_to_ucum(self):
        assert normalize_unit("mmHg") == "mm[Hg]"
        assert normalize_unit("cm") == "cm"
        assert normalize_unit("kg") == "kg"
        assert normalize_unit("Cel") == "Cel"
        assert normalize_unit("/min") == "/min"
        assert normalize_unit("%") == "%"

    def test_unknown_unit_is_preserved_as_raw_string(self):
        # AI 사용 금지 + 거짓 UCUM 주장 금지(HL7-2 §12): 모르는 단위는
        # 그대로 보존하고 UCUM이라고 주장하지 않는다.
        assert normalize_unit("mg/dL") == "mg/dL"


class TestVitalTypeLoinc:
    def test_all_seven_vital_types_have_loinc_candidates(self):
        assert VITAL_TYPE_LOINC[VitalType.BODY_HEIGHT] == "8302-2"
        assert VITAL_TYPE_LOINC[VitalType.BODY_WEIGHT] == "29463-7"
        assert VITAL_TYPE_LOINC[VitalType.BODY_TEMPERATURE] == "8310-5"
        assert VITAL_TYPE_LOINC[VitalType.HEART_RATE] == "8867-4"
        assert VITAL_TYPE_LOINC[VitalType.RESPIRATORY_RATE] == "9279-1"
        assert VITAL_TYPE_LOINC[VitalType.PULSE_OXIMETRY] == "2708-6"
        # BLOOD_PRESSURE는 panel/systolic/diastolic 3개 코드가 필요해
        # 단일 문자열이 아니라 별도 상수(BLOOD_PRESSURE_PANEL_LOINC 등)로
        # 다룬다 - 이 표에는 포함하지 않는다.
        assert VitalType.BLOOD_PRESSURE not in VITAL_TYPE_LOINC


class TestConfidentialityAndDocumentCode:
    def test_confidentiality_mvp_constant(self):
        assert CDA_CONFIDENTIALITY_CODE.state == "known"
        assert CDA_CONFIDENTIALITY_CODE.code == "N"
        assert CDA_CONFIDENTIALITY_CODE.code_system == "2.16.840.1.113883.5.25"

    def test_document_code_mvp_constant(self):
        assert CDA_DOCUMENT_CODE_ORIGINAL_TEXT.state == "unknown"
        assert CDA_DOCUMENT_CODE_ORIGINAL_TEXT.null_flavor == "UNK"
        assert CDA_DOCUMENT_CODE_ORIGINAL_TEXT.original_text == "진료참고 보고서"

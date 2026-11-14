"""HL7-4A: CDA terminology/unit 상수.

HL7-3 §13 결정: VitalSign LOINC, UCUM 단위 매핑, confidentiality/
document code MVP 값은 배포마다 달라질 이유가 없는 Application/
Terminology Mapping이다 - .env config가 아니라 이 모듈의 코드 상수로
둔다. 이 모듈의 함수는 모두 순수 함수다(safety_rules.py/
vital_sign_derived.py와 같은 원칙) - DB 조회, AI 호출을 하지 않는다.
"""

from __future__ import annotations

from app.models.enums import VitalType
from app.services.cda.models import CodedValue

# HL7-2 §12 / vital_sign_derived.CANONICAL_UNITS에서 쓰는 원본 단위
# 문자열을 UCUM 코드로 1:1 고정 매핑한다. mmHg만 실제로 표기가 다르고
# 나머지는 UCUM과 문자열이 같다(HL7-1A §19에서 PQ.unit이 raw string임을
# 확인 - UCUM은 CDA Core가 강제하는 게 아니라 이 프로젝트의 terminology
# 선택이다).
_KNOWN_UNIT_TO_UCUM: dict[str, str] = {
    "mmHg": "mm[Hg]",
    "cm": "cm",
    "kg": "kg",
    "Cel": "Cel",
    "/min": "/min",
    "%": "%",
}


def normalize_unit(raw_unit: str) -> str:
    """known whitelist에 있으면 UCUM 코드로, 없으면 원본 문자열을 그대로
    반환한다. 모르는 단위를 UCUM이라고 주장하지 않는다(AI로 추측하지
    않음, HL7-2 §12)."""
    return _KNOWN_UNIT_TO_UCUM.get(raw_unit, raw_unit)


# docs/standards/kr-cdi-kr-core-mapping.md §3에서 KR Core IG v1.0.2
# StructureDefinition 페이지의 Fixed Value로 확인한 LOINC 코드 -
# CDA Core의 요구가 아니라 이 프로젝트가 채택한 terminology 선택이다
# (HL7-2 §10). BLOOD_PRESSURE는 panel/systolic/diastolic 3개 코드가
# 필요해 이 표에 넣지 않고 아래 별도 상수로 둔다.
VITAL_TYPE_LOINC: dict[VitalType, str] = {
    VitalType.BODY_HEIGHT: "8302-2",
    VitalType.BODY_WEIGHT: "29463-7",
    VitalType.BODY_TEMPERATURE: "8310-5",
    VitalType.HEART_RATE: "8867-4",
    VitalType.RESPIRATORY_RATE: "9279-1",
    VitalType.PULSE_OXIMETRY: "2708-6",
}

BLOOD_PRESSURE_PANEL_LOINC = "85354-9"
BLOOD_PRESSURE_SYSTOLIC_LOINC = "8480-6"
BLOOD_PRESSURE_DIASTOLIC_LOINC = "8462-4"

_LOINC_CODE_SYSTEM_OID = "2.16.840.1.113883.6.1"


# Narrative fallback 표(§17/§19)에만 쓰는 한국어 라벨 - Structured
# Entry(code/codeSystem)에는 영향이 없는 순수 표시용 문자열이다.
VITAL_TYPE_LABELS: dict[VitalType, str] = {
    VitalType.BODY_HEIGHT: "키",
    VitalType.BODY_WEIGHT: "체중",
    VitalType.BODY_TEMPERATURE: "체온",
    VitalType.HEART_RATE: "맥박",
    VitalType.RESPIRATORY_RATE: "호흡수",
    VitalType.PULSE_OXIMETRY: "산소포화도",
}

BLOOD_PRESSURE_LABEL = "혈압"


def vital_type_coded_value(vital_type: VitalType) -> CodedValue:
    """단일값 VitalType(혈압 제외)의 CodedValue. 혈압은 Organizer+2
    Observation 구조라 이 함수를 쓰지 않는다(mapper.py가 별도 처리)."""
    return CodedValue.known(
        code=VITAL_TYPE_LOINC[vital_type],
        code_system=_LOINC_CODE_SYSTEM_OID,
        display_name=VITAL_TYPE_LABELS[vital_type],
    )


# Gate A(HL7-3A §5): HL7 공식 v3 Confidentiality code system(OID
# 2.16.840.1.113883.5.25)에서 확인한 code "N"="normal" - "Default for
# normal clinical care access"라는 공식 정의가 이 프로젝트(합성 단일
# 기관, 별도 문서별 confidentiality 분류 기능 없음, 일반 임상정보)의
# 실제 상태를 정확히 기술한다. 주의: ClinicalDocument.confidentialityCode
# 자체에 대한 명시적 CDA 바인딩 선언 문장은 공식 소스에서 확인하지
# 못했다 - 이 코드체계가 "Act.Confidentiality attribute"를 값매김한다는
# RIM 구조적 근거에 기반한 MVP 선택이며, 특정 국가 Implementation
# Guide의 binding을 주장하지 않는다.
CDA_CONFIDENTIALITY_CODE = CodedValue.known(
    code="N", code_system="2.16.840.1.113883.5.25", display_name="normal"
)

# Gate B(HL7-3A §9): ClinicalDocument.code의 공식 바인딩은 FHIR Document
# Type Codes(LOINC SCALE_TYP=Doc)에 대해 강도 "example"이며, 공식
# 페이지 자체가 "Instances are not expected or even encouraged to draw
# from the specified value set"라고 명시한다. DOCTOR_REFERENCE와 정확히
# 일치하는 공식 LOINC 문서유형 코드를 확인하지 못했으므로(Progress
# Note/Consultation Note 등을 이름만 비슷하다는 이유로 선택하지 않음),
# nullFlavor="UNK" + originalText로 표현한다.
CDA_DOCUMENT_CODE_ORIGINAL_TEXT = CodedValue.unknown(original_text="진료참고 보고서")

# ClinicalDocument.title - 배포마다 달라질 이유가 없는 고정 제품
# 텍스트라 application constant로 둔다(config가 아님, HL7-3 §9). 기존
# 코드 주석(clinical_reports.py의 "진료참고 보고서" 표현)과 동일한
# 용어를 재사용한다.
CDA_DOCUMENT_TITLE = "진료참고 보고서"

# HL7-4A.2 Gate 2(HL7-4A.1에서 공식 확인): 공식 HL7 v3 ActStatus
# CodeSystem(http://terminology.hl7.org/CodeSystem/v3-ActStatus,
# OID 2.16.840.1.113883.5.14)의 "completed" 코드 - "An Act that has
# terminated normally after all of its constituents have been
# performed." 이 프로젝트에서 유일한 Organizer 사용처인 BP Organizer는
# 이미 DB에 저장된, 특정 과거 measured_at 시점에 확정된 systolic/
# diastolic 측정값만 묶는다(ongoing workflow 아님) - 이 공식 정의와
# 의미가 정확히 일치한다. Observation.statusCode(optional)에는 적용하지
# 않는다 - 그쪽은 derive할 lifecycle state 소스 데이터가 없다(HL7-3A).
ACT_STATUS_CODE_SYSTEM = "2.16.840.1.113883.5.14"
CDA_ORGANIZER_STATUS_COMPLETED = CodedValue.known(code="completed", code_system=ACT_STATUS_CODE_SYSTEM)

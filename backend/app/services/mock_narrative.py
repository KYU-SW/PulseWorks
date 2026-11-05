"""ClinicalReport.content.narrative를 채우는 결정적 Mock 설명문 생성기.

DB/HTTP에 의존하지 않는 순수 함수다 — app.schemas.clinical_report.EmrSnapshot
(저장된 스냅샷을 재검증한 결과)만 입력받고, 같은 스냅샷에는 항상 같은
문자열을 반환한다. 실제 LLM이나 외부 AI API를 호출하지 않으며, 난수나
현재 시각에 의존하지 않는다.

Task 20C 후속 보완: 이 narrative는 의사가 검토하는 동시에, 승인 후
환자에게 그대로 공개된다. 그래서 Encounter/진단/검사/SafetyAlert/
ClinicalNote의 내부 ID·코드·개발 검증용 문자열은 절대 포함하지 않고,
정확한 수치·참고범위·용량·알레르기 상세는 구조화된 섹션에 맡긴 채
사실 그대로의 짧은 중립 요약만 만든다 — 새 진단, 악화/호전 확정,
치료·처방 변경 권고, 재검사 지시, 위험도 확정, 예후 예측은 만들지
않는다. SafetyAlert와 ClinicalNote는 narrative 생성에 전혀 사용하지
않는다(스냅샷과 의사용 구조화 화면에는 그대로 남는다).

Task F4-B: 핵심 5종(혈압·체온·맥박·호흡수·산소포화도)만 narrative에
사실 그대로 옮기고, 키·체중은 수치를 반복하지 않고 구조화된 활력징후
섹션으로 안내만 한다. BMI·품질 경고·V Evidence Tag·vital_sign 내부 ID는
여기서 절대 만들지 않는다 - 둘 다 조회 시점에 계산하는 파생값이고
이 함수는 애초에 app.services.vital_sign_derived를 import하지 않는다.
snapshot.vital_signs가 비어 있으면(과거 Snapshot 포함) 이 함수의 출력은
F4-B 이전과 완전히 동일하다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.schemas.clinical_report import (
    EmrSnapshot,
    SnapshotAllergy,
    SnapshotDiagnosis,
    SnapshotEncounter,
    SnapshotLabResult,
    SnapshotPrescription,
    SnapshotVitalSign,
)

_PROVIDER = "DETERMINISTIC_MOCK"
_VERSION = "1"

_DEPARTMENT_LABELS = {
    "ENDOCRINOLOGY": "내분비내과",
    "ORTHOPEDICS": "정형외과",
    "EMERGENCY_MEDICINE": "응급의학과",
}
_ENCOUNTER_TYPE_LABELS = {
    "OUTPATIENT": "외래",
    "INPATIENT": "입원",
    "EMERGENCY": "응급",
}

# 실제 사용되는 검사 판정은 이 네 가지뿐이다(app/services/safety_rules.py의
# LabStatus). 문장은 status만 중립적으로 옮길 뿐 새 의학적 해석을 더하지
# 않는다 — 목록에 없는 값이 들어오면(있을 수 없지만) 조용히 건너뛴다.
_LAB_STATUS_SENTENCE_TEMPLATES = {
    "HIGH": "{names} 검사결과가 저장된 참고범위보다 높은 것으로 기록되어 있습니다.",
    "LOW": "{names} 검사결과가 저장된 참고범위보다 낮은 것으로 기록되어 있습니다.",
    "NORMAL": "{names} 검사결과가 저장된 참고범위 내에 있는 것으로 기록되어 있습니다.",
    "UNKNOWN": "{names} 검사결과 판정이 확인되지 않은 것으로 기록되어 있습니다.",
}
_LAB_STATUS_ORDER = ("HIGH", "LOW", "NORMAL", "UNKNOWN")

# 환자가 읽는 narrative에서만 쓰는 표시 변환이다 — 저장된
# medication_name/스냅샷 자체는 바꾸지 않는다. 매핑에 없는 이름은 원문을
# 그대로 쓴다(가상의 실제 약물명 추정·변환을 하지 않기 위해서다).
_MEDICATION_DISPLAY_NAMES = {
    "Metformin": "메트포르민",
    "Penicillin V": "페니실린 V",
}

# "Task10VerifyNonConflictMedX"는 실제 약물이 아니라 Task 9/10 안전 규칙
# 검증에 쓰인 개발용 합성 문자열이다(frontend의 PatientPrescriptionsList.tsx
# 와 동일한 값) — narrative에서는 다른 약물로 추정하지 않고 완전히 뺀다.
_DEV_TEST_MEDICATION_NAME = "Task10VerifyNonConflictMedX"

# Task F4-B: snapshot.vital_signs는 이미 canonical 단위만 담고 있다
# (report_data.py가 조립 시점에 걸러낸다) - 여기서 단위를 다시 확인하지
# 않는다. 키·체중은 narrative에 수치로 반복하지 않고 구조화된 활력징후
# 섹션으로 안내만 한다 - BMI·품질 경고와 마찬가지로 이 함수는 그 둘을
# 계산하거나 언급하지 않는다(evaluate_vital_sign_quality()/calculate_bmi()를
# import하지 않는다).
_CORE_VITAL_TYPE_ORDER = (
    "BLOOD_PRESSURE",
    "BODY_TEMPERATURE",
    "HEART_RATE",
    "RESPIRATORY_RATE",
    "PULSE_OXIMETRY",
)

_VITAL_SIGN_GUIDANCE_SENTENCE = (
    "키와 체중을 포함한 자세한 내용은 아래 활력징후 항목에서 확인할 수 있습니다."
)

_GUIDANCE_SENTENCE = (
    "정확한 검사결과, 참고범위, 처방 및 알레르기 정보는 "
    "아래의 각 항목에서 확인할 수 있습니다."
)
_SAFETY_NOTICE_SENTENCE = "검사결과와 처방의 의미는 담당 의료진 또는 약사에게 확인하세요."
_NO_RECORDS_SENTENCE = "이 범위에서 확인할 수 있는 기록이 없습니다."


@dataclass(frozen=True)
class MockNarrativeResult:
    summary_text: str
    source_record_ids: list[str]
    provider: str
    version: str


def _has_trailing_batchim(word: str) -> bool:
    """word 마지막 글자에 받침이 있는지만 확인한다 - "와"/"과" 중 어느
    조사를 붙일지 고르는 데만 쓴다. 한글 음절이 아니면 받침 없음으로
    취급한다."""
    if not word:
        return False
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return False
    return (ord(last) - ord("가")) % 28 != 0


def _join_korean_list(items: list[str]) -> str:
    """자연스러운 한국어 나열: 1개면 그대로, 2개면 받침에 따라 "와"/"과",
    3개 이상이면 마지막 항목 앞에 "및"을 붙인다."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        particle = "과" if _has_trailing_batchim(items[0]) else "와"
        return f"{items[0]}{particle} {items[1]}"
    return ", ".join(items[:-1]) + f" 및 {items[-1]}"


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _format_date(dt) -> str:
    return f"{dt.year}년 {dt.month}월 {dt.day}일"


def _encounter_paragraph(encounters: list[SnapshotEncounter]) -> str | None:
    if not encounters:
        return None
    phrases = [
        f"{_format_date(encounter.start_time)} "
        f"{_DEPARTMENT_LABELS.get(encounter.department, encounter.department)} "
        f"{_ENCOUNTER_TYPE_LABELS.get(encounter.encounter_type, encounter.encounter_type)}"
        for encounter in encounters
    ]
    phrases = _dedupe_preserve_order(phrases)
    return f"{', '.join(phrases)} 진료기록을 정리한 보고서입니다."


def _lab_status_sentences(lab_results: list[SnapshotLabResult]) -> list[str]:
    names_by_status: dict[str, list[str]] = {}
    for lab in lab_results:
        names_by_status.setdefault(lab.status, []).append(lab.test_name)

    sentences: list[str] = []
    for status in _LAB_STATUS_ORDER:
        names = names_by_status.get(status)
        if not names:
            continue
        template = _LAB_STATUS_SENTENCE_TEMPLATES[status]
        sentences.append(template.format(names=_join_korean_list(_dedupe_preserve_order(names))))
    return sentences


def _diagnosis_and_lab_paragraph(
    diagnoses: list[SnapshotDiagnosis], lab_results: list[SnapshotLabResult]
) -> str | None:
    parts: list[str] = []
    descriptions = _dedupe_preserve_order([d.description for d in diagnoses])
    lab_sentences = _lab_status_sentences(lab_results)

    if descriptions:
        clause = f"{_join_korean_list(descriptions)}에 관한 진단 기록이 있"
        clause += "으며," if lab_sentences else "습니다."
        parts.append(clause)

    parts.extend(lab_sentences)

    return " ".join(parts) if parts else None


def _prescription_and_allergy_paragraph(
    prescriptions: list[SnapshotPrescription], allergies: list[SnapshotAllergy]
) -> str | None:
    parts: list[str] = []
    names = _dedupe_preserve_order(
        [
            _MEDICATION_DISPLAY_NAMES.get(p.medication_name, p.medication_name)
            for p in prescriptions
            if p.medication_name != _DEV_TEST_MEDICATION_NAME
        ]
    )
    substances = _dedupe_preserve_order([a.substance for a in allergies])

    if names:
        clause = f"{_join_korean_list(names)} 처방 기록이 있"
        clause += "으며," if substances else "습니다."
        parts.append(clause)

    if substances:
        parts.append(f"{_join_korean_list(substances)}에 대한 알레르기 정보가 등록되어 있습니다.")

    return " ".join(parts) if parts else None


def _round_integer(value: Decimal) -> str:
    return str(value.to_integral_value())


def _round_one_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1")))


def _latest_vital_sign(
    vital_signs: list[SnapshotVitalSign], vital_type: str
) -> SnapshotVitalSign | None:
    """같은 유형이 둘 이상이면(정상적으로는 드문 상황) 가장 최근 측정값을
    쓴다 - calculate_bmi()가 height/weight를 고를 때 쓰는 "최근 값" 원칙과
    동일하다."""
    matching = [v for v in vital_signs if v.vital_type == vital_type]
    if not matching:
        return None
    return max(matching, key=lambda v: v.measured_at)


def _core_vital_sign_clause(vital_type: str, vital: SnapshotVitalSign) -> str | None:
    if vital_type == "BLOOD_PRESSURE":
        if vital.value_secondary is None:
            return None  # 구조적으로 발생하지 않아야 하지만 방어적으로 건너뛴다.
        systolic = _round_integer(vital.value)
        diastolic = _round_integer(vital.value_secondary)
        return f"혈압은 {systolic}/{diastolic} mmHg"
    if vital_type == "BODY_TEMPERATURE":
        return f"체온은 {_round_one_decimal(vital.value)}℃"
    if vital_type == "HEART_RATE":
        return f"맥박은 {_round_integer(vital.value)}회/분"
    if vital_type == "RESPIRATORY_RATE":
        return f"호흡수는 {_round_integer(vital.value)}회/분"
    return f"산소포화도는 {_round_integer(vital.value)}%"  # PULSE_OXIMETRY


def _vital_sign_paragraph(vital_signs: list[SnapshotVitalSign]) -> str | None:
    """핵심 5종(혈압·체온·맥박·호흡수·산소포화도)만 사실 그대로 서술하고,
    키·체중은 안내 문장으로만 가리킨다. BMI·품질 경고·V Evidence Tag·
    source_record_id·내부 ID는 만들지 않는다 - 새 진단·치료 권고·위험도
    판단도 하지 않는다(이 함수가 하는 일은 저장된 값을 중립적으로
    옮기는 것뿐이다)."""
    if not vital_signs:
        return None

    clauses: list[str] = []
    for vital_type in _CORE_VITAL_TYPE_ORDER:
        vital = _latest_vital_sign(vital_signs, vital_type)
        if vital is None:
            continue
        clause = _core_vital_sign_clause(vital_type, vital)
        if clause is not None:
            clauses.append(clause)

    parts: list[str] = []
    if clauses:
        parts.append(", ".join(clauses) + "로 기록되어 있습니다.")
    parts.append(_VITAL_SIGN_GUIDANCE_SENTENCE)
    return " ".join(parts)


def generate_mock_report_narrative(snapshot: EmrSnapshot) -> MockNarrativeResult:
    """저장된 스냅샷만으로 환자도 읽을 수 있는 짧은 요약문을 조립한다.
    문단 구성은 Encounter → (진단+검사 요약) → (처방+알레르기 요약) →
    안내 문구로 고정되어 있다 — 같은 스냅샷이면 항상 같은 문자열이
    나온다. SafetyAlert/ClinicalNote는 이 함수에서 전혀 읽지 않는다."""
    paragraphs: list[str] = []

    encounter_paragraph = _encounter_paragraph(snapshot.encounters)
    if encounter_paragraph:
        paragraphs.append(encounter_paragraph)

    dx_lab_paragraph = _diagnosis_and_lab_paragraph(snapshot.diagnoses, snapshot.lab_results)
    if dx_lab_paragraph:
        paragraphs.append(dx_lab_paragraph)

    vital_sign_paragraph = _vital_sign_paragraph(snapshot.vital_signs)
    if vital_sign_paragraph:
        paragraphs.append(vital_sign_paragraph)

    rx_allergy_paragraph = _prescription_and_allergy_paragraph(snapshot.prescriptions, snapshot.allergies)
    if rx_allergy_paragraph:
        paragraphs.append(rx_allergy_paragraph)

    if paragraphs:
        paragraphs.append(_GUIDANCE_SENTENCE)
    else:
        paragraphs.append(_NO_RECORDS_SENTENCE)

    paragraphs.append(_SAFETY_NOTICE_SENTENCE)

    return MockNarrativeResult(
        summary_text="\n\n".join(paragraphs),
        source_record_ids=list(snapshot.source_record_ids),
        provider=_PROVIDER,
        version=_VERSION,
    )

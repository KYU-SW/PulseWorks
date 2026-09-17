"""검사값 참고범위 비교, 알레르기-처방 문자열 충돌 비교 등 중앙 규칙 모음.

이 모듈은 순수 함수만 담는다: DB 조회, HTTP 처리, 감사 로그 작성, 전역
상태 변경을 하지 않으며, 같은 입력에는 항상 같은 결과를 반환한다.

evaluate_lab_abnormal()은 합성 검사값을 등록된 데모 참고범위와 기계적으로
비교할 뿐이다 — 의료 판단(진단/치료/처방 권고)을 수행하지 않는다. 최종
해석은 항상 의료진이 수행한다.

check_allergy_conflict()도 마찬가지로 등록된 합성 Allergy 이름과 입력된
medication_name을 제한된 문자열 규칙으로만 비교한다 — 실제 성분 기반
알레르기 판정, 교차반응 판정, 약물계열 추론(예: Amoxicillin을 Penicillin과
같은 계열로 추론)을 하지 않는다. 충돌 표시는 의료진 확인을 요청하는
용도일 뿐, 처방을 자동 차단·변경·취소하지 않는다.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum


class LabAbnormalStatus(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


_RULE_ID = "LAB_REFERENCE_RANGE"

_EXPLANATIONS: dict[LabAbnormalStatus, str] = {
    LabAbnormalStatus.LOW: "검사값이 등록된 데모 참고범위 하한보다 낮습니다.",
    LabAbnormalStatus.NORMAL: "검사값이 등록된 데모 참고범위 안에 있습니다.",
    LabAbnormalStatus.HIGH: "검사값이 등록된 데모 참고범위 상한보다 높습니다.",
    LabAbnormalStatus.UNKNOWN: "참고범위 판정에 필요한 정보가 부족하거나 유효하지 않습니다.",
}


@dataclass(frozen=True)
class LabAbnormalResult:
    status: LabAbnormalStatus
    value: float | None
    reference_low: float | None
    reference_high: float | None
    unit: str | None
    rule_id: str
    explanation: str


def _is_finite_number(candidate: object) -> bool:
    """None, bool, 비유한(NaN/inf) 값을 전부 "안전한 숫자 아님"으로 취급한다."""
    if isinstance(candidate, bool):
        return False
    if not isinstance(candidate, (int, float)):
        return False
    return math.isfinite(candidate)


def evaluate_lab_abnormal(
    value: float | None,
    reference_low: float | None,
    reference_high: float | None,
    unit: str | None = None,
) -> LabAbnormalResult:
    """검사값과 참고범위를 비교해 구조화된 결과를 반환한다.

    규칙:
    - value < reference_low            -> LOW
    - reference_low <= value <= reference_high -> NORMAL (경계값은 정상범위에 포함)
    - value > reference_high           -> HIGH
    - 판정에 필요한 값이 없거나(None), 숫자가 아니거나(NaN/inf),
      참고범위가 유효하지 않으면(reference_low > reference_high) -> UNKNOWN

    입력받은 value/reference_low/reference_high/unit은 그대로 보존해
    반환한다 — 단위 변환이나 정규화는 하지 않는다.
    """
    if (
        not _is_finite_number(value)
        or not _is_finite_number(reference_low)
        or not _is_finite_number(reference_high)
        or reference_low > reference_high
    ):
        status = LabAbnormalStatus.UNKNOWN
    elif value < reference_low:
        status = LabAbnormalStatus.LOW
    elif value > reference_high:
        status = LabAbnormalStatus.HIGH
    else:
        status = LabAbnormalStatus.NORMAL

    return LabAbnormalResult(
        status=status,
        value=value,
        reference_low=reference_low,
        reference_high=reference_high,
        unit=unit,
        rule_id=_RULE_ID,
        explanation=_EXPLANATIONS[status],
    )


_ALLERGY_RULE_ID = "ALLERGY_MEDICATION_CONFLICT"

_ALLERGY_CONFLICT_EXPLANATION = (
    "입력된 약물명이 등록된 알레르기 물질명과 문자열 비교 규칙상 일치합니다. "
    "처방 전 의료진의 확인이 필요합니다."
)
_ALLERGY_NO_CONFLICT_EXPLANATION = (
    "입력된 약물명이 등록된 알레르기 물질명과 문자열 비교 규칙상 일치하지 않습니다."
)


@dataclass(frozen=True)
class AllergyEvidence:
    """check_allergy_conflict()의 입력 단위 — 실제 SQLAlchemy Allergy 모델에
    의존하지 않는 최소 필드만 담는다."""

    allergy_id: int
    allergy_name: str


@dataclass(frozen=True)
class AllergyConflictResult:
    has_conflict: bool
    rule_id: str
    matched_allergy_id: int | None
    matched_allergy_name: str | None
    medication_name: str
    priority: str | None
    explanation: str


def _normalize_for_comparison(text: str) -> str:
    """앞뒤 공백 제거, 연속 공백을 하나로 축소, 대소문자 무시."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def _is_prefix_with_word_boundary(medication_normalized: str, allergy_normalized: str) -> bool:
    """medication_normalized가 allergy_normalized로 시작하고, 그 다음이
    문자열 끝이거나 영숫자가 아닌 경계 문자(공백, 하이픈 등)인 경우에만
    True. "Pen"이 "Penicillin V"의 접두어이지만 그 다음 문자 "i"가
    영숫자이므로 경계가 아니다 — 이런 우연한 부분일치는 충돌로 보지
    않는다."""
    if not allergy_normalized:
        return False
    if not medication_normalized.startswith(allergy_normalized):
        return False
    if len(medication_normalized) == len(allergy_normalized):
        return True
    boundary_char = medication_normalized[len(allergy_normalized)]
    return not boundary_char.isalnum()


def check_allergy_conflict(
    allergies: list[AllergyEvidence],
    medication_name: str,
) -> AllergyConflictResult:
    """등록된 Allergy 목록과 처방하려는 medication_name을 제한된 문자열
    규칙으로만 비교한다. 실제 성분·약물계열 데이터베이스를 사용하지 않으며,
    Amoxicillin과 Penicillin 같은 실제 계열 관계를 추론하지 않는다.

    medication_name이 어떤 allergy_name으로(정규화 후) 시작하고 그 다음이
    단어 경계이면 충돌로 판단한다. 일치하는 Allergy가 여러 개면 입력 순서와
    무관하게 allergy_id가 가장 작은 것을 선택해 항상 같은 입력에 같은
    결과를 반환한다.

    Allergy 목록이 비었거나 medication_name이 빈 문자열/공백뿐이면 충돌
    없음으로 판단한다.
    """
    medication_normalized = _normalize_for_comparison(medication_name) if medication_name else ""

    matched: AllergyEvidence | None = None
    if medication_normalized:
        candidates = [
            allergy
            for allergy in allergies
            if _is_prefix_with_word_boundary(
                medication_normalized, _normalize_for_comparison(allergy.allergy_name)
            )
        ]
        if candidates:
            matched = min(candidates, key=lambda allergy: allergy.allergy_id)

    if matched is None:
        return AllergyConflictResult(
            has_conflict=False,
            rule_id=_ALLERGY_RULE_ID,
            matched_allergy_id=None,
            matched_allergy_name=None,
            medication_name=medication_name,
            priority=None,
            explanation=_ALLERGY_NO_CONFLICT_EXPLANATION,
        )

    return AllergyConflictResult(
        has_conflict=True,
        rule_id=_ALLERGY_RULE_ID,
        matched_allergy_id=matched.allergy_id,
        matched_allergy_name=matched.allergy_name,
        medication_name=medication_name,
        priority="HIGH",
        explanation=_ALLERGY_CONFLICT_EXPLANATION,
    )

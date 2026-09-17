"""검사값을 참고범위와 비교하는 중앙 규칙.

이 모듈은 순수 함수만 담는다: DB 조회, HTTP 처리, 감사 로그 작성, 전역
상태 변경을 하지 않으며, 같은 입력에는 항상 같은 결과를 반환한다.

evaluate_lab_abnormal()은 합성 검사값을 등록된 데모 참고범위와 기계적으로
비교할 뿐이다 — 의료 판단(진단/치료/처방 권고)을 수행하지 않는다. 최종
해석은 항상 의료진이 수행한다.
"""

from __future__ import annotations

import math
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

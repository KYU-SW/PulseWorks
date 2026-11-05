"""VitalSign의 canonical 단위, 품질 경고, BMI 파생값을 담는 중앙 규칙 모음.

safety_rules.py(evaluate_lab_abnormal, check_allergy_conflict)와 같은
원칙을 따른다: 이 모듈은 순수 함수만 담는다 — DB 조회, HTTP 처리, 감사
로그 작성, 전역 상태 변경을 하지 않으며, 같은 입력에는 항상 같은 결과를
반환한다. 아무것도 DB에 저장하지 않는다(상태 컬럼 없음, BMI 저장 없음) —
호출할 때마다 다시 계산한다.

evaluate_vital_sign_quality()는 F1에서 확인한 KR Core IG v1.0.2 공식
구조(docs/standards/kr-cdi-kr-core-mapping.md)를 참고해 "혈압 component가
서로 역전됐는지", "canonical 단위와 다른지", "같은 시각에 중복 측정이
있는지"만 기계적으로 판단한다 — 유형별 임상 극단값(예: 체온 40도 이상)
기준은 의료진 검토 전까지 하드코딩하지 않는다. 극단적인 값이라는 이유만
으로 저장을 거부하거나 삭제하지 않는다 — 경고만 반환한다.

calculate_bmi()도 마찬가지로 기계적 계산만 한다 — 비만·저체중 같은
임상적 해석을 하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.models.enums import VitalType

# KR Core IG v1.0.2 StructureDefinition 페이지에서 직접 확인한 고정 단위
# (docs/standards/kr-cdi-kr-core-mapping.md §3). 체온은 ℃ 대신 ASCII
# 문자열 "Cel"을 canonical 값으로 쓴다 — 이 프로젝트의 다른 Enum류 값
# (Department/EncounterType 등)이 전부 ASCII이고 한글 표시는 별도 라벨
# 딕셔너리로 분리하는 것과 같은 패턴이며("degC"처럼 근거 없는 표기를
# 새로 만들지 않고, UCUM이 실제로 쓰는 코드 "Cel"을 그대로 재사용), 여러
# 시스템(Python/Postgres/JSON/TypeScript)을 오가며 등가 비교를 해야 하는
# 값이라 유니코드 정규화(NFC/NFD) 불일치로 "==" 비교가 깨질 수 있는
# 위험을 원천적으로 피한다. 화면에는 별도 표시 라벨(프론트엔드)로 "℃"를
# 보여준다 — canonical 값 자체를 바꾸지 않는다.
CANONICAL_UNITS: dict[VitalType, str] = {
    VitalType.BLOOD_PRESSURE: "mmHg",
    VitalType.BODY_HEIGHT: "cm",
    VitalType.BODY_WEIGHT: "kg",
    VitalType.BODY_TEMPERATURE: "Cel",
    VitalType.HEART_RATE: "/min",
    VitalType.RESPIRATORY_RATE: "/min",
    VitalType.PULSE_OXIMETRY: "%",
}


def is_canonical_unit(vital_type: VitalType, unit: str) -> bool:
    """신규 API·seed 입력을 거부할지 판단할 때, 그리고 환자 화면·LLM
    입력에 포함해도 되는지 판단할 때 쓰는 단일 기준."""
    return unit == CANONICAL_UNITS[vital_type]


class VitalSignQualityWarning(str, Enum):
    BLOOD_PRESSURE_REVERSED = "BLOOD_PRESSURE_REVERSED"
    NON_CANONICAL_UNIT = "NON_CANONICAL_UNIT"
    DUPLICATE_MEASUREMENT = "DUPLICATE_MEASUREMENT"


_WARNING_MESSAGES: dict[VitalSignQualityWarning, str] = {
    VitalSignQualityWarning.BLOOD_PRESSURE_REVERSED: (
        "수축기 값이 이완기 값보다 낮습니다."
    ),
    VitalSignQualityWarning.NON_CANONICAL_UNIT: (
        "측정 단위가 이 유형의 기본 단위와 다릅니다(원본 값은 그대로 보존됨)."
    ),
    VitalSignQualityWarning.DUPLICATE_MEASUREMENT: (
        "같은 방문·같은 유형·같은 측정 시각의 다른 기록이 이미 있습니다."
    ),
}


@dataclass(frozen=True)
class VitalSignLike:
    """evaluate_vital_sign_quality()/calculate_bmi()가 필요로 하는 필드만
    뽑은 최소 구조체 — SQLAlchemy VitalSign 모델에 직접 의존하지 않아
    순수 함수 원칙(DB 세션 없이도 테스트 가능)을 지킨다."""

    id: int
    encounter_id: int
    vital_type: VitalType
    value: Decimal
    value_secondary: Decimal | None
    unit: str
    measured_at: datetime


@dataclass(frozen=True)
class VitalSignQualityResult:
    warnings: list[VitalSignQualityWarning]
    messages: list[str]

    @property
    def has_warning(self) -> bool:
        return len(self.warnings) > 0


def evaluate_vital_sign_quality(
    candidate: VitalSignLike,
    existing_in_same_encounter: list[VitalSignLike],
) -> VitalSignQualityResult:
    """candidate 1건을 같은 Encounter에 이미 있는 나머지 기록들과 비교해
    객관적 규칙 3가지만 확인한다. 저장 자체를 막지 않는다 — 결과는 항상
    경고 목록일 뿐이다."""
    warnings: list[VitalSignQualityWarning] = []

    if (
        candidate.vital_type == VitalType.BLOOD_PRESSURE
        and candidate.value_secondary is not None
        and candidate.value < candidate.value_secondary
    ):
        warnings.append(VitalSignQualityWarning.BLOOD_PRESSURE_REVERSED)

    if not is_canonical_unit(candidate.vital_type, candidate.unit):
        warnings.append(VitalSignQualityWarning.NON_CANONICAL_UNIT)

    for other in existing_in_same_encounter:
        if other.id == candidate.id:
            continue
        if (
            other.encounter_id == candidate.encounter_id
            and other.vital_type == candidate.vital_type
            and other.measured_at == candidate.measured_at
        ):
            warnings.append(VitalSignQualityWarning.DUPLICATE_MEASUREMENT)
            break

    return VitalSignQualityResult(
        warnings=warnings,
        messages=[_WARNING_MESSAGES[w] for w in warnings],
    )


def calculate_bmi(
    height: VitalSignLike | None, weight: VitalSignLike | None
) -> Decimal | None:
    """동일 Encounter의 BODY_HEIGHT/BODY_WEIGHT 중 가장 최근 값으로 BMI를
    계산한다(둘 다 그 Encounter에서 가장 최근(measured_at 최대) 값을
    호출자가 미리 골라 넘겨준다 — 이 함수는 "그중 어떤 레코드를 고를지"는
    모르고 계산만 한다).

    다음 중 하나라도 해당하면 None을 반환한다(계산하지 않음) — 임상적
    판단이 아니라 계산 자체가 불가능하거나 신뢰할 수 없는 경우다:
    - height 또는 weight가 없음
    - 서로 다른 Encounter(호출자 책임이지만 방어적으로 한 번 더 확인)
    - canonical 단위가 아님(품질 경고가 붙을 만큼 단위가 의심스러운
      값으로는 계산하지 않음)
    - 신장이 0 이하(나눗셈이 불가능/무의미함 — 수학적 안전장치일 뿐,
      임상적 "저신장" 판단이 아니다)
    """
    if height is None or weight is None:
        return None
    if height.encounter_id != weight.encounter_id:
        return None
    if not is_canonical_unit(VitalType.BODY_HEIGHT, height.unit):
        return None
    if not is_canonical_unit(VitalType.BODY_WEIGHT, weight.unit):
        return None
    if height.value <= 0:
        return None

    height_m = height.value / Decimal("100")
    bmi = weight.value / (height_m * height_m)
    return bmi.quantize(Decimal("0.1"))

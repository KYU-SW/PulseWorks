from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import VitalType
from app.services.vital_sign_derived import (
    CANONICAL_UNITS,
    VitalSignLike,
    VitalSignQualityWarning,
    calculate_bmi,
    evaluate_vital_sign_quality,
    is_canonical_unit,
)


def _vs(
    id=1,
    encounter_id=1,
    vital_type=VitalType.HEART_RATE,
    value="72",
    value_secondary=None,
    unit=None,
    measured_at=None,
) -> VitalSignLike:
    return VitalSignLike(
        id=id,
        encounter_id=encounter_id,
        vital_type=vital_type,
        value=Decimal(value),
        value_secondary=Decimal(value_secondary) if value_secondary is not None else None,
        unit=unit if unit is not None else CANONICAL_UNITS[vital_type],
        measured_at=measured_at or datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )


# 1. canonical 단위 — 7종 전부 지정돼 있는지
def test_canonical_units_defined_for_all_seven_types():
    assert set(CANONICAL_UNITS.keys()) == {
        VitalType.BLOOD_PRESSURE,
        VitalType.BODY_HEIGHT,
        VitalType.BODY_WEIGHT,
        VitalType.BODY_TEMPERATURE,
        VitalType.HEART_RATE,
        VitalType.RESPIRATORY_RATE,
        VitalType.PULSE_OXIMETRY,
    }
    assert CANONICAL_UNITS[VitalType.BLOOD_PRESSURE] == "mmHg"
    assert CANONICAL_UNITS[VitalType.BODY_TEMPERATURE] == "Cel"  # ℃가 아니라 ASCII


def test_is_canonical_unit():
    assert is_canonical_unit(VitalType.HEART_RATE, "/min") is True
    assert is_canonical_unit(VitalType.HEART_RATE, "bpm") is False


# 2. 혈압 수축기 < 이완기는 경고만, 거부하지 않음(여기서는 '거부'라는
# 개념이 없다 — 경고 목록에 포함되는지만 확인)
def test_blood_pressure_reversed_produces_warning_not_rejection():
    candidate = _vs(vital_type=VitalType.BLOOD_PRESSURE, value="80", value_secondary="120")
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[])
    assert VitalSignQualityWarning.BLOOD_PRESSURE_REVERSED in result.warnings
    assert result.has_warning is True


def test_normal_blood_pressure_has_no_reversal_warning():
    candidate = _vs(vital_type=VitalType.BLOOD_PRESSURE, value="120", value_secondary="80")
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[])
    assert VitalSignQualityWarning.BLOOD_PRESSURE_REVERSED not in result.warnings


def test_equal_systolic_and_diastolic_is_not_reversed():
    # value < value_secondary일 때만 역전 — 같으면 역전이 아니다.
    candidate = _vs(vital_type=VitalType.BLOOD_PRESSURE, value="90", value_secondary="90")
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[])
    assert VitalSignQualityWarning.BLOOD_PRESSURE_REVERSED not in result.warnings


# 3. 비표준 단위 → 경고
def test_non_canonical_unit_produces_warning():
    candidate = _vs(vital_type=VitalType.HEART_RATE, unit="bpm")
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[])
    assert VitalSignQualityWarning.NON_CANONICAL_UNIT in result.warnings
    assert "기본 단위" in result.messages[0] or any("기본 단위" in m for m in result.messages)


# 4. 동일 encounter+vital_type+measured_at 중복 → 경고
def test_duplicate_measurement_produces_warning():
    t = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    existing = _vs(id=1, encounter_id=5, vital_type=VitalType.HEART_RATE, measured_at=t)
    candidate = _vs(id=2, encounter_id=5, vital_type=VitalType.HEART_RATE, measured_at=t)
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[existing])
    assert VitalSignQualityWarning.DUPLICATE_MEASUREMENT in result.warnings


def test_same_type_different_time_is_not_a_duplicate():
    existing = _vs(
        id=1, encounter_id=5, vital_type=VitalType.HEART_RATE,
        measured_at=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    candidate = _vs(
        id=2, encounter_id=5, vital_type=VitalType.HEART_RATE,
        measured_at=datetime(2026, 1, 1, 9, 5, tzinfo=timezone.utc),
    )
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[existing])
    assert VitalSignQualityWarning.DUPLICATE_MEASUREMENT not in result.warnings


def test_different_encounter_same_time_is_not_a_duplicate():
    existing = _vs(id=1, encounter_id=5, vital_type=VitalType.HEART_RATE)
    candidate = _vs(id=2, encounter_id=6, vital_type=VitalType.HEART_RATE)
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[existing])
    assert VitalSignQualityWarning.DUPLICATE_MEASUREMENT not in result.warnings


def test_comparing_a_record_against_itself_is_not_a_duplicate():
    candidate = _vs(id=1, encounter_id=5, vital_type=VitalType.HEART_RATE)
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[candidate])
    assert VitalSignQualityWarning.DUPLICATE_MEASUREMENT not in result.warnings


def test_no_hardcoded_clinical_extreme_value_warning():
    # 극단적인 값(체온 99도)이라도 canonical 단위·구조가 맞으면 경고가
    # 전혀 없어야 한다 — 임상 극단값 기준은 하드코딩하지 않는다.
    candidate = _vs(vital_type=VitalType.BODY_TEMPERATURE, value="99.0")
    result = evaluate_vital_sign_quality(candidate, existing_in_same_encounter=[])
    assert result.has_warning is False


# 5. BMI 계산
def test_bmi_calculates_successfully_when_both_present_and_valid():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="170")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65")
    bmi = calculate_bmi(height, weight)
    assert bmi == Decimal("22.5")  # 65 / 1.7^2 = 22.49134... -> 22.5


def test_bmi_rounds_to_one_decimal_place():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="180")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="70")
    bmi = calculate_bmi(height, weight)
    assert bmi == Decimal("21.6")  # 70 / 1.8^2 = 21.604938... -> 21.6
    assert bmi.as_tuple().exponent == -1  # 소수점 정확히 1자리


def test_bmi_is_none_when_height_missing():
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65")
    assert calculate_bmi(None, weight) is None


def test_bmi_is_none_when_weight_missing():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="170")
    assert calculate_bmi(height, None) is None


def test_bmi_is_none_for_different_encounters():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="170")
    weight = _vs(id=2, encounter_id=2, vital_type=VitalType.BODY_WEIGHT, value="65")
    assert calculate_bmi(height, weight) is None


def test_bmi_is_none_when_height_unit_is_not_canonical():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="170", unit="m")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65")
    assert calculate_bmi(height, weight) is None


def test_bmi_is_none_when_weight_unit_is_not_canonical():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="170")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65", unit="lb")
    assert calculate_bmi(height, weight) is None


def test_bmi_is_none_when_height_is_zero():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="0")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65")
    assert calculate_bmi(height, weight) is None


def test_bmi_is_none_when_height_is_negative():
    height = _vs(id=1, encounter_id=1, vital_type=VitalType.BODY_HEIGHT, value="-5")
    weight = _vs(id=2, encounter_id=1, vital_type=VitalType.BODY_WEIGHT, value="65")
    assert calculate_bmi(height, weight) is None

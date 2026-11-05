from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.models.enums import SourceType, VitalType
from app.schemas.vital_sign import VitalSignIn

_NOW = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def _base_kwargs(**overrides) -> dict:
    kwargs = dict(
        encounter_id=1,
        vital_type=VitalType.HEART_RATE,
        value=Decimal("72"),
        value_secondary=None,
        unit="/min",
        measured_at=_NOW,
        source_type=SourceType.INSTITUTION_GENERATED,
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_non_blood_pressure_input_is_accepted():
    vital = VitalSignIn(**_base_kwargs())
    assert vital.value == Decimal("72")
    assert vital.value_secondary is None


def test_valid_blood_pressure_with_both_components_is_accepted():
    vital = VitalSignIn(
        **_base_kwargs(
            vital_type=VitalType.BLOOD_PRESSURE,
            value=Decimal("120"),
            value_secondary=Decimal("80"),
            unit="mmHg",
        )
    )
    assert vital.value_secondary == Decimal("80")


# 혈압 두 component 필수 — 한쪽만 있으면 구조 오류로 거부
def test_blood_pressure_missing_diastolic_is_rejected():
    with pytest.raises(PydanticValidationError):
        VitalSignIn(
            **_base_kwargs(
                vital_type=VitalType.BLOOD_PRESSURE,
                value=Decimal("120"),
                value_secondary=None,
                unit="mmHg",
            )
        )


# 수축기<이완기(역전)는 구조 오류가 아니다 — 스키마는 거부하지 않는다
# (품질 경고로만 처리됨, app/services/vital_sign_derived.py에서 테스트).
def test_blood_pressure_reversed_values_are_still_accepted_by_schema():
    vital = VitalSignIn(
        **_base_kwargs(
            vital_type=VitalType.BLOOD_PRESSURE,
            value=Decimal("80"),
            value_secondary=Decimal("120"),
            unit="mmHg",
        )
    )
    assert vital.value == Decimal("80")
    assert vital.value_secondary == Decimal("120")


# 혈압 외 유형은 value_secondary를 가질 수 없음 — 구조 오류로 거부
@pytest.mark.parametrize(
    "vital_type,unit",
    [
        (VitalType.BODY_HEIGHT, "cm"),
        (VitalType.BODY_WEIGHT, "kg"),
        (VitalType.BODY_TEMPERATURE, "Cel"),
        (VitalType.HEART_RATE, "/min"),
        (VitalType.RESPIRATORY_RATE, "/min"),
        (VitalType.PULSE_OXIMETRY, "%"),
    ],
)
def test_non_blood_pressure_with_value_secondary_is_rejected(vital_type, unit):
    with pytest.raises(PydanticValidationError):
        VitalSignIn(
            **_base_kwargs(
                vital_type=vital_type,
                value=Decimal("1"),
                value_secondary=Decimal("1"),
                unit=unit,
            )
        )


# canonical 단위가 아닌 신규 입력은 구조 오류로 거부
@pytest.mark.parametrize(
    "vital_type,bad_unit",
    [
        (VitalType.BLOOD_PRESSURE, "kPa"),
        (VitalType.BODY_HEIGHT, "inch"),
        (VitalType.BODY_WEIGHT, "lb"),
        (VitalType.BODY_TEMPERATURE, "F"),
        (VitalType.HEART_RATE, "bpm"),
        (VitalType.RESPIRATORY_RATE, "bpm"),
        (VitalType.PULSE_OXIMETRY, "percent"),
    ],
)
def test_non_canonical_unit_on_new_input_is_rejected(vital_type, bad_unit):
    extra = {"value_secondary": Decimal("1")} if vital_type == VitalType.BLOOD_PRESSURE else {}
    with pytest.raises(PydanticValidationError):
        VitalSignIn(**_base_kwargs(vital_type=vital_type, unit=bad_unit, **extra))


def test_canonical_unit_for_each_type_is_accepted():
    cases = [
        (VitalType.BLOOD_PRESSURE, "mmHg", Decimal("80")),
        (VitalType.BODY_HEIGHT, "cm", None),
        (VitalType.BODY_WEIGHT, "kg", None),
        (VitalType.BODY_TEMPERATURE, "Cel", None),
        (VitalType.HEART_RATE, "/min", None),
        (VitalType.RESPIRATORY_RATE, "/min", None),
        (VitalType.PULSE_OXIMETRY, "%", None),
    ]
    for vital_type, unit, secondary in cases:
        vital = VitalSignIn(
            **_base_kwargs(vital_type=vital_type, unit=unit, value_secondary=secondary)
        )
        assert vital.unit == unit


def test_unknown_extra_field_is_rejected():
    with pytest.raises(PydanticValidationError):
        VitalSignIn(**_base_kwargs(), vendor="Ollama")

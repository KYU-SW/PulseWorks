"""VitalSign 신규 입력(seed·향후 API 공용)의 구조 오류 검증 스키마.

Task F4-A 범위 — 이 스키마는 "신규 입력"에만 적용되는 구조 오류 규칙만
담는다(app/services/vital_sign_derived.py의 §4 단위 정책 참고):

- BLOOD_PRESSURE는 value(수축기)·value_secondary(이완기)가 모두 있어야
  한다. 한쪽만 있으면 구조 오류(이번 스키마가 거부) — "정상 혈압
  기록"으로 취급하지 않는다.
- BLOOD_PRESSURE 이외의 6종은 value_secondary가 반드시 None이어야
  한다.
- unit은 vital_type별 canonical 단위와 정확히 같아야 한다(신규 입력
  기준 — 기존·외부 변환 데이터의 비표준 단위는 이 스키마를 거치지 않고
  보존되며, 품질 경고로만 표시된다. 이 스키마는 그 경로를 다루지 않음).

수축기<이완기(혈압 역전)는 이 스키마가 거부하지 않는다 — 구조 오류가
아니라 품질 경고이므로(app/services/vital_sign_derived.py가 저장 후
조회 시점에 경고로만 알려준다)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import SourceType, VitalType
from app.services.vital_sign_derived import is_canonical_unit


class VitalSignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encounter_id: int
    vital_type: VitalType
    value: Decimal
    value_secondary: Decimal | None = None
    unit: str
    measured_at: datetime
    source_type: SourceType

    @model_validator(mode="after")
    def _validate_blood_pressure_components(self) -> "VitalSignIn":
        if self.vital_type == VitalType.BLOOD_PRESSURE:
            if self.value_secondary is None:
                raise ValueError(
                    "BLOOD_PRESSURE는 value(수축기)와 value_secondary(이완기)가 "
                    "모두 있어야 합니다."
                )
        elif self.value_secondary is not None:
            raise ValueError(
                f"{self.vital_type.value}은 value_secondary를 가질 수 없습니다."
            )
        return self

    @model_validator(mode="after")
    def _validate_canonical_unit(self) -> "VitalSignIn":
        if not is_canonical_unit(self.vital_type, self.unit):
            raise ValueError(
                f"{self.vital_type.value}의 신규 입력 단위는 canonical 단위여야 합니다."
            )
        return self

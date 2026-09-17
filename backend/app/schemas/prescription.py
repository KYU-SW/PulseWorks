from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import SourceType


class PrescriptionCreate(BaseModel):
    """처방 생성 요청. patient_id/prescribed_by_user_id/id/생성·수정
    시각/is_deleted/SafetyAlert 관련 필드는 클라이언트가 신뢰할 수 없는
    값이므로 아예 필드로 두지 않는다 — extra="forbid"로, 그런 필드를 보내면
    무시하지 않고 422로 명시적으로 거부한다."""

    model_config = ConfigDict(extra="forbid")

    encounter_id: int
    medication_name: str
    dosage: str
    source_type: SourceType = SourceType.INSTITUTION_GENERATED

    @field_validator("medication_name", "dosage")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class PrescriptionOut(BaseModel):
    id: int
    encounter_id: int
    medication_name: str
    dosage: str
    source_type: str
    prescribed_by_user_id: int


class AllergyConflictOut(BaseModel):
    has_conflict: bool
    rule_id: str
    matched_allergy_id: int | None
    matched_allergy_name: str | None
    medication_name: str
    priority: str | None
    explanation: str


class PrescriptionCreateResponse(BaseModel):
    prescription: PrescriptionOut
    allergy_conflict: AllergyConflictOut
    safety_alert_created: bool

"""RealLLMProvider가 파싱하는 LLM 응답 구조. provider/model/version은
여기에 없다 - 그 값들은 신뢰할 수 없는 LLM 자기 보고 값이 아니라 항상
서버 설정과 RealLLMProvider가 직접 채운다.

evidence_tags는 실제 source_record_ids(내부 숫자 PK를 담은 "type:id"
문자열)가 아니라, 이 요청에 한해 서버가 부여한 익명 태그(E1/D1/L1/P1/A1
같은 문자열)다. LLM은 이 태그만 보고, 돌려주는 것도 이 태그만이다 -
RealLLMProvider가 태그를 검증한 뒤 실제 source_record_id로 역매핑해
NarrativeProviderResult.cited_record_ids를 채운다(app/services/
narrative_providers/prompt.py, real_llm_provider.py 참고)."""

from pydantic import BaseModel, ConfigDict, Field


class MentionedMeasurementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str
    value: float
    unit: str


class MentionedVitalSignIn(BaseModel):
    """Task F4-B: MentionedMeasurementIn과 같은 역할을 VitalSign에 대해
    담당한다. value_secondary는 BLOOD_PRESSURE의 이완기 값에만 쓴다."""

    model_config = ConfigDict(extra="forbid")

    vital_type: str
    value: float
    value_secondary: float | None = None
    unit: str


class LlmStructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narrative: str = Field(min_length=1, max_length=4000)
    # 필수 필드다(기본값 없음) - 필드가 통째로 빠지거나 빈 배열이면 여기서
    # 바로 거부된다(min_length=1 -> JSON Schema minItems=1). 그래도
    # RealLLMProvider._resolve_evidence_tags()의 빈 목록 거부는 지우지
    # 않는다 - 이 스키마를 우회해 직접 구성하는 경로(예: 테스트)에서도
    # 안전하도록 하는 defense-in-depth다.
    evidence_tags: list[str] = Field(
        min_length=1,
        description=(
            "narrative 작성에 실제로 사용한 항목의 태그만 담는다. "
            "[사용 가능한 태그] 목록에 있는 문자열만 사용하고, "
            "새 태그를 만들지 않는다. "
            "최소 1개 이상 반드시 포함한다."
        ),
    )
    mentioned_measurements: list[MentionedMeasurementIn] = Field(default_factory=list)
    # Task F4-B: VitalSign 전용 - mentioned_measurements(LabResult)와 같은
    # 자기 보고 계약을 공유하지 않는다(단위·혈압 두 component가 다른
    # 구조라 별도 필드).
    mentioned_vital_signs: list[MentionedVitalSignIn] = Field(default_factory=list)

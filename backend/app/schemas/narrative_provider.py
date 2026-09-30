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


class LlmStructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narrative: str = Field(min_length=1, max_length=4000)
    evidence_tags: list[str] = Field(default_factory=list)
    mentioned_measurements: list[MentionedMeasurementIn] = Field(default_factory=list)

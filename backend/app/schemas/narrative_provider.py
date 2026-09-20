"""RealLLMProvider가 파싱하는 LLM 응답 구조. provider/model/version은
여기에 없다 - 그 값들은 신뢰할 수 없는 LLM 자기 보고 값이 아니라 항상
서버 설정과 RealLLMProvider가 직접 채운다."""

from pydantic import BaseModel, ConfigDict, Field


class MentionedMeasurementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str
    value: float
    unit: str


class LlmStructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narrative: str = Field(min_length=1, max_length=4000)
    cited_record_ids: list[str] = Field(default_factory=list)
    mentioned_measurements: list[MentionedMeasurementIn] = Field(default_factory=list)

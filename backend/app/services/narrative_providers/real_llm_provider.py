from pydantic import ValidationError

from app.schemas.clinical_report import EmrSnapshot
from app.schemas.narrative_provider import LlmStructuredOutput
from app.services.narrative_providers.base import (
    MentionedMeasurement,
    MentionedVitalSign,
    NarrativeProvider,
    NarrativeProviderError,
    NarrativeProviderResult,
)
from app.services.narrative_providers.llm_client import LlmHttpClient, LlmHttpError
from app.services.narrative_providers.prompt import build_narrative_prompt

# 실제 벤더별 이름은 그 벤더의 Adapter를 구현할 때 부여한다(아직 없음).
# version은 LLM 모델 자체의 버전이 아니라 이 provider 연동 방식의
# 버전이다(Mock의 version="1"과 같은 의미) - LLM 모델명은 model 필드가
# 담당한다.
_PROVIDER_NAME = "LLM"
_PROVIDER_VERSION = "1"


def _resolve_evidence_tags(tags: list[str], tag_to_source_record_id: dict[str, str]) -> list[str]:
    """LLM이 돌려준 익명 evidence_tags를 실제 source_record_id로
    역매핑한다. 허용되지 않은 태그가 하나라도 있으면 일부만 신뢰하지
    않고 전체를 거부한다. 빈 목록도 거부한다(LLM 결과는 근거가
    필수라는 기존 정책 그대로). 중복 태그는 첫 등장 순서를 유지한 채
    제거한다."""
    if not tags:
        raise NarrativeProviderError("LLM_EVIDENCE_TAGS_EMPTY")

    resolved: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag not in tag_to_source_record_id:
            raise NarrativeProviderError("LLM_EVIDENCE_TAG_UNKNOWN")
        if tag in seen:
            continue
        seen.add(tag)
        resolved.append(tag_to_source_record_id[tag])
    return resolved


class RealLLMProvider(NarrativeProvider):
    """LlmHttpClient를 주입받는다 - 벤더 SDK를 직접 import하지 않고
    네트워크 요청 형식도 직접 구현하지 않는다. 실제 벤더 Adapter(예:
    특정 회사의 REST API를 호출하는 구체 클래스)는 이번 단계에서
    만들지 않는다 - 테스트에서는 LlmHttpClient를 만족하는 가짜 client만
    주입한다."""

    def __init__(
        self,
        client: LlmHttpClient,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float,
    ):
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds

    def generate(self, snapshot: EmrSnapshot) -> NarrativeProviderResult:
        prompt = build_narrative_prompt(snapshot)

        try:
            raw = self._client.complete(
                model=self._model,
                prompt=prompt.text,
                max_output_tokens=self._max_output_tokens,
                timeout_seconds=self._timeout_seconds,
            )
        except LlmHttpError as exc:
            raise NarrativeProviderError("LLM_REQUEST_FAILED") from exc

        try:
            parsed = LlmStructuredOutput.model_validate_json(raw)
        except ValidationError as exc:
            raise NarrativeProviderError("LLM_OUTPUT_INVALID_JSON") from exc

        cited_record_ids = _resolve_evidence_tags(
            parsed.evidence_tags, prompt.tag_to_source_record_id
        )

        return NarrativeProviderResult(
            narrative=parsed.narrative,
            cited_record_ids=cited_record_ids,
            mentioned_measurements=[
                MentionedMeasurement(test_name=m.test_name, value=m.value, unit=m.unit)
                for m in parsed.mentioned_measurements
            ],
            provider=_PROVIDER_NAME,
            model=self._model,
            version=_PROVIDER_VERSION,
            mentioned_vital_signs=[
                MentionedVitalSign(
                    vital_type=v.vital_type,
                    value=v.value,
                    value_secondary=v.value_secondary,
                    unit=v.unit,
                )
                for v in parsed.mentioned_vital_signs
            ],
        )

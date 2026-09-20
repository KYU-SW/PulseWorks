"""narrative_provider 설정값에 따라 NarrativeProvider 구현체를 고른다.

llm 모드인데 키/모델이 없거나 실제 Adapter가 아직 없으면 Mock으로
조용히 대체하지 않고 항상 NarrativeProviderError를 던진다 - 라우터가
이를 잡아 명확한 설정 오류 응답으로 바꾼다."""

from app.core.config import Settings, get_settings
from app.services.narrative_providers.base import NarrativeProvider, NarrativeProviderError
from app.services.narrative_providers.mock_provider import DeterministicMockProvider


def get_narrative_provider(settings: Settings | None = None) -> NarrativeProvider:
    settings = settings or get_settings()

    if settings.narrative_provider == "mock":
        return DeterministicMockProvider()

    # settings.narrative_provider == "llm" (Settings 필드 검증이 이 두
    # 값만 허용하므로 다른 값은 여기 도달하지 않는다).
    if not settings.llm_api_key:
        raise NarrativeProviderError("LLM_API_KEY_MISSING")
    if not settings.llm_model:
        raise NarrativeProviderError("LLM_MODEL_MISSING")

    # 벤더별 실제 HTTP Adapter는 이번 단계에서 구현하지 않는다 -
    # LlmHttpClient를 만족하는 구체 구현이 없으므로, 키와 모델이 모두
    # 있어도 조용히 Mock으로 대체하지 않고 명확한 미구성 오류로 끝낸다.
    raise NarrativeProviderError(
        "LLM_NOT_CONFIGURED", "실제 LLM Adapter가 아직 구성되지 않았습니다."
    )

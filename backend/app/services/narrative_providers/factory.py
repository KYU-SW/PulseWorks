"""narrative_provider 설정값에 따라 NarrativeProvider 구현체를 고른다.

llm 모드인데 필요한 설정이 없거나 지원하지 않는 벤더면 Mock으로
조용히 대체하지 않고 항상 NarrativeProviderError를 던진다 - 라우터가
이를 잡아 명확한 설정 오류 응답으로 바꾼다.

벤더별 API 키 요구사항은 다르다(Ollama는 로컬 실행이라 키가 필요
없다) - 그래서 "llm 모드면 무조건 llm_api_key가 있어야 한다"는 검사를
공통으로 두지 않고, 벤더 분기 안에서 그 벤더가 실제로 필요로 하는
값만 검사한다. vendor가 없거나 지원하지 않는 값이면 ollama로
추측해서 넘어가지 않고 바로 실패한다."""

from app.core.config import Settings, get_settings
from app.services.narrative_providers.base import NarrativeProvider, NarrativeProviderError
from app.services.narrative_providers.mock_provider import DeterministicMockProvider
from app.services.narrative_providers.ollama_client import OllamaHttpClient
from app.services.narrative_providers.real_llm_provider import RealLLMProvider


def get_narrative_provider(settings: Settings | None = None) -> NarrativeProvider:
    settings = settings or get_settings()

    if settings.narrative_provider == "mock":
        return DeterministicMockProvider()

    # settings.narrative_provider == "llm" (Settings 필드 검증이 이 두
    # 값만 허용하므로 다른 값은 여기 도달하지 않는다).
    if not settings.llm_vendor:
        raise NarrativeProviderError("LLM_VENDOR_MISSING")

    if settings.llm_vendor == "ollama":
        # 로컬 Ollama는 API 키가 필요 없다 - llm_api_key는 여기서
        # 검사하지 않는다.
        if not settings.llm_base_url:
            raise NarrativeProviderError("LLM_BASE_URL_MISSING")
        if not settings.llm_model:
            raise NarrativeProviderError("LLM_MODEL_MISSING")
        client = OllamaHttpClient(base_url=settings.llm_base_url)
        return RealLLMProvider(
            client=client,
            model=settings.llm_model,
            max_output_tokens=settings.llm_max_output_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    # 상용 벤더는 이번 단계에서 구현하지 않는다 - 나중에 추가할 때는
    # 이 자리에 그 벤더만의 분기(예: API 키 필수 검사 + Adapter 조립)를
    # 새로 추가한다.
    raise NarrativeProviderError("LLM_VENDOR_UNSUPPORTED")

"""RealLLMProvider가 의존하는 최소 HTTP client 경계.

이 Protocol을 만족하는 구체 구현(예: 특정 벤더의 REST API를 호출하는
클래스)이 벤더 SDK/요청 형식과 결합하는 유일한 지점이다. 이번 단계는
이 Protocol과 RealLLMProvider 골격만 두고, 실제 벤더 Adapter는 구현하지
않는다 - 테스트에서는 이 Protocol을 만족하는 가짜 client만 사용한다.
"""

from typing import Protocol


class LlmHttpError(Exception):
    """네트워크 실패, 타임아웃, 비정상 상태 코드 등 LlmHttpClient
    구현체가 던지는 공통 예외. 벤더별 원인 구분은 이 예외의 책임이
    아니다 - RealLLMProvider가 이를 잡아 NarrativeProviderError로
    변환한다."""


class LlmHttpClient(Protocol):
    def complete(
        self, *, model: str, prompt: str, max_output_tokens: int, timeout_seconds: float
    ) -> str:
        """LLM의 원문 응답(JSON 문자열)을 반환하거나 LlmHttpError를
        던진다. 이 메서드 자체가 이미 구조화된 결과를 신뢰하지 않는다 -
        호출자(RealLLMProvider)가 반환값을 Pydantic으로 다시 검증한다."""
        ...

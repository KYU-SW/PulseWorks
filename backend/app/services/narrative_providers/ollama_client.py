"""LlmHttpClient Protocol을 구현하는 로컬 Ollama 전용 Adapter (Task B).

이 파일이 Ollama API(엔드포인트, 요청 body 형식, 응답 envelope)와
결합하는 유일한 지점이다 - RealLLMProvider/factory는 이 파일의 내부
구조를 전혀 모른다. evidence_tags 역매핑, narrative 의미 검증, 검사값
검증, 금지 표현 검사, DB 저장, 감사 로그, Mock 대체는 전부 이 클래스의
책임이 아니다 - 이 클래스는 "HTTP로 문자열 하나를 받아온다" 그 이상을
하지 않는다.

think=false, stream=false, temperature=0을 항상 명시한다 - 사용자가
끄고 켤 수 있는 옵션으로 만들지 않는다. Ollama가 응답에 thinking
필드를 함께 돌려줘도 이 코드는 그 필드를 절대 읽지/저장/로그하지
않는다 - message.content만 꺼내 그대로 반환하고, 그 내용이
LlmStructuredOutput과 일치하는지는 검증하지 않는다(그건 여전히
RealLLMProvider의 Pydantic 검증이 최종 신뢰 경계다).
"""

from __future__ import annotations

import time

import httpx

from app.schemas.narrative_provider import LlmStructuredOutput
from app.services.narrative_providers.llm_client import LlmHttpError

_CHAT_PATH = "/api/chat"
_CONNECT_TIMEOUT_SECONDS = 5.0
_MAX_ATTEMPTS = 2  # 최초 1회 + 재시도 가능한 오류에 한해 최대 1회 추가
_RETRY_DELAY_SECONDS = 0.5


class OllamaHttpClient:
    """base_url 예: "http://host.docker.internal:11434"(컨테이너) 또는
    "http://localhost:11434"(호스트 직접 실행) - 어느 쪽을 쓸지는
    LLM_BASE_URL 설정이 결정하고, 이 클래스는 받은 값을 그대로 쓴다.

    transport는 테스트에서 httpx.MockTransport를 주입하기 위한
    파라미터다 - 운영 중에는 항상 None(실제 네트워크)이다.
    """

    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None):
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def complete(
        self, *, model: str, prompt: str, max_output_tokens: int, timeout_seconds: float
    ) -> str:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "format": LlmStructuredOutput.model_json_schema(),
            "options": {
                "temperature": 0,
                "num_predict": max_output_tokens,
            },
        }
        timeout = httpx.Timeout(
            connect=_CONNECT_TIMEOUT_SECONDS,
            read=timeout_seconds,
            write=timeout_seconds,
            pool=timeout_seconds,
        )

        last_error = LlmHttpError("ollama_unknown_error")
        for attempt in range(_MAX_ATTEMPTS):
            if attempt > 0:
                time.sleep(_RETRY_DELAY_SECONDS)

            try:
                with httpx.Client(transport=self._transport, timeout=timeout) as client:
                    response = client.post(f"{self._base_url}{_CHAT_PATH}", json=payload)
            except httpx.TimeoutException:
                last_error = LlmHttpError("ollama_timeout")
                continue
            except httpx.RequestError:
                last_error = LlmHttpError("ollama_connection_failed")
                continue

            # 429(일시적 제한)와 5xx(서버 오류)만 재시도 가능한 것으로
            # 분류한다 - 그 외 4xx(모델 미설치·모델명 오류 포함)는 같은
            # 요청을 반복해도 결과가 바뀌지 않는 설정/요청 오류라 즉시
            # 실패시킨다.
            if response.status_code == 429 or response.status_code >= 500:
                last_error = LlmHttpError("ollama_server_error")
                continue
            if response.status_code >= 400:
                raise LlmHttpError("ollama_client_error")

            return self._extract_content(response)

        raise last_error

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError as exc:
            raise LlmHttpError("ollama_invalid_envelope") from exc

        if not isinstance(body, dict):
            raise LlmHttpError("ollama_invalid_envelope")

        message = body.get("message")
        if not isinstance(message, dict):
            raise LlmHttpError("ollama_invalid_envelope")

        # message.thinking은 존재해도 절대 읽지 않는다(사고 내용 격리
        # 정책) - content만 꺼낸다.
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmHttpError("ollama_empty_content")

        return content

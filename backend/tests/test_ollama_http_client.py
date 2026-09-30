"""OllamaHttpClient(Task B) 단위 테스트.

실제 Ollama 서버를 호출하지 않는다 - httpx.MockTransport로 HTTP
레벨을 스텁한다. 이 파일은 벤더 결합 지점(OllamaHttpClient) 자체만
검증하고, RealLLMProvider/evidence_tags 통합은 test_narrative_providers.py
에서 별도로 확인한다.
"""

import json

import httpx
import pytest

from app.schemas.narrative_provider import LlmStructuredOutput
from app.services.narrative_providers.llm_client import LlmHttpError
from app.services.narrative_providers.ollama_client import OllamaHttpClient

BASE_URL = "http://ollama.invalid:11434"
DISTINCTIVE_PROMPT = "이 문자열은 예외 메시지에 절대 나타나면 안 되는 프롬프트 마커-XYZ123"


def _transport(handler):
    return httpx.MockTransport(handler)


def _client(handler, base_url: str = BASE_URL) -> OllamaHttpClient:
    return OllamaHttpClient(base_url=base_url, transport=_transport(handler))


def _ok_envelope(content: str, extra_message_fields: dict | None = None) -> httpx.Response:
    message = {"role": "assistant", "content": content}
    if extra_message_fields:
        message.update(extra_message_fields)
    return httpx.Response(200, json={"model": "qwen3:8b", "message": message, "done": True})


VALID_CONTENT = json.dumps(
    {"narrative": "x", "evidence_tags": ["L1"], "mentioned_measurements": []}
)


# ============================== 요청 구성 ====================================


class TestRequestConstruction:
    def test_calls_the_correct_chat_url(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["url"] == f"{BASE_URL}/api/chat"

    def test_passes_the_model(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["model"] == "qwen3:8b"

    def test_sets_stream_false(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["stream"] is False

    def test_sets_think_false(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["think"] is False

    def test_sets_temperature_zero(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["options"]["temperature"] == 0

    def test_passes_a_json_schema_format_matching_llm_structured_output(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["format"] == LlmStructuredOutput.model_json_schema()

    def test_passes_the_prompt_inside_the_messages_array(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt=DISTINCTIVE_PROMPT, max_output_tokens=500, timeout_seconds=10
        )
        assert seen["body"]["messages"] == [{"role": "user", "content": DISTINCTIVE_PROMPT}]

    def test_never_sends_an_api_key_or_authorization_header(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["headers"] = {k.lower() for k in request.headers.keys()}
            return _ok_envelope(VALID_CONTENT)

        _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert "authorization" not in seen["headers"]
        assert "x-api-key" not in seen["headers"]


# ============================== 응답 추출 ====================================


class TestResponseExtraction:
    def test_extracts_message_content_on_success(self):
        result = _client(lambda r: _ok_envelope(VALID_CONTENT)).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert result == VALID_CONTENT

    def test_ignores_a_thinking_field_and_returns_only_content(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _ok_envelope(VALID_CONTENT, extra_message_fields={"thinking": "숨겨야 할 사고 과정"})

        result = _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert result == VALID_CONTENT
        assert "사고 과정" not in result

    def test_rejects_empty_content(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _ok_envelope("")

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_empty_content"

    def test_rejects_a_response_with_only_thinking_and_no_content(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "qwen3:8b",
                    "message": {"role": "assistant", "thinking": "생각만 있음"},
                    "done": True,
                },
            )

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_empty_content"

    def test_rejects_an_envelope_without_a_message_field(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"model": "qwen3:8b", "done": True})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_invalid_envelope"

    def test_rejects_an_invalid_json_envelope(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json at all")

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_invalid_envelope"


# ============================== 오류 변환 ====================================


class TestErrorConversion:
    def test_converts_a_4xx_response_without_retrying(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(404, json={"error": "model 'x' not found"})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="missing-model", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_client_error"
        assert calls["count"] == 1  # 4xx는 재시도하지 않는다

    def test_retries_a_5xx_response_at_most_once(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(500, json={"error": "boom"})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_server_error"
        assert calls["count"] == 2  # 최초 1회 + 재시도 1회

    def test_a_5xx_then_success_recovers_on_the_retry(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(500, json={"error": "boom"})
            return _ok_envelope(VALID_CONTENT)

        result = _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert result == VALID_CONTENT
        assert calls["count"] == 2

    def test_retries_a_429_response_at_most_once(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(429, json={"error": "rate limited"})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_server_error"
        assert calls["count"] == 2

    def test_converts_a_connection_failure_and_retries_at_most_once(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            raise httpx.ConnectError("connection refused")

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_connection_failed"
        assert calls["count"] == 2

    def test_converts_a_timeout_and_retries_at_most_once(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            raise httpx.ReadTimeout("timed out")

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert str(exc_info.value) == "ollama_timeout"
        assert calls["count"] == 2

    def test_invalid_json_content_is_not_retried(self):
        # Adapter는 content의 JSON 유효성을 검사하지 않고 그대로
        # 반환한다 - "잘못된 JSON"은 RealLLMProvider의 몫이라 Adapter
        # 레벨에서는 재시도 대상이 될 수 없다(애초에 오류로 보지 않음).
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return _ok_envelope("not json at all")

        result = _client(handler).complete(
            model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
        )
        assert result == "not json at all"
        assert calls["count"] == 1


# ============================== 예외 메시지에 원문 미포함 =======================


class TestExceptionMessagesNeverLeakRawContent:
    def test_prompt_text_never_appears_in_the_exception(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b",
                prompt=DISTINCTIVE_PROMPT,
                max_output_tokens=500,
                timeout_seconds=10,
            )
        assert DISTINCTIVE_PROMPT not in str(exc_info.value)

    def test_raw_response_body_never_appears_in_the_exception(self):
        distinctive_error_body = "매우-특이한-원본-응답-마커-QRS789"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": distinctive_error_body})

        with pytest.raises(LlmHttpError) as exc_info:
            _client(handler).complete(
                model="qwen3:8b", prompt="p", max_output_tokens=500, timeout_seconds=10
            )
        assert distinctive_error_body not in str(exc_info.value)

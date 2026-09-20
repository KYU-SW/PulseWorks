import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.schemas.clinical_report import EmrSnapshot
from app.services.mock_narrative import generate_mock_report_narrative
from app.services.narrative_providers.base import (
    MentionedMeasurement,
    NarrativeProviderError,
    NarrativeProviderResult,
)
from app.services.narrative_providers.factory import get_narrative_provider
from app.services.narrative_providers.llm_client import LlmHttpError
from app.services.narrative_providers.mock_provider import DeterministicMockProvider
from app.services.narrative_providers.real_llm_provider import RealLLMProvider


def _snapshot(**overrides) -> EmrSnapshot:
    base = {
        "patient": {"id": 1, "mrn": "SYN-0001", "name": "합성환자-내분비01", "birth_date": "1968-04-12"},
        "encounters": [
            {
                "id": 1, "department": "ENDOCRINOLOGY", "encounter_type": "OUTPATIENT",
                "start_time": "2026-03-10T09:00:00Z", "end_time": None,
            }
        ],
        "diagnoses": [],
        "lab_results": [
            {
                "id": 1, "encounter_id": 1, "test_name": "HbA1c", "value": 8.1, "unit": "%",
                "reference_low": 4.0, "reference_high": 6.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "HIGH", "rule_id": "LAB_REFERENCE_RANGE",
            }
        ],
        "lab_trends": [],
        "prescriptions": [],
        "allergies": [],
        "safety_alerts": [],
        "clinical_notes": [],
        "source_record_ids": ["encounter:1", "lab_result:1"],
    }
    base.update(overrides)
    return EmrSnapshot.model_validate(base)


# ============================== DeterministicMockProvider ===================


class TestDeterministicMockProvider:
    def test_matches_generate_mock_report_narrative_exactly(self):
        snapshot = _snapshot()

        wrapped = DeterministicMockProvider().generate(snapshot)
        direct = generate_mock_report_narrative(snapshot)

        assert wrapped.narrative == direct.summary_text
        assert wrapped.cited_record_ids == direct.source_record_ids

    def test_reports_the_expected_provider_model_version(self):
        result = DeterministicMockProvider().generate(_snapshot())

        assert result.provider == "DETERMINISTIC_MOCK"
        assert result.model == "n/a"
        assert result.version == "1"

    def test_never_produces_mentioned_measurements(self):
        result = DeterministicMockProvider().generate(_snapshot())
        assert result.mentioned_measurements == []


# ============================== RealLLMProvider ==============================


class _FakeLlmHttpClient:
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    def complete(self, *, model, prompt, max_output_tokens, timeout_seconds):
        self.calls.append(
            {"model": model, "prompt": prompt, "max_output_tokens": max_output_tokens,
             "timeout_seconds": timeout_seconds}
        )
        if self._error is not None:
            raise self._error
        return self._response


VALID_LLM_JSON = (
    '{"narrative": "HbA1c가 8.1%로 확인됩니다.", '
    '"cited_record_ids": ["lab_result:1"], '
    '"mentioned_measurements": [{"test_name": "HbA1c", "value": 8.1, "unit": "%"}]}'
)


class TestRealLLMProvider:
    def test_parses_a_valid_json_response(self):
        client = _FakeLlmHttpClient(response=VALID_LLM_JSON)
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())

        assert result.narrative == "HbA1c가 8.1%로 확인됩니다."
        assert result.cited_record_ids == ["lab_result:1"]
        assert result.mentioned_measurements == [MentionedMeasurement("HbA1c", 8.1, "%")]

    def test_sets_server_controlled_provider_model_version(self):
        client = _FakeLlmHttpClient(response=VALID_LLM_JSON)
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())

        assert result.provider == "LLM"
        assert result.model == "test-model"
        assert result.version == "1"

    def test_passes_the_prompt_and_model_config_to_the_client(self):
        client = _FakeLlmHttpClient(response=VALID_LLM_JSON)
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        provider.generate(_snapshot())

        assert client.calls[0]["model"] == "test-model"
        assert client.calls[0]["max_output_tokens"] == 500
        assert client.calls[0]["timeout_seconds"] == 10
        assert "HbA1c" in client.calls[0]["prompt"]

    def test_rejects_invalid_json(self):
        client = _FakeLlmHttpClient(response="not json at all")
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_OUTPUT_INVALID_JSON"

    def test_rejects_a_response_with_an_extra_unexpected_field(self):
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "cited_record_ids": [], "mentioned_measurements": [], '
            '"provider": "SNEAKY_SELF_REPORTED_PROVIDER"}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_OUTPUT_INVALID_JSON"

    def test_converts_a_client_error_into_a_narrative_provider_error(self):
        client = _FakeLlmHttpClient(error=LlmHttpError("timeout"))
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_REQUEST_FAILED"

    def test_never_lets_the_llm_self_report_provider_model_version(self):
        # provider/model/version 필드가 LLM 출력 스키마에 아예 없으므로,
        # 응답에 그 필드가 있으면(extra="forbid") 거부되어야 한다 -
        # test_rejects_a_response_with_an_extra_unexpected_field가 이미
        # 확인하지만, 여기서는 서버가 항상 자기 설정값을 쓴다는 점을
        # 명시적으로 재확인한다.
        client = _FakeLlmHttpClient(response=VALID_LLM_JSON)
        provider = RealLLMProvider(client=client, model="server-configured-model", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())
        assert result.model == "server-configured-model"


# ============================== Factory ======================================


class TestGetNarrativeProvider:
    def test_defaults_to_mock(self):
        settings = Settings(narrative_provider="mock")
        provider = get_narrative_provider(settings)
        assert isinstance(provider, DeterministicMockProvider)

    def test_explicit_mock_returns_deterministic_mock_provider(self):
        settings = Settings(narrative_provider="mock", llm_api_key=None, llm_model="")
        provider = get_narrative_provider(settings)
        assert isinstance(provider, DeterministicMockProvider)

    def test_unknown_provider_is_rejected_at_settings_construction(self):
        with pytest.raises(PydanticValidationError):
            Settings(narrative_provider="unknown")

    def test_non_positive_timeout_is_rejected_at_settings_construction(self):
        with pytest.raises(PydanticValidationError):
            Settings(llm_timeout_seconds=0)
        with pytest.raises(PydanticValidationError):
            Settings(llm_timeout_seconds=-5)

    def test_non_positive_max_output_tokens_is_rejected_at_settings_construction(self):
        with pytest.raises(PydanticValidationError):
            Settings(llm_max_output_tokens=0)

    def test_llm_without_api_key_is_rejected(self):
        settings = Settings(narrative_provider="llm", llm_api_key=None, llm_model="gpt-4")
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_API_KEY_MISSING"

    def test_llm_without_model_is_rejected(self):
        settings = Settings(narrative_provider="llm", llm_api_key="sk-fake", llm_model="")
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_MODEL_MISSING"

    def test_llm_with_key_and_model_still_fails_because_no_adapter_exists(self):
        settings = Settings(narrative_provider="llm", llm_api_key="sk-fake", llm_model="gpt-4")
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_NOT_CONFIGURED"

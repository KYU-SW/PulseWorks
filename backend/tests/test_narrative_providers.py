import json
import re

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.schemas.clinical_report import EmrSnapshot
from app.schemas.narrative_provider import LlmStructuredOutput
from app.services.mock_narrative import generate_mock_report_narrative
from app.services.narrative_providers.base import (
    MentionedMeasurement,
    NarrativeProviderError,
    NarrativeProviderResult,
)
from app.services.narrative_providers.factory import get_narrative_provider
from app.services.narrative_providers.llm_client import LlmHttpError
from app.services.narrative_providers.mock_provider import DeterministicMockProvider
from app.services.narrative_providers.ollama_client import OllamaHttpClient
from app.services.narrative_providers.prompt import build_narrative_prompt
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


def _full_snapshot() -> EmrSnapshot:
    """encounter/diagnosis/lab_result/prescription/allergy를 모두 최소
    1개씩 포함한 스냅샷 - 5개 태그 접두사(E/D/L/P/A)를 전부 검증하는 데
    쓴다."""
    return _snapshot(
        diagnoses=[
            {
                "id": 7, "encounter_id": 1, "code": "E11.9", "description": "2형 당뇨병",
                "diagnosed_at": "2026-03-10T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
        prescriptions=[
            {
                "id": 9, "encounter_id": 1, "medication_name": "Metformin", "dosage": "500mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            }
        ],
        allergies=[
            {
                "id": 3, "substance": "Penicillin", "reaction": "두드러기", "severity": "MODERATE",
                "recorded_at": "2026-01-01T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
    )


# ============================== LlmStructuredOutput 스키마 (evidence_tags) =======


class TestLlmStructuredOutputEvidenceTagsSchema:
    def test_evidence_tags_is_required(self):
        schema = LlmStructuredOutput.model_json_schema()
        assert "evidence_tags" in schema["required"]

    def test_evidence_tags_has_min_items_one(self):
        schema = LlmStructuredOutput.model_json_schema()
        assert schema["properties"]["evidence_tags"]["minItems"] == 1

    def test_evidence_tags_has_a_non_empty_description(self):
        schema = LlmStructuredOutput.model_json_schema()
        description = schema["properties"]["evidence_tags"]["description"]
        assert "최소 1개 이상" in description
        assert "[사용 가능한 태그]" in description
        assert "새 태그를 만들지 않는다" in description


# ============================== build_narrative_prompt (익명 근거 태그) =========


class TestBuildNarrativePrompt:
    def test_never_includes_the_raw_source_record_ids(self):
        snapshot = _full_snapshot()
        prompt = build_narrative_prompt(snapshot)

        for source_id in snapshot.source_record_ids:
            assert source_id not in prompt.text

    def test_never_includes_an_internal_type_colon_id_pattern(self):
        snapshot = _full_snapshot()
        prompt = build_narrative_prompt(snapshot)

        assert not re.search(
            r"\b(encounter|diagnosis|lab_result|prescription|allergy|safety_alert|clinical_note):\d+\b",
            prompt.text,
        )

    def test_is_deterministic_for_the_same_snapshot(self):
        snapshot = _full_snapshot()

        first = build_narrative_prompt(snapshot)
        second = build_narrative_prompt(snapshot)

        assert first.text == second.text
        assert first.tag_to_source_record_id == second.tag_to_source_record_id

    def test_uses_the_correct_prefix_for_each_record_type(self):
        snapshot = _full_snapshot()
        prompt = build_narrative_prompt(snapshot)

        assert prompt.tag_to_source_record_id["E1"] == "encounter:1"
        assert prompt.tag_to_source_record_id["D1"] == "diagnosis:7"
        assert prompt.tag_to_source_record_id["L1"] == "lab_result:1"
        assert prompt.tag_to_source_record_id["P1"] == "prescription:9"
        assert prompt.tag_to_source_record_id["A1"] == "allergy:3"

    def test_tags_appear_inline_next_to_their_own_item_in_the_prompt_text(self):
        prompt = build_narrative_prompt(_full_snapshot())

        assert "[E1]" in prompt.text
        assert "[D1]" in prompt.text
        assert "[L1]" in prompt.text
        assert "[P1]" in prompt.text
        assert "[A1]" in prompt.text

    def test_never_generates_tags_for_safety_alerts_or_clinical_notes(self):
        snapshot = _snapshot(
            safety_alerts=[
                {
                    "id": 1, "encounter_id": 1, "prescription_id": None, "lab_result_id": 1,
                    "rule_id": "LAB_REFERENCE_RANGE", "priority": "HIGH",
                    "evidence": {}, "created_at": "2026-09-17T14:52:27Z",
                }
            ],
            clinical_notes=[
                {
                    "id": 1, "encounter_id": 1, "author_user_id": 1, "preview_text": "미리보기",
                    "created_at": "2026-03-10T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
                }
            ],
        )
        prompt = build_narrative_prompt(snapshot)

        assert not any(tag.startswith("S") or tag.startswith("C") for tag in prompt.tag_to_source_record_id)
        assert "LAB_REFERENCE_RANGE" not in prompt.text
        assert "미리보기" not in prompt.text

    def test_allowed_tags_block_lists_every_tag_in_the_map(self):
        snapshot = _full_snapshot()
        prompt = build_narrative_prompt(snapshot)

        allowed_line = next(line for line in prompt.text.splitlines() if line.startswith("[사용 가능한 태그]"))
        for tag in prompt.tag_to_source_record_id:
            assert tag in allowed_line

    def test_allowed_tags_block_is_positioned_after_all_data_sections(self):
        prompt = build_narrative_prompt(_full_snapshot())
        lines = prompt.text.splitlines()

        allowed_index = next(i for i, line in enumerate(lines) if line.startswith("[사용 가능한 태그]"))
        last_data_tag_index = max(
            i for i, line in enumerate(lines) if any(f"[{tag}]" in line for tag in ("E1", "D1", "L1", "P1", "A1"))
        )
        assert allowed_index > last_data_tag_index

    def test_evidence_tags_reminder_appears_after_the_allowed_tags_block(self):
        prompt = build_narrative_prompt(_full_snapshot())
        lines = prompt.text.splitlines()

        allowed_index = next(i for i, line in enumerate(lines) if line.startswith("[사용 가능한 태그]"))
        reminder_index = next(
            i for i, line in enumerate(lines) if "최소 1개 이상 포함하라" in line
        )
        assert reminder_index > allowed_index

    def test_missing_data_types_contribute_no_tags_to_the_allowed_list(self):
        # 진단·처방·알레르기가 전부 0건인 스냅샷 - D/P/A 태그가 전혀
        # 생성되지 않고, [사용 가능한 태그]에도 등장하지 않아야 한다.
        snapshot = _snapshot(diagnoses=[], prescriptions=[], allergies=[])
        prompt = build_narrative_prompt(snapshot)

        allowed_line = next(line for line in prompt.text.splitlines() if line.startswith("[사용 가능한 태그]"))
        assert "D1" not in allowed_line
        assert "P1" not in allowed_line
        assert "A1" not in allowed_line
        assert not any(tag.startswith(("D", "P", "A")) for tag in prompt.tag_to_source_record_id)

    def test_allowed_tags_order_is_deterministic_for_the_same_snapshot(self):
        snapshot = _full_snapshot()

        first = build_narrative_prompt(snapshot)
        second = build_narrative_prompt(snapshot)

        first_line = next(line for line in first.text.splitlines() if line.startswith("[사용 가능한 태그]"))
        second_line = next(line for line in second.text.splitlines() if line.startswith("[사용 가능한 태그]"))
        assert first_line == second_line

    # --- Task C1: 본문 태그 금지 지시 + 진료과/진료형태 한글 정규화 ------------

    def test_prompt_tells_the_model_to_never_write_tags_in_the_narrative_body(self):
        prompt = build_narrative_prompt(_full_snapshot())

        assert "narrative 본문에는" in prompt.text
        assert "[ ], ( ), { }" in prompt.text

    def test_prompt_tells_the_model_evidence_tags_go_only_in_the_evidence_tags_field(self):
        prompt = build_narrative_prompt(_full_snapshot())

        assert "evidence_tags는 JSON의 evidence_tags 필드에만" in prompt.text

    def test_the_tag_prohibition_rule_appears_only_once(self):
        # "같은 규칙을 여러 곳에 중복하지 마라" - [사용 가능한 태그] 근처
        # 한 곳에만 있어야 한다.
        prompt = build_narrative_prompt(_full_snapshot())
        assert prompt.text.count("narrative 본문에는") == 1

    def test_allowed_tags_block_is_still_present_alongside_the_new_rule(self):
        prompt = build_narrative_prompt(_full_snapshot())
        assert "[사용 가능한 태그]" in prompt.text

    def test_department_is_shown_as_the_standard_korean_label(self):
        prompt = build_narrative_prompt(_full_snapshot())

        assert "내분비내과" in prompt.text
        assert "ENDOCRINOLOGY" not in prompt.text

    def test_encounter_type_is_shown_as_the_standard_korean_label(self):
        prompt = build_narrative_prompt(_full_snapshot())

        assert "외래" in prompt.text
        assert "OUTPATIENT" not in prompt.text

    def test_unmapped_department_falls_back_to_the_raw_value_instead_of_guessing(self):
        snapshot = _snapshot(
            encounters=[
                {
                    "id": 1, "department": "SOME_FUTURE_DEPARTMENT", "encounter_type": "OUTPATIENT",
                    "start_time": "2026-03-10T09:00:00Z", "end_time": None,
                }
            ]
        )
        prompt = build_narrative_prompt(snapshot)
        assert "SOME_FUTURE_DEPARTMENT" in prompt.text


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
    '"evidence_tags": ["L1"], '
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
            response='{"narrative": "x", "evidence_tags": ["L1"], "mentioned_measurements": [], '
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


# ============================== 익명 evidence_tags 역매핑 ========================


class TestEvidenceTagResolution:
    def test_resolves_a_valid_tag_to_the_real_source_record_id(self):
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "evidence_tags": ["L1"], "mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())

        assert result.cited_record_ids == ["lab_result:1"]

    def test_rejects_a_tag_that_was_never_offered(self):
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "evidence_tags": ["Z9"], "mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_EVIDENCE_TAG_UNKNOWN"

    def test_rejects_an_empty_evidence_tags_list(self):
        # evidence_tags는 이제 min_length=1이라 빈 배열은 RealLLMProvider의
        # _resolve_evidence_tags에 도달하기 전에 LlmStructuredOutput
        # 파싱(Pydantic) 단계에서 먼저 거부된다 - 그래서 코드가
        # LLM_EVIDENCE_TAGS_EMPTY가 아니라 LLM_OUTPUT_INVALID_JSON이다.
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "evidence_tags": [], "mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_OUTPUT_INVALID_JSON"

    def test_rejects_a_response_missing_the_evidence_tags_key_entirely(self):
        # evidence_tags가 필수 필드로 바뀌었으므로, 키 자체가 없는
        # 응답(과거에는 기본값 빈 리스트로 조용히 통과했다)도 이제는
        # 거부된다.
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_OUTPUT_INVALID_JSON"

    def test_resolve_evidence_tags_helper_still_rejects_an_empty_list_directly(self):
        # RealLLMProvider._resolve_evidence_tags()의 빈 목록 거부는
        # Pydantic 스키마를 우회해 직접 이 함수를 호출하는 경로에서도
        # 안전해야 한다는 defense-in-depth를 그대로 유지한다 - 이 함수를
        # 직접 호출해 삭제/완화되지 않았음을 재확인한다.
        from app.services.narrative_providers.real_llm_provider import _resolve_evidence_tags

        with pytest.raises(NarrativeProviderError) as exc_info:
            _resolve_evidence_tags([], {"L1": "lab_result:1"})
        assert exc_info.value.code == "LLM_EVIDENCE_TAGS_EMPTY"

    def test_a_single_invalid_tag_rejects_the_whole_result_even_if_others_are_valid(self):
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "evidence_tags": ["L1", "Z9"], "mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_EVIDENCE_TAG_UNKNOWN"

    def test_deduplicates_repeated_tags_while_keeping_first_seen_order(self):
        client = _FakeLlmHttpClient(
            response='{"narrative": "x", "evidence_tags": ["L1", "E1", "L1"], '
            '"mentioned_measurements": []}'
        )
        provider = RealLLMProvider(client=client, model="test-model", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())

        assert result.cited_record_ids == ["lab_result:1", "encounter:1"]


# ============================== RealLLMProvider + OllamaHttpClient 통합 =========


class TestRealLLMProviderWithOllamaClient:
    """MockTransport로 실제 네트워크 없이 OllamaHttpClient를
    RealLLMProvider에 주입해, Task A의 evidence_tags 계약이 Task B의
    벤더 Adapter를 거쳐도 그대로 지켜지는지 확인한다."""

    def test_end_to_end_resolves_evidence_tags_through_the_ollama_client(self):
        def handler(request: httpx.Request) -> httpx.Response:
            content = json.dumps(
                {"narrative": "HbA1c가 확인됩니다.", "evidence_tags": ["L1"], "mentioned_measurements": []}
            )
            return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})

        client = OllamaHttpClient(base_url="http://ollama.invalid:11434", transport=httpx.MockTransport(handler))
        provider = RealLLMProvider(client=client, model="qwen3:8b", max_output_tokens=500, timeout_seconds=10)

        result = provider.generate(_snapshot())

        assert result.narrative == "HbA1c가 확인됩니다."
        assert result.cited_record_ids == ["lab_result:1"]
        assert result.provider == "LLM"
        assert result.model == "qwen3:8b"

    def test_llm_request_failure_through_ollama_client_never_falls_back_to_mock(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        client = OllamaHttpClient(base_url="http://ollama.invalid:11434", transport=httpx.MockTransport(handler))
        provider = RealLLMProvider(client=client, model="qwen3:8b", max_output_tokens=500, timeout_seconds=10)

        with pytest.raises(NarrativeProviderError) as exc_info:
            provider.generate(_snapshot())
        assert exc_info.value.code == "LLM_REQUEST_FAILED"


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

    # --- Task B: 벤더 분기 -------------------------------------------------

    def test_llm_without_a_vendor_is_rejected_and_does_not_guess_ollama(self):
        # llm_vendor를 명시적으로 빈 문자열로 준다 - 지정하지 않으면
        # pydantic-settings가 실제 backend/.env의 LLM_VENDOR 값을 그대로
        # 읽어와 이 테스트가 로컬 .env 상태에 좌우될 수 있다.
        settings = Settings(narrative_provider="llm", llm_model="qwen3:8b", llm_vendor="")
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_VENDOR_MISSING"

    def test_llm_with_an_unsupported_vendor_is_rejected(self):
        settings = Settings(
            narrative_provider="llm", llm_vendor="openai", llm_api_key="sk-fake", llm_model="gpt-4"
        )
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_VENDOR_UNSUPPORTED"

    def test_ollama_without_base_url_is_rejected(self):
        # llm_base_url을 명시적으로 빈 문자열로 준다 - 같은 이유로 실제
        # .env의 LLM_BASE_URL에 좌우되지 않게 한다.
        settings = Settings(
            narrative_provider="llm", llm_vendor="ollama", llm_model="qwen3:8b", llm_base_url=""
        )
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_BASE_URL_MISSING"

    def test_ollama_without_model_is_rejected(self):
        settings = Settings(
            narrative_provider="llm",
            llm_vendor="ollama",
            llm_base_url="http://localhost:11434",
            llm_model="",
        )
        with pytest.raises(NarrativeProviderError) as exc_info:
            get_narrative_provider(settings)
        assert exc_info.value.code == "LLM_MODEL_MISSING"

    def test_ollama_initializes_without_an_api_key(self):
        # 로컬 Ollama는 API 키가 없어도 정상적으로 조립되어야 한다 -
        # 이것이 이번 Task B 벤더 분기의 핵심 동작이다.
        settings = Settings(
            narrative_provider="llm",
            llm_vendor="ollama",
            llm_base_url="http://localhost:11434",
            llm_model="qwen3:8b",
            llm_api_key=None,
        )
        provider = get_narrative_provider(settings)
        assert isinstance(provider, RealLLMProvider)

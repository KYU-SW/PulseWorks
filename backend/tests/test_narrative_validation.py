from app.schemas.clinical_report import EmrSnapshot
from app.services.narrative_providers.base import MentionedMeasurement, NarrativeProviderResult
from app.services.narrative_validation import (
    MAX_NARRATIVE_LENGTH,
    validate_narrative_provider_result,
)


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
            },
            {
                "id": 2, "encounter_id": 1, "test_name": "Fasting Glucose", "value": 130, "unit": "mg/dL",
                "reference_low": 70.0, "reference_high": 100.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "HIGH", "rule_id": "LAB_REFERENCE_RANGE",
            },
        ],
        "lab_trends": [],
        "prescriptions": [],
        "allergies": [],
        "safety_alerts": [],
        "clinical_notes": [],
        "source_record_ids": ["encounter:1", "lab_result:1", "lab_result:2"],
    }
    base.update(overrides)
    return EmrSnapshot.model_validate(base)


def _llm_result(**overrides) -> NarrativeProviderResult:
    base = dict(
        narrative="HbA1c는 8.1%입니다.",
        cited_record_ids=["lab_result:1"],
        mentioned_measurements=[MentionedMeasurement("HbA1c", 8.1, "%")],
        provider="LLM",
        model="test-model",
        version="1",
    )
    base.update(overrides)
    return NarrativeProviderResult(**base)


def _mock_result(**overrides) -> NarrativeProviderResult:
    base = dict(
        narrative="내분비내과 외래 방문 기록이 있습니다.",
        cited_record_ids=["encounter:1", "lab_result:1", "lab_result:2"],
        mentioned_measurements=[],
        provider="DETERMINISTIC_MOCK",
        model="n/a",
        version="1",
    )
    base.update(overrides)
    return NarrativeProviderResult(**base)


class TestLlmResultValidation:
    def test_a_valid_result_passes(self):
        validation = validate_narrative_provider_result(_llm_result(), _snapshot())
        assert validation.ok is True
        assert validation.reason is None

    def test_cited_ids_that_are_a_subset_pass(self):
        result = _llm_result(cited_record_ids=["lab_result:1", "lab_result:2"])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_a_cited_id_not_in_the_snapshot_is_rejected(self):
        result = _llm_result(cited_record_ids=["lab_result:999"])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "cited_id_not_in_snapshot"

    def test_a_real_measurement_passes(self):
        result = _llm_result(mentioned_measurements=[MentionedMeasurement("Fasting Glucose", 130, "mg/dL")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_130_and_130_point_0_are_treated_as_the_same_value(self):
        result = _llm_result(mentioned_measurements=[MentionedMeasurement("Fasting Glucose", 130.0, "mg/dL")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_a_different_numeric_value_is_rejected(self):
        result = _llm_result(mentioned_measurements=[MentionedMeasurement("HbA1c", 9.9, "%")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "measurement_not_in_snapshot"

    def test_a_different_unit_is_rejected(self):
        result = _llm_result(mentioned_measurements=[MentionedMeasurement("HbA1c", 8.1, "mmol/mol")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "measurement_not_in_snapshot"

    def test_a_different_test_name_is_rejected(self):
        result = _llm_result(mentioned_measurements=[MentionedMeasurement("Troponin", 8.1, "%")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "measurement_not_in_snapshot"

    def test_a_banned_phrase_is_rejected(self):
        result = _llm_result(narrative="상태가 악화되었습니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "banned_phrase_detected"

    def test_an_empty_narrative_is_rejected(self):
        result = _llm_result(narrative="   ")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "empty_narrative"

    def test_a_narrative_longer_than_the_limit_is_rejected(self):
        result = _llm_result(narrative="가" * (MAX_NARRATIVE_LENGTH + 1))
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "narrative_too_long"

    def test_empty_cited_ids_and_empty_measurements_together_are_rejected(self):
        result = _llm_result(cited_record_ids=[], mentioned_measurements=[])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "no_evidence_provided"

    def test_cited_ids_alone_are_enough_evidence(self):
        result = _llm_result(cited_record_ids=["lab_result:1"], mentioned_measurements=[])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_measurements_alone_are_enough_evidence(self):
        result = _llm_result(cited_record_ids=[], mentioned_measurements=[MentionedMeasurement("HbA1c", 8.1, "%")])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_never_mutates_the_input_snapshot(self):
        snapshot = _snapshot()
        before = snapshot.model_dump(mode="json")

        validate_narrative_provider_result(_llm_result(), snapshot)

        assert snapshot.model_dump(mode="json") == before


class TestEvidenceTagLeakDetection:
    # --- 차단해야 하는 표현 -------------------------------------------------

    def test_rejects_square_bracket_tag(self):
        result = _llm_result(narrative="검사 결과가 있습니다 [E1].")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_parenthesis_tag(self):
        result = _llm_result(narrative="검사 결과가 있습니다 (D1).")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_curly_brace_tag(self):
        result = _llm_result(narrative="검사 결과가 있습니다 {L1}.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_square_bracket_tag_with_internal_spaces(self):
        result = _llm_result(narrative="처방 기록이 있습니다 [ P1 ].")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_parenthesis_tag_with_internal_spaces(self):
        result = _llm_result(narrative="알레르기 정보가 있습니다 ( A1 ).")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_geungeo_cue_word_with_tag(self):
        result = _llm_result(narrative="이 설명은 근거 E1을 바탕으로 합니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_tag_word_cue_with_tag(self):
        result = _llm_result(narrative="이 설명은 태그 D1을 바탕으로 합니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_source_cue_word_with_tag(self):
        result = _llm_result(narrative="이 설명은 출처 L1을 바탕으로 합니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_reference_cue_word_with_tag(self):
        result = _llm_result(narrative="이 설명은 참고 P1을 바탕으로 합니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    def test_rejects_english_evidence_cue_word_with_tag_case_insensitive(self):
        result = _llm_result(narrative="This is based on Evidence A1.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "evidence_tag_leaked_into_narrative"

    # --- 정상적으로 허용해야 하는 표현 ---------------------------------------

    def test_allows_a_normal_narrative_with_no_tag_shaped_text(self):
        result = _llm_result(narrative="내분비내과 외래 진료 기록을 정리한 설명문입니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_allows_l1_as_a_lumbar_spine_reference_without_delimiter(self):
        # 정형외과에서 L1은 제1요추를 가리키는 실제 의학 표현이다 -
        # 구분자나 인용 단서어 없이 홀로 등장하면 차단하지 않는다.
        result = _llm_result(narrative="L1 척추 부위에 관한 기록이 있습니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_allows_l1_written_after_a_korean_vertebra_description(self):
        result = _llm_result(narrative="제1요추 L1에 관한 기록이 있습니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_allows_e1_as_a_bare_word_without_delimiter_or_cue_word(self):
        result = _llm_result(narrative="E1 반응이 확인되었습니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_allows_a_generic_alphanumeric_combination(self):
        result = _llm_result(narrative="검사 항목 코드 A1B2와 관련된 기록입니다.")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True


class TestMockResultValidation:
    def test_the_mock_result_passes_with_its_own_looser_policy(self):
        validation = validate_narrative_provider_result(_mock_result(), _snapshot())
        assert validation.ok is True

    def test_mock_path_never_runs_the_evidence_tag_leak_check(self):
        # Task C1: 이 검사는 _validate_llm_result에만 있다 - Mock 결과가
        # 우연히 태그 모양 텍스트를 담고 있어도(정상적으로는 생기지
        # 않지만) Mock 전용 느슨한 정책 그대로 통과해야 한다.
        result = _mock_result(narrative="내분비내과 외래 방문 기록이 있습니다 [E1].")
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is True

    def test_mock_result_with_no_evidence_still_passes(self):
        # Mock 경로는 "근거가 모두 비어 있으면 거부" 규칙을 적용받지
        # 않는다 - 빈 스냅샷에서도 Task 16 기존 동작이 그대로 유지돼야
        # 한다.
        empty_snapshot = _snapshot(
            encounters=[], diagnoses=[], lab_results=[], lab_trends=[],
            prescriptions=[], allergies=[], safety_alerts=[], clinical_notes=[],
            source_record_ids=[],
        )
        result = _mock_result(cited_record_ids=[], mentioned_measurements=[])
        validation = validate_narrative_provider_result(result, empty_snapshot)
        assert validation.ok is True

    def test_mock_result_still_rejects_a_cited_id_not_in_snapshot(self):
        result = _mock_result(cited_record_ids=["lab_result:999"])
        validation = validate_narrative_provider_result(result, _snapshot())
        assert validation.ok is False
        assert validation.reason == "cited_id_not_in_snapshot"

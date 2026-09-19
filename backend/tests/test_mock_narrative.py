from app.schemas.clinical_report import EmrSnapshot
from app.services.mock_narrative import generate_mock_report_narrative

_BANNED_PHRASES = [
    "악화되었습니다",
    "호전되었습니다",
    "치료를 권고",
    "권고합니다",
    "처방을 추가",
    "처방을 변경",
    "처방을 중단",
    "재검사가 필요합니다",
    "재검사를 지시",
    "위험도가 확정",
    "예후는",
    "예상됩니다",
]


def _snapshot(**overrides) -> EmrSnapshot:
    base = {
        "patient": {"id": 1, "mrn": "SYN-0001", "name": "합성환자-내분비01", "birth_date": "1968-04-12"},
        "encounters": [
            {
                "id": 1, "department": "ENDOCRINOLOGY", "encounter_type": "OUTPATIENT",
                "start_time": "2026-03-10T09:00:00Z", "end_time": None,
            }
        ],
        "diagnoses": [
            {
                "id": 1, "encounter_id": 1, "code": "E11.9", "description": "2형 당뇨병 신규 진단 (합성 데이터)",
                "diagnosed_at": "2026-03-10T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
        "lab_results": [
            {
                "id": 1, "encounter_id": 1, "test_name": "HbA1c", "value": 7.2, "unit": "%",
                "reference_low": 4.0, "reference_high": 6.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "HIGH", "rule_id": "LAB_REFERENCE_RANGE",
            }
        ],
        "lab_trends": [],
        "prescriptions": [
            {
                "id": 1, "encounter_id": 1, "medication_name": "Metformin", "dosage": "500mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            }
        ],
        "allergies": [
            {
                "id": 1, "substance": "Penicillin", "reaction": "두드러기 (합성 데이터)", "severity": "MODERATE",
                "recorded_at": "2026-01-01T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
        "safety_alerts": [
            {
                "id": 1, "encounter_id": 1, "prescription_id": 5, "lab_result_id": None,
                "rule_id": "ALLERGY_MEDICATION_CONFLICT", "priority": "HIGH",
                "evidence": {"explanation": "테스트"}, "created_at": "2026-09-17T14:52:27Z",
            }
        ],
        "clinical_notes": [
            {
                "id": 1, "encounter_id": 1, "author_user_id": 1, "preview_text": "합성 진료기록 미리보기",
                "created_at": "2026-03-10T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
        "source_record_ids": [
            "encounter:1", "diagnosis:1", "lab_result:1", "prescription:1",
            "allergy:1", "safety_alert:1", "clinical_note:1",
        ],
    }
    base.update(overrides)
    return EmrSnapshot.model_validate(base)


# 동일 입력에 동일 설명문
def test_same_snapshot_always_returns_the_same_narrative():
    snapshot = _snapshot()
    first = generate_mock_report_narrative(snapshot)
    second = generate_mock_report_narrative(snapshot)
    assert first.summary_text == second.summary_text
    assert first.source_record_ids == second.source_record_ids


# 원본 snapshot 불변
def test_does_not_mutate_the_input_snapshot():
    snapshot = _snapshot()
    before = snapshot.model_dump(mode="json")
    generate_mock_report_narrative(snapshot)
    after = snapshot.model_dump(mode="json")
    assert before == after


# 근거 ID 보존
def test_source_record_ids_are_preserved_from_the_snapshot():
    snapshot = _snapshot()
    result = generate_mock_report_narrative(snapshot)
    assert result.source_record_ids == snapshot.source_record_ids


# provider/version 고정값
def test_provider_and_version_are_fixed():
    result = generate_mock_report_narrative(_snapshot())
    assert result.provider == "DETERMINISTIC_MOCK"
    assert result.version == "1"


# 기록에 있는 사실은 그대로 인용
def test_narrative_quotes_recorded_facts():
    result = generate_mock_report_narrative(_snapshot())
    assert "2형 당뇨병 신규 진단" in result.summary_text
    assert "HbA1c" in result.summary_text
    assert "7.2%" in result.summary_text
    assert "Metformin" in result.summary_text
    assert "Penicillin" in result.summary_text
    assert "ALLERGY_MEDICATION_CONFLICT" in result.summary_text
    assert "합성 진료기록 미리보기" in result.summary_text


# 고정 안내 문구 포함
def test_narrative_ends_with_the_fixed_disclaimer():
    result = generate_mock_report_narrative(_snapshot())
    assert (
        "이 설명은 합성 임상기록을 정해진 규칙으로 정리한 초안이며, "
        "의료진의 검토가 필요합니다." in result.summary_text
    )


# 기록에 없는 정보 생성 없음 & 금지된 치료·처방 권고 없음
def test_narrative_never_contains_banned_recommendation_phrases():
    result = generate_mock_report_narrative(_snapshot())
    for banned in _BANNED_PHRASES:
        assert banned not in result.summary_text


# 빈 스냅샷(모든 목록이 비어 있음)도 예외 없이 처리
def test_empty_snapshot_returns_a_disclaimer_only_narrative():
    empty = _snapshot(
        encounters=[], diagnoses=[], lab_results=[], lab_trends=[], prescriptions=[],
        allergies=[], safety_alerts=[], clinical_notes=[],
        source_record_ids=[],
    )
    result = generate_mock_report_narrative(empty)
    assert "이 범위에 표시할 기록이 없습니다." in result.summary_text
    assert result.summary_text.strip().endswith("의료진의 검토가 필요합니다.")


# 서로 다른 스냅샷은 서로 다른 설명문
def test_different_snapshots_produce_different_narratives():
    first = generate_mock_report_narrative(_snapshot())
    second = generate_mock_report_narrative(
        _snapshot(diagnoses=[])
    )
    assert first.summary_text != second.summary_text

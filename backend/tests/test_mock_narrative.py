from app.schemas.clinical_report import EmrSnapshot
from app.services.mock_narrative import generate_mock_report_narrative

# app/services/narrative_validation.py의 BANNED_NARRATIVE_PHRASES와 같은
# 목록 + Task 20C 후속 보완에서 명시적으로 금지된 추가 표현.
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
    "이 약은 위험합니다",
    "복용하지 마세요",
    "처방이 잘못되었습니다",
    "약을 중단하세요",
    "알레르기 반응이 발생합니다",
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


def _empty_snapshot(**overrides) -> EmrSnapshot:
    defaults = {
        "encounters": [], "diagnoses": [], "lab_results": [], "lab_trends": [], "prescriptions": [],
        "allergies": [], "safety_alerts": [], "clinical_notes": [], "source_record_ids": [],
    }
    defaults.update(overrides)
    return _snapshot(**defaults)


# --- 1. 결정성/근거 보존 ------------------------------------------------

def test_same_snapshot_always_returns_the_same_narrative():
    snapshot = _snapshot()
    first = generate_mock_report_narrative(snapshot)
    second = generate_mock_report_narrative(snapshot)
    assert first.summary_text == second.summary_text
    assert first.source_record_ids == second.source_record_ids


def test_does_not_mutate_the_input_snapshot():
    snapshot = _snapshot()
    before = snapshot.model_dump(mode="json")
    generate_mock_report_narrative(snapshot)
    after = snapshot.model_dump(mode="json")
    assert before == after


def test_source_record_ids_are_preserved_from_the_snapshot():
    snapshot = _snapshot()
    result = generate_mock_report_narrative(snapshot)
    assert result.source_record_ids == snapshot.source_record_ids


def test_provider_and_version_are_fixed():
    result = generate_mock_report_narrative(_snapshot())
    assert result.provider == "DETERMINISTIC_MOCK"
    assert result.version == "1"


def test_different_snapshots_produce_different_narratives():
    first = generate_mock_report_narrative(_snapshot())
    second = generate_mock_report_narrative(_snapshot(diagnoses=[]))
    assert first.summary_text != second.summary_text


# --- 2~4. narrative에서 제거해야 하는 내부·개발용 표현 -------------------

def test_narrative_never_contains_encounter_internal_id_marker():
    result = generate_mock_report_narrative(_snapshot())
    assert "Encounter #" not in result.summary_text
    assert "encounter:1" not in result.summary_text


def test_narrative_never_contains_the_diagnosis_code():
    result = generate_mock_report_narrative(_snapshot())
    assert "E11.9" not in result.summary_text


def test_narrative_never_contains_the_lab_rule_id():
    result = generate_mock_report_narrative(_snapshot())
    assert "LAB_REFERENCE_RANGE" not in result.summary_text
    assert "lab_result:1" not in result.summary_text


def test_narrative_never_contains_the_safety_alert_rule_id_or_priority():
    result = generate_mock_report_narrative(_snapshot())
    assert "ALLERGY_MEDICATION_CONFLICT" not in result.summary_text
    assert "우선순위" not in result.summary_text
    assert "priority" not in result.summary_text
    assert "safety_alert:1" not in result.summary_text


def test_narrative_never_contains_the_dev_test_medication_name():
    snapshot = _snapshot(
        prescriptions=[
            {
                "id": 1, "encounter_id": 1, "medication_name": "Task10VerifyNonConflictMedX",
                "dosage": "1정", "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            }
        ]
    )
    result = generate_mock_report_narrative(snapshot)
    assert "Task10VerifyNonConflictMedX" not in result.summary_text
    # 다른 실제 약물로 대체 추정하지도 않으므로, 처방 관련 문장 자체가 없다.
    assert "처방 기록이" not in result.summary_text


def test_dev_test_medication_is_excluded_even_when_mixed_with_a_real_prescription():
    snapshot = _snapshot(
        prescriptions=[
            {
                "id": 1, "encounter_id": 1, "medication_name": "Metformin", "dosage": "500mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            },
            {
                "id": 2, "encounter_id": 1, "medication_name": "Task10VerifyNonConflictMedX",
                "dosage": "1정", "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            },
        ]
    )
    result = generate_mock_report_narrative(snapshot)
    assert "Task10VerifyNonConflictMedX" not in result.summary_text
    assert "메트포르민" in result.summary_text


def test_narrative_never_contains_clinical_note_preview_text():
    result = generate_mock_report_narrative(_snapshot())
    assert "합성 진료기록 미리보기" not in result.summary_text
    assert "진료기록 미리보기" not in result.summary_text
    assert "clinical_note:1" not in result.summary_text


def test_narrative_never_contains_the_patient_mrn():
    result = generate_mock_report_narrative(_snapshot())
    assert "SYN-0001" not in result.summary_text


def test_narrative_never_contains_a_raw_source_record_id():
    result = generate_mock_report_narrative(_snapshot())
    for source_id in _snapshot().source_record_ids:
        assert source_id not in result.summary_text


# --- 5~9. 실제 기록 기반 중립 요약이 정확히 포함되는지 -------------------

def test_encounter_paragraph_uses_actual_date_department_and_type():
    result = generate_mock_report_narrative(_snapshot())
    assert "2026년 3월 10일" in result.summary_text
    assert "내분비내과" in result.summary_text
    assert "외래" in result.summary_text


def test_diagnosis_paragraph_uses_the_description_only():
    result = generate_mock_report_narrative(_snapshot())
    assert "2형 당뇨병 신규 진단 (합성 데이터)" in result.summary_text
    assert "에 관한 진단 기록이 있" in result.summary_text


def test_lab_paragraph_summarizes_high_status_neutrally():
    result = generate_mock_report_narrative(_snapshot())
    assert "HbA1c" in result.summary_text
    assert "저장된 참고범위보다 높은 것으로 기록되어 있습니다" in result.summary_text
    # 정확한 수치·참고범위는 narrative에서 반복하지 않는다.
    assert "7.2" not in result.summary_text
    assert "4.0" not in result.summary_text
    assert "6.0" not in result.summary_text


def test_lab_paragraph_summarizes_low_status_neutrally():
    snapshot = _snapshot(
        lab_results=[
            {
                "id": 1, "encounter_id": 1, "test_name": "Fasting Glucose", "value": 55.0, "unit": "mg/dL",
                "reference_low": 70.0, "reference_high": 100.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "LOW", "rule_id": "LAB_REFERENCE_RANGE",
            }
        ]
    )
    result = generate_mock_report_narrative(snapshot)
    assert "Fasting Glucose" in result.summary_text
    assert "저장된 참고범위보다 낮은 것으로 기록되어 있습니다" in result.summary_text


def test_lab_paragraph_joins_two_high_status_test_names_with_correct_particle():
    snapshot = _snapshot(
        lab_results=[
            {
                "id": 1, "encounter_id": 1, "test_name": "HbA1c", "value": 7.2, "unit": "%",
                "reference_low": 4.0, "reference_high": 6.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "HIGH", "rule_id": "LAB_REFERENCE_RANGE",
            },
            {
                "id": 2, "encounter_id": 1, "test_name": "Fasting Glucose", "value": 150.0, "unit": "mg/dL",
                "reference_low": 70.0, "reference_high": 100.0, "measured_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED", "status": "HIGH", "rule_id": "LAB_REFERENCE_RANGE",
            },
        ]
    )
    result = generate_mock_report_narrative(snapshot)
    assert "HbA1c와 Fasting Glucose 검사결과" in result.summary_text


def test_prescription_paragraph_translates_known_medication_names():
    snapshot = _snapshot(
        prescriptions=[
            {
                "id": 1, "encounter_id": 1, "medication_name": "Metformin", "dosage": "500mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            },
            {
                "id": 2, "encounter_id": 1, "medication_name": "Penicillin V", "dosage": "250mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            },
        ]
    )
    result = generate_mock_report_narrative(snapshot)
    assert "메트포르민과 페니실린 V 처방 기록이" in result.summary_text
    assert "Metformin" not in result.summary_text
    # 복용법/횟수/투여 경로/처방 목적은 narrative에서 만들지 않는다.
    assert "500mg" not in result.summary_text
    assert "250mg" not in result.summary_text


def test_prescription_paragraph_keeps_unmapped_medication_name_as_is():
    snapshot = _snapshot(
        prescriptions=[
            {
                "id": 1, "encounter_id": 1, "medication_name": "Ibuprofen", "dosage": "200mg",
                "prescribed_by_user_id": 1, "prescribed_at": "2026-03-10T09:00:00Z",
                "source_type": "INSTITUTION_GENERATED",
            }
        ],
        allergies=[],
    )
    result = generate_mock_report_narrative(snapshot)
    assert "Ibuprofen 처방 기록이 있습니다." in result.summary_text


def test_allergy_paragraph_uses_substance_only():
    result = generate_mock_report_narrative(_snapshot())
    assert "Penicillin에 대한 알레르기 정보가 등록되어 있습니다" in result.summary_text
    # reaction/severity 상세는 구조화된 알레르기 섹션에 맡긴다.
    assert "두드러기" not in result.summary_text
    assert "MODERATE" not in result.summary_text


# --- 10. SafetyAlert / ClinicalNote 제외 --------------------------------

def test_safety_alert_is_never_used_even_though_it_exists_in_the_snapshot():
    result = generate_mock_report_narrative(_snapshot())
    assert "안전 알림" not in result.summary_text


def test_clinical_note_is_never_used_even_though_it_exists_in_the_snapshot():
    result = generate_mock_report_narrative(_snapshot())
    assert "미리보기" not in result.summary_text


# --- 11. 최종 안내 문구 --------------------------------------------------

def test_old_draft_review_disclaimer_is_removed():
    result = generate_mock_report_narrative(_snapshot())
    assert "초안" not in result.summary_text
    assert "검토가 필요합니다" not in result.summary_text


def test_narrative_ends_with_a_guidance_sentence_that_does_not_conflict_with_approval():
    result = generate_mock_report_narrative(_snapshot())
    assert (
        "정확한 검사결과, 참고범위, 처방 및 알레르기 정보는 "
        "아래의 각 항목에서 확인할 수 있습니다."
    ) in result.summary_text
    assert result.summary_text.strip().endswith(
        "검사결과와 처방의 의미는 담당 의료진 또는 약사에게 확인하세요."
    )


# --- 12. 금지된 치료·처방 권고 표현 미생성 -------------------------------

def test_narrative_never_contains_banned_recommendation_phrases():
    result = generate_mock_report_narrative(_snapshot())
    for banned in _BANNED_PHRASES:
        assert banned not in result.summary_text


# --- 13. 각 항목이 없을 때의 처리 ----------------------------------------

def test_missing_diagnosis_generates_no_diagnosis_sentence():
    result = generate_mock_report_narrative(_snapshot(diagnoses=[]))
    assert "에 관한 진단 기록이" not in result.summary_text


def test_missing_lab_results_generates_no_lab_sentence():
    result = generate_mock_report_narrative(_snapshot(lab_results=[]))
    assert "검사결과가 저장된 참고범위" not in result.summary_text


def test_missing_prescriptions_generates_no_prescription_sentence():
    result = generate_mock_report_narrative(_snapshot(prescriptions=[]))
    assert "처방 기록이" not in result.summary_text


def test_missing_allergies_generates_no_allergy_sentence():
    result = generate_mock_report_narrative(_snapshot(allergies=[]))
    assert "알레르기 정보가 등록되어 있습니다" not in result.summary_text


def test_empty_snapshot_returns_a_no_records_and_safety_notice_only_narrative():
    result = generate_mock_report_narrative(_empty_snapshot())
    assert "이 범위에서 확인할 수 있는 기록이 없습니다." in result.summary_text
    assert result.summary_text.strip().endswith(
        "검사결과와 처방의 의미는 담당 의료진 또는 약사에게 확인하세요."
    )
    # 원본에 없는 진단·검사·처방·알레르기 문장이 생기지 않는다.
    assert "에 관한 진단 기록이" not in result.summary_text
    assert "처방 기록이" not in result.summary_text
    assert "알레르기 정보가 등록되어 있습니다" not in result.summary_text


def test_snapshot_with_only_safety_alert_and_clinical_note_still_falls_back_to_no_records():
    # 진단/검사/처방/알레르기가 전부 없고 SafetyAlert/ClinicalNote만 있어도,
    # 그 둘은 narrative에서 절대 쓰이지 않으므로 "기록 없음"으로 처리된다.
    snapshot = _empty_snapshot(
        safety_alerts=[
            {
                "id": 1, "encounter_id": 1, "prescription_id": None, "lab_result_id": None,
                "rule_id": "ALLERGY_MEDICATION_CONFLICT", "priority": "HIGH",
                "evidence": {}, "created_at": "2026-09-17T14:52:27Z",
            }
        ],
        clinical_notes=[
            {
                "id": 1, "encounter_id": 1, "author_user_id": 1, "preview_text": "합성 진료기록 미리보기",
                "created_at": "2026-03-10T09:00:00Z", "source_type": "INSTITUTION_GENERATED",
            }
        ],
    )
    result = generate_mock_report_narrative(snapshot)
    assert "이 범위에서 확인할 수 있는 기록이 없습니다." in result.summary_text
    assert "ALLERGY_MEDICATION_CONFLICT" not in result.summary_text
    assert "미리보기" not in result.summary_text

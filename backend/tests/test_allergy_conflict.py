from app.models import LabResult  # noqa: F401  (모듈 레벨 테이블 등록, Task 9와 동일 이유)
from app.services.safety_rules import AllergyEvidence, check_allergy_conflict

_BANNED_PHRASES = [
    "진단",
    "치료",
    "약물을 중단",
    "약물을 변경",
    "대체 약물",
    "대체약물",
    "상호작용",
    "교차반응",
    "적절",
]


# 1. Allergy 목록이 비어 있으면 충돌 없음
def test_empty_allergy_list_has_no_conflict():
    result = check_allergy_conflict([], "Penicillin V")
    assert result.has_conflict is False


# 2. medication_name이 빈 문자열이면 충돌 없음
def test_empty_medication_name_has_no_conflict():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], ""
    )
    assert result.has_conflict is False


# 3. medication_name이 공백만 있으면 충돌 없음
def test_blank_medication_name_has_no_conflict():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "   "
    )
    assert result.has_conflict is False


# 4. 정확히 같은 이름이면 충돌
def test_exact_same_name_conflicts():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin"
    )
    assert result.has_conflict is True


# 5. 대소문자가 달라도 충돌
def test_case_insensitive_match_conflicts():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="penicillin")], "PENICILLIN V"
    )
    assert result.has_conflict is True


# 6. 앞뒤 공백이 있어도 충돌
def test_leading_trailing_whitespace_still_conflicts():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="  Penicillin  ")], "  Penicillin V  "
    )
    assert result.has_conflict is True


# 7. 연속된 공백을 정규화한 뒤 충돌
def test_repeated_internal_whitespace_is_normalized_then_conflicts():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin    V"
    )
    assert result.has_conflict is True


# 8. Penicillin Allergy와 Penicillin V 처방은 충돌
def test_penicillin_allergy_conflicts_with_penicillin_v():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result.has_conflict is True


# 9. Penicillin Allergy와 Penicillin-V 처방은 충돌
def test_penicillin_allergy_conflicts_with_hyphenated_penicillin_v():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin-V"
    )
    assert result.has_conflict is True


# 10. Pen Allergy와 Penicillin V는 충돌하지 않음
def test_pen_allergy_does_not_conflict_with_penicillin_v():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Pen")], "Penicillin V"
    )
    assert result.has_conflict is False


# 11. Cillin Allergy와 Penicillin V는 충돌하지 않음
def test_cillin_allergy_does_not_conflict_with_penicillin_v():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Cillin")], "Penicillin V"
    )
    assert result.has_conflict is False


# 12. Ace Allergy와 Acetaminophen은 충돌하지 않음
def test_ace_allergy_does_not_conflict_with_acetaminophen():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Ace")], "Acetaminophen"
    )
    assert result.has_conflict is False


# 13. Penicillin Allergy와 Amoxicillin은 충돌하지 않음 (계열 추론 없음)
def test_penicillin_allergy_does_not_conflict_with_amoxicillin():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Amoxicillin"
    )
    assert result.has_conflict is False


# 14. 무관한 Allergy와 Medication은 충돌하지 않음
def test_unrelated_allergy_and_medication_do_not_conflict():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Latex")], "Metformin"
    )
    assert result.has_conflict is False


# 15. 충돌 시 rule_id
def test_rule_id_is_allergy_medication_conflict():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result.rule_id == "ALLERGY_MEDICATION_CONFLICT"


# 16. 충돌 시 priority가 HIGH
def test_conflict_priority_is_high():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result.priority == "HIGH"


# 17. 비충돌 시 priority가 None
def test_no_conflict_priority_is_none():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Amoxicillin"
    )
    assert result.priority is None


# 18. 충돌 시 matched_allergy_id와 matched_allergy_name 보존
def test_conflict_preserves_matched_allergy_id_and_name():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=42, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result.matched_allergy_id == 42
    assert result.matched_allergy_name == "Penicillin"


# 19. 비충돌 시 matched_allergy 정보가 None
def test_no_conflict_matched_allergy_info_is_none():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Amoxicillin"
    )
    assert result.matched_allergy_id is None
    assert result.matched_allergy_name is None


# 20. medication_name이 결과에 보존
def test_medication_name_is_preserved_in_result():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result.medication_name == "Penicillin V"


# 21. 입력 Allergy 순서가 달라도 allergy_id가 가장 작은 일치 항목 선택
def test_smallest_allergy_id_is_selected_regardless_of_input_order():
    allergies_a = [
        AllergyEvidence(allergy_id=5, allergy_name="Penicillin"),
        AllergyEvidence(allergy_id=2, allergy_name="Penicillin"),
    ]
    allergies_b = list(reversed(allergies_a))

    result_a = check_allergy_conflict(allergies_a, "Penicillin V")
    result_b = check_allergy_conflict(allergies_b, "Penicillin V")

    assert result_a.matched_allergy_id == 2
    assert result_b.matched_allergy_id == 2


# 22. 같은 입력에는 항상 같은 결과 반환
def test_same_input_always_returns_same_result():
    allergies = [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")]
    first = check_allergy_conflict(allergies, "Penicillin V")
    second = check_allergy_conflict(allergies, "Penicillin V")
    assert first == second


# 23. DB 세션 없이 실행 가능 (인자 없음 자체로 증명됨)
def test_runs_without_a_db_session():
    result = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    assert result is not None


# 24. DB 레코드를 변경하지 않음
def test_never_touches_the_database(db_session):
    before = db_session.query(LabResult).count()
    check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    after = db_session.query(LabResult).count()
    assert before == after == 0


# 25. explanation에 진단·치료·약물 중단·대체 추천 문구 없음
def test_explanations_never_contain_banned_phrases():
    conflict = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Penicillin V"
    )
    no_conflict = check_allergy_conflict(
        [AllergyEvidence(allergy_id=1, allergy_name="Penicillin")], "Amoxicillin"
    )
    for explanation in (conflict.explanation, no_conflict.explanation):
        for banned in _BANNED_PHRASES:
            assert banned not in explanation

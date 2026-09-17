import math

# 모델을 모듈 레벨에서 임포트해야 한다 — db_session 픽스처의
# Base.metadata.create_all()이 실행되기 전에 SQLAlchemy가 이 테이블들을
# 등록하고 있어야, 이 테스트 파일만 단독으로 실행해도 테이블이 만들어진다.
from app.models import LabResult
from app.services.safety_rules import LabAbnormalStatus, evaluate_lab_abnormal

_BANNED_PHRASES = [
    "의심",
    "진단",
    "위험",
    "약물을 조정",
    "약물을 추가",
    "약물을 변경",
    "약물을 중단",
    "치료",
    "처방",
    "당뇨병",
]


# 1. 하한 미만 -> LOW
def test_value_below_reference_low_is_low():
    result = evaluate_lab_abnormal(value=69, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.LOW


# 2. 하한과 동일 -> NORMAL (경계값은 정상범위에 포함)
def test_value_equal_to_reference_low_is_normal():
    result = evaluate_lab_abnormal(value=70, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.NORMAL


# 3. 범위 중간 -> NORMAL
def test_value_in_middle_of_range_is_normal():
    result = evaluate_lab_abnormal(value=85, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.NORMAL


# 4. 상한과 동일 -> NORMAL
def test_value_equal_to_reference_high_is_normal():
    result = evaluate_lab_abnormal(value=100, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.NORMAL


# 5. 상한 초과 -> HIGH
def test_value_above_reference_high_is_high():
    result = evaluate_lab_abnormal(value=101, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.HIGH


# 6, 7, 8, 9. UNKNOWN 기준
def test_value_none_is_unknown():
    result = evaluate_lab_abnormal(value=None, reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.UNKNOWN


def test_reference_low_none_is_unknown():
    result = evaluate_lab_abnormal(value=85, reference_low=None, reference_high=100)
    assert result.status == LabAbnormalStatus.UNKNOWN


def test_reference_high_none_is_unknown():
    result = evaluate_lab_abnormal(value=85, reference_low=70, reference_high=None)
    assert result.status == LabAbnormalStatus.UNKNOWN


def test_reference_low_greater_than_high_is_unknown():
    result = evaluate_lab_abnormal(value=85, reference_low=100, reference_high=70)
    assert result.status == LabAbnormalStatus.UNKNOWN


# 10. 단위 보존
def test_unit_is_preserved_in_result():
    result = evaluate_lab_abnormal(value=8.1, reference_low=4.0, reference_high=6.0, unit="%")
    assert result.unit == "%"
    assert result.value == 8.1
    assert result.reference_low == 4.0
    assert result.reference_high == 6.0


def test_unit_defaults_to_none_when_not_given():
    result = evaluate_lab_abnormal(value=5.0, reference_low=4.0, reference_high=6.0)
    assert result.unit is None


# 11. rule_id
def test_rule_id_is_lab_reference_range():
    result = evaluate_lab_abnormal(value=5.0, reference_low=4.0, reference_high=6.0)
    assert result.rule_id == "LAB_REFERENCE_RANGE"


# 12. 각 상태에 설명문 존재 (지정된 문구와 정확히 일치)
def test_explanation_text_matches_each_status():
    low = evaluate_lab_abnormal(value=1, reference_low=70, reference_high=100)
    normal = evaluate_lab_abnormal(value=85, reference_low=70, reference_high=100)
    high = evaluate_lab_abnormal(value=200, reference_low=70, reference_high=100)
    unknown = evaluate_lab_abnormal(value=None, reference_low=70, reference_high=100)

    assert low.explanation == "검사값이 등록된 데모 참고범위 하한보다 낮습니다."
    assert normal.explanation == "검사값이 등록된 데모 참고범위 안에 있습니다."
    assert high.explanation == "검사값이 등록된 데모 참고범위 상한보다 높습니다."
    assert unknown.explanation == "참고범위 판정에 필요한 정보가 부족하거나 유효하지 않습니다."


# 13. 진단·처방성 문구 없음
def test_explanations_never_contain_diagnostic_or_treatment_language():
    all_explanations = [
        evaluate_lab_abnormal(value=1, reference_low=70, reference_high=100).explanation,
        evaluate_lab_abnormal(value=85, reference_low=70, reference_high=100).explanation,
        evaluate_lab_abnormal(value=200, reference_low=70, reference_high=100).explanation,
        evaluate_lab_abnormal(value=None, reference_low=70, reference_high=100).explanation,
    ]
    for explanation in all_explanations:
        for banned in _BANNED_PHRASES:
            assert banned not in explanation


# 14. 동일 입력의 결과가 동일 (순수 함수)
def test_same_input_always_returns_same_result():
    first = evaluate_lab_abnormal(value=8.1, reference_low=4.0, reference_high=6.0, unit="%")
    second = evaluate_lab_abnormal(value=8.1, reference_low=4.0, reference_high=6.0, unit="%")
    assert first == second


# 15 & 16. DB 세션 없이 실행 가능하고 DB 레코드를 변경하지 않음
def test_runs_without_a_db_session_and_never_touches_the_database(db_session):
    before = db_session.query(LabResult).count()
    evaluate_lab_abnormal(value=8.1, reference_low=4.0, reference_high=6.0)  # db_session 인자 없음
    after = db_session.query(LabResult).count()

    assert before == after == 0


# 17. NaN 또는 무한대 입력이면 UNKNOWN
def test_nan_value_is_unknown():
    result = evaluate_lab_abnormal(value=float("nan"), reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.UNKNOWN


def test_infinite_value_is_unknown():
    result = evaluate_lab_abnormal(value=float("inf"), reference_low=70, reference_high=100)
    assert result.status == LabAbnormalStatus.UNKNOWN


def test_infinite_reference_bound_is_unknown():
    result = evaluate_lab_abnormal(value=85, reference_low=70, reference_high=float("inf"))
    assert result.status == LabAbnormalStatus.UNKNOWN


# 18. 기존 is_abnormal(boolean)과 LOW/HIGH/NORMAL 의미 일치
def test_low_and_high_map_to_true_normal_maps_to_false_like_the_old_boolean():
    cases = [
        (69, 70, 100, True),  # LOW
        (70, 70, 100, False),  # NORMAL (경계)
        (85, 70, 100, False),  # NORMAL
        (100, 70, 100, False),  # NORMAL (경계)
        (101, 70, 100, True),  # HIGH
    ]
    for value, low, high, expected_old_style_bool in cases:
        result = evaluate_lab_abnormal(value=value, reference_low=low, reference_high=high)
        old_style_bool = value < low or value > high
        assert old_style_bool == expected_old_style_bool
        new_style_bool = result.status in (LabAbnormalStatus.LOW, LabAbnormalStatus.HIGH)
        assert new_style_bool == old_style_bool

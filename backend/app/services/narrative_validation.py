"""NarrativeProvider 결과를 저장하기 전 반드시 통과해야 하는 검증.

순수 함수다 - DB/HTTP를 모르고, 원본 EmrSnapshot을 수정하지 않는다.
검증 실패는 예외를 던지지 않고 결과 객체로만 알린다 - 호출자(라우터)가
그 결과를 보고 감사 로그를 남기지 않고 DB 쓰기를 건너뛸 수 있게
하기 위해서다.

여기 있는 금지 문구 목록은 tests/test_mock_narrative.py가 결정적
Mock에 대해 이미 검증해 온 것과 같은 목록을 런타임 상수로 승격한
것이다 - Mock은 고정 템플릿이라 애초에 이 문구들을 만들 수 없었지만,
LLM은 자유 서술형이라 이 검사가 실제로 의미를 가진다.

중요한 한계: 이 문구 목록은 완전한 의미 검증이 아니라 보조 장치다.
같은 뜻의 새로운 표현(예: "약을 그만 드셔야 합니다")은 이 목록으로
잡아내지 못할 수 있다. 최종 안전장치는 여전히 담당 의사의 검토·승인
절차(Task 17)이며, 이 검증은 그 절차를 대체하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.schemas.clinical_report import EmrSnapshot
from app.services.narrative_providers.base import MentionedMeasurement, NarrativeProviderResult

MAX_NARRATIVE_LENGTH = 4000  # LlmStructuredOutput의 max_length와 동일

BANNED_NARRATIVE_PHRASES: tuple[str, ...] = (
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
)


@dataclass(frozen=True)
class NarrativeValidationResult:
    ok: bool
    reason: str | None  # ok=True면 항상 None


def _to_decimal(value: float) -> Decimal | None:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _cited_ids_are_subset(result: NarrativeProviderResult, snapshot: EmrSnapshot) -> bool:
    return set(result.cited_record_ids).issubset(set(snapshot.source_record_ids))


def _measurement_exists_in_snapshot(measurement: MentionedMeasurement, snapshot: EmrSnapshot) -> bool:
    target_name = measurement.test_name.strip()
    target_unit = measurement.unit.strip()
    target_value = _to_decimal(measurement.value)
    if target_value is None:
        return False

    for lab in snapshot.lab_results:
        if lab.test_name.strip() != target_name:
            continue
        if lab.unit.strip() != target_unit:
            continue
        lab_value = _to_decimal(lab.value)
        if lab_value is not None and lab_value == target_value:
            return True
    return False


def _contains_banned_phrase(narrative: str) -> bool:
    return any(phrase in narrative for phrase in BANNED_NARRATIVE_PHRASES)


def validate_narrative_provider_result(
    result: NarrativeProviderResult, snapshot: EmrSnapshot
) -> NarrativeValidationResult:
    if result.provider == "DETERMINISTIC_MOCK":
        return _validate_mock_result(result, snapshot)
    return _validate_llm_result(result, snapshot)


def _validate_mock_result(
    result: NarrativeProviderResult, snapshot: EmrSnapshot
) -> NarrativeValidationResult:
    # 결정적 Mock은 기존 동작 호환을 위해 더 느슨한 정책으로 검증한다:
    # cited_record_ids가 항상 snapshot.source_record_ids와 완전히 같고
    # mentioned_measurements를 아예 채우지 않는 것이 정상 동작이라,
    # "근거가 모두 비어 있으면 거부" 규칙을 적용하면 안 된다.
    if not result.narrative.strip():
        return NarrativeValidationResult(False, "empty_narrative")
    if not _cited_ids_are_subset(result, snapshot):
        return NarrativeValidationResult(False, "cited_id_not_in_snapshot")
    return NarrativeValidationResult(True, None)


def _validate_llm_result(
    result: NarrativeProviderResult, snapshot: EmrSnapshot
) -> NarrativeValidationResult:
    if not result.narrative.strip():
        return NarrativeValidationResult(False, "empty_narrative")
    if len(result.narrative) > MAX_NARRATIVE_LENGTH:
        return NarrativeValidationResult(False, "narrative_too_long")
    if not result.cited_record_ids and not result.mentioned_measurements:
        return NarrativeValidationResult(False, "no_evidence_provided")
    if not _cited_ids_are_subset(result, snapshot):
        return NarrativeValidationResult(False, "cited_id_not_in_snapshot")
    if any(not _measurement_exists_in_snapshot(m, snapshot) for m in result.mentioned_measurements):
        return NarrativeValidationResult(False, "measurement_not_in_snapshot")
    if _contains_banned_phrase(result.narrative):
        return NarrativeValidationResult(False, "banned_phrase_detected")
    return NarrativeValidationResult(True, None)

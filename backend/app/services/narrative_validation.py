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

Task C1(2026-09-30 실제 Ollama 수동 검증에서 narrative 본문에 "(E1)",
"(D1)" 노출 발견) 추가: LLM 결과에 한해 evidence tag가 narrative 본문에
노출됐는지도 검사한다 - "[E1]"/"(D1)"/"{L1}"처럼 구분자로 감싼 형태와
"근거 E1"/"출처 D1"처럼 인용 단서어와 함께 나온 형태만 차단한다.
구분자·단서어 없이 홀로 등장하는 "L1"(정형외과에서 제1요추를 가리킬
수 있는 실제 의학 표현) 같은 토큰은 오탐을 피하기 위해 의도적으로
차단하지 않는다 - 이 요청에서 실제로 유효한 태그 집합을 알아야 할
필요가 없어 narrative_validation.py가 prompt.py에 의존하지 않는다.
Mock은 태그 개념을 전혀 모르므로(별도 검증 함수) 이 검사와 무관하다.

Task F4-B(VitalSign Evidence Tag 연동) 추가: 문자 클래스에 V를 더해
[V1]/(V1)/{V1}/"근거 V1" 같은 명확한 태그 표현도 같은 방식으로
차단한다. "V1"은 L1보다도 오탐 위험이 더 크다 - ECG 흉부 리드(V1~V6),
삼차신경 제1분지(V1), 소프트웨어 버전 표기("v1")와 실제로 겹치는 실제
표현이라, 구분자·단서어 없이 홀로 등장하는 "V1"도 L1과 똑같이 의도적으로
차단하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.schemas.clinical_report import EmrSnapshot
from app.services.narrative_providers.base import (
    MentionedMeasurement,
    MentionedVitalSign,
    NarrativeProviderResult,
)

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

# 구분자로 감싼 형태([E1], (D1), {L1}, [ P1 ], ( A1 ), (V1) - 내부 공백
# 허용)와 인용 단서어 + 태그 형태(근거 E1, 태그 D1, 출처 L1, 참고 P1,
# Evidence A1, 근거 V1) 만 차단한다. "L1 척추"/"제1요추 L1"/"E1 반응"/
# "V1 리드"처럼 구분자·단서어 없이 홀로 등장하는 토큰은 정형외과의 실제
# 척추 레벨 표기(L1~L5 등)나 ECG 흉부 리드(V1~V6) 표기와 구분할 수 없어
# 의도적으로 차단 대상에서 제외한다.
_EVIDENCE_TAG_LEAK_PATTERN = re.compile(
    r"[\[({]\s*[EDLPAV]\d+\s*[\])}]|(?:근거|태그|출처|참고|[Ee]vidence)\s*[EDLPAV]\d+"
)


def _contains_evidence_tag_leak(narrative: str) -> bool:
    return bool(_EVIDENCE_TAG_LEAK_PATTERN.search(narrative))


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


def _vital_sign_mentioned_exists_in_snapshot(
    mentioned: MentionedVitalSign, snapshot: EmrSnapshot
) -> bool:
    """mentioned_measurements(LabResult)와 같은 "자기 보고 값을 Snapshot
    원본과 정확히 대조"하는 원칙을 VitalSign에 대해 적용한다.
    BLOOD_PRESSURE는 수축기·이완기 두 값이 모두 일치해야 한다(한쪽만
    맞으면 거부) - 나머지 6종은 value_secondary가 항상 None이어야
    일치한다."""
    target_value = _to_decimal(mentioned.value)
    if target_value is None:
        return False
    target_secondary = (
        _to_decimal(mentioned.value_secondary) if mentioned.value_secondary is not None else None
    )
    if mentioned.value_secondary is not None and target_secondary is None:
        return False

    for vital in snapshot.vital_signs:
        if vital.vital_type != mentioned.vital_type:
            continue
        if vital.unit.strip() != mentioned.unit.strip():
            continue
        if vital.value != target_value:
            continue
        if target_secondary is None:
            if vital.value_secondary is not None:
                continue
        elif vital.value_secondary != target_secondary:
            continue
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
    if (
        not result.cited_record_ids
        and not result.mentioned_measurements
        and not result.mentioned_vital_signs
    ):
        return NarrativeValidationResult(False, "no_evidence_provided")
    if not _cited_ids_are_subset(result, snapshot):
        return NarrativeValidationResult(False, "cited_id_not_in_snapshot")
    if any(not _measurement_exists_in_snapshot(m, snapshot) for m in result.mentioned_measurements):
        return NarrativeValidationResult(False, "measurement_not_in_snapshot")
    if any(
        not _vital_sign_mentioned_exists_in_snapshot(v, snapshot)
        for v in result.mentioned_vital_signs
    ):
        return NarrativeValidationResult(False, "measurement_not_in_snapshot")
    if _contains_banned_phrase(result.narrative):
        return NarrativeValidationResult(False, "banned_phrase_detected")
    if _contains_evidence_tag_leak(result.narrative):
        return NarrativeValidationResult(False, "evidence_tag_leaked_into_narrative")
    return NarrativeValidationResult(True, None)

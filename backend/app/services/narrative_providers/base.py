"""ClinicalReport.content.narrative를 만드는 provider의 공통 계약.

Task 16의 결정적 Mock 생성기(app/services/mock_narrative.py)는 이 파일이
정의하는 어떤 것도 알 필요가 없다 - 이 인터페이스를 감싸는 쪽은
DeterministicMockProvider(mock_provider.py)뿐이다. 실제 LLM은 아직
연결하지 않는다 - RealLLMProvider(real_llm_provider.py)는 골격만
존재하고, 벤더별 HTTP Adapter는 이번 단계에서 구현하지 않는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.clinical_report import EmrSnapshot


@dataclass(frozen=True)
class MentionedMeasurement:
    test_name: str
    value: float
    unit: str


@dataclass(frozen=True)
class MentionedVitalSign:
    """Task F4-B: MentionedMeasurement와 같은 역할(LLM이 narrative에서
    실제로 언급한 값을 자기 보고하게 해 결정적으로 검증하는 용도)을
    VitalSign에 대해 담당한다. value_secondary는 BLOOD_PRESSURE의
    이완기 값에만 쓰이고, 그 외 6종은 항상 None이다."""

    vital_type: str
    value: float
    value_secondary: float | None
    unit: str


@dataclass(frozen=True)
class NarrativeProviderResult:
    narrative: str
    cited_record_ids: list[str]
    mentioned_measurements: list[MentionedMeasurement]
    # provider/model/version은 항상 서버(각 Provider 구현체 또는 서버
    # 설정)가 직접 채운다 - LLM 응답 JSON에서 받아오지 않는다(신뢰할 수
    # 없는 자기 보고 값이기 때문).
    provider: str
    model: str
    version: str
    # Task F4-B: 기본값이 있어야 기존 호출부(테스트 포함)가 이 필드를
    # 몰라도 그대로 동작한다.
    mentioned_vital_signs: list[MentionedVitalSign] = field(default_factory=list)


class NarrativeProviderError(Exception):
    """설정 오류(키/모델 누락, Adapter 미구성)와 공급자 측 실패(네트워크
    실패, 잘못된 JSON, 검증 실패)를 모두 이 예외로 통일한다. code는
    서버 로그와 감사 로그 reason에만 남기고 HTTP 응답 본문에는 절대
    그대로 노출하지 않는다 - 라우터는 이 예외를 잡아 항상 같은 일반
    메시지로 변환한다."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


class NarrativeProvider(ABC):
    @abstractmethod
    def generate(self, snapshot: EmrSnapshot) -> NarrativeProviderResult:
        """저장된 EmrSnapshot만으로 설명문 초안을 만든다. 원본 스냅샷을
        수정하지 않는다."""

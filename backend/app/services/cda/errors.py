"""HL7-4A: CDA 에러 타입 + structured warning + config 교차검증.

HL7-2 §23/§25 에러 모델과 HL7-3 §16(Validation Timing Option C)을
구현한다. CDA_ENABLED=false면 아무것도 검사하지 않고(narrative_provider
와 같은 이유 - 한 기능의 설정 부재가 앱 전체를 막으면 안 됨),
CDA_ENABLED=true면 필요한 설정이 전부 있고 유효한지 즉시(= 호출 시점에
eager하게) 검사한다. 이 함수를 실제 FastAPI startup에 연결하는 것은
이번 HL7-4A의 범위 밖이다(API 미구현).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import Settings
from app.services.cda.models import validate_uuid_root

# BCP-47 형식에 대한 이 프로젝트 자체의 narrow한 self-check다 - CDA
# Core(XSD) 자체는 languageCode에 이런 형식을 강제하지 않는다(타입
# CS는 codeSystem 계열 속성이 전부 prohibited인 단순 문자열, HL7-1A
# §19). 이 정규식은 "ko-KR" 같은 단순 language-REGION 태그만 받아들이는
# 매우 보수적인 self-check이며, CDA 표준이 요구하는 형식이 아니다.
_LANGUAGE_TAG_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")

_ROOT_FIELDS: tuple[tuple[str, str], ...] = (
    ("cda_document_id_root", "MISSING_DOCUMENT_ROOT"),
    ("cda_patient_id_root", "MISSING_PATIENT_ROOT"),
    ("cda_encounter_id_root", "MISSING_ENCOUNTER_ROOT"),
    ("cda_author_id_root", "MISSING_AUTHOR_ROOT"),
    ("cda_custodian_id_root", "MISSING_CUSTODIAN_ROOT"),
    ("cda_entry_id_root", "MISSING_ENTRY_ROOT"),
)


class CdaConfigError(Exception):
    """CDA_ENABLED=true인데 필수 설정이 없거나 형식이 잘못된 경우(HL7-2
    §23 에러 분류 중 MISSING_*_ROOT/INVALID_*_ROOT/MISSING_CUSTODIAN_NAME/
    INVALID_LANGUAGE_CODE 계열). HTTP 응답에 노출하지 않고 서버 로그에만
    code/필드명을 남기는 것을 원칙으로 한다(HL7-2 §23) - 이 예외 자체는
    그 경계를 강제하지 않지만, 호출자가 그 원칙을 지키도록 code 속성을
    분리해 둔다."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class CdaEligibilityError(Exception):
    """HL7-2 §4/§23 Export Eligibility 실패(NOT_APPROVED,
    UNSUPPORTED_REPORT_TYPE, UNSUPPORTED_SCOPE, MISSING_SNAPSHOT 등)."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class CdaWarning:
    """HL7-4A §15: Mapper가 반환할 수 있는 non-fatal warning. 환자 이름/
    MRN/narrative 전문/임상 데이터 전문을 담지 않는다 - source_record_id
    같은 이미 익명화된 로컬 레코드 식별자(예: "vital_sign:42")만 담는다.
    이 값은 XML에 자동 삽입되지 않는다 - 호출자/로그를 위한 metadata다."""

    code: str
    source_type: str
    source_record_id: str
    message: str


def validate_cda_settings(settings: Settings) -> None:
    """CDA_ENABLED=false면 아무것도 하지 않는다. true면 6개 root UUID,
    custodian extension/name, language code가 전부 존재하고 유효한지
    확인한다. 개별 root의 "형식"은 이미 Settings field_validator가
    검사했으므로(빈 문자열이 아니면 항상 유효한 UUID), 여기서는 주로
    "활성화 시 필수"라는 교차조건만 추가로 본다."""
    if not settings.cda_enabled:
        return

    for field_name, error_code in _ROOT_FIELDS:
        value = getattr(settings, field_name)
        if value == "":
            raise CdaConfigError(error_code, f"CDA_ENABLED=true인데 {field_name}이 비어 있습니다.")
        # 이미 Settings 생성 시점에 형식 검증을 통과했으나, 호출자가
        # Settings를 직접 조립한 경우(테스트 등)를 대비해 한 번 더
        # 방어적으로 확인한다.
        validate_uuid_root(value, field_name=field_name)

    if settings.cda_custodian_id_extension == "":
        raise CdaConfigError("MISSING_CUSTODIAN_EXTENSION", "CDA_CUSTODIAN_ID_EXTENSION이 비어 있습니다.")

    if settings.cda_custodian_name == "":
        raise CdaConfigError("MISSING_CUSTODIAN_NAME", "CDA_CUSTODIAN_NAME이 비어 있습니다.")

    if not _LANGUAGE_TAG_PATTERN.match(settings.cda_language_code):
        raise CdaConfigError(
            "INVALID_LANGUAGE_CODE",
            f"CDA_LANGUAGE_CODE 형식이 올바르지 않습니다: {settings.cda_language_code!r}",
        )

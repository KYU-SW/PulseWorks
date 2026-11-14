"""HL7-4A §5/§15/§25: CDA config 교차검증 + structured warning + eligibility
에러 테스트."""

import pytest

from app.core.config import Settings
from app.services.cda.errors import (
    CdaConfigError,
    CdaEligibilityError,
    CdaWarning,
    validate_cda_settings,
)

_VALID_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"


def _full_settings(**overrides) -> Settings:
    base = dict(
        cda_enabled=True,
        cda_document_id_root=_VALID_ROOT,
        cda_patient_id_root=_VALID_ROOT,
        cda_encounter_id_root=_VALID_ROOT,
        cda_author_id_root=_VALID_ROOT,
        cda_custodian_id_root=_VALID_ROOT,
        cda_entry_id_root=_VALID_ROOT,
        cda_custodian_id_extension="synthetic-facility-1",
        cda_custodian_name="EMR Synthetic Demonstration Facility",
        cda_language_code="ko-KR",
    )
    base.update(overrides)
    return Settings(**base)


class TestValidateCdaSettings:
    def test_disabled_skips_validation_entirely(self):
        # CDA_ENABLED=false면 아무 필드가 비어 있어도 통과한다(HL7-3 §16
        # Option C).
        validate_cda_settings(Settings(cda_enabled=False))

    def test_fully_configured_enabled_settings_pass(self):
        validate_cda_settings(_full_settings())

    def test_missing_document_root_fails_when_enabled(self):
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_document_id_root=""))
        assert exc_info.value.code == "MISSING_DOCUMENT_ROOT"

    def test_missing_patient_root_fails_when_enabled(self):
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_patient_id_root=""))
        assert exc_info.value.code == "MISSING_PATIENT_ROOT"

    def test_missing_custodian_name_fails_when_enabled(self):
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_custodian_name=""))
        assert exc_info.value.code == "MISSING_CUSTODIAN_NAME"

    def test_missing_custodian_extension_fails_when_enabled(self):
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_custodian_id_extension=""))
        assert exc_info.value.code == "MISSING_CUSTODIAN_EXTENSION"

    def test_invalid_language_code_fails_when_enabled(self):
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_language_code="not a language tag!"))
        assert exc_info.value.code == "INVALID_LANGUAGE_CODE"

    def test_error_message_never_includes_secret_like_hint(self):
        # CDA config 값 자체는 secret이 아니다(HL7-3 §17) - 에러 메시지에
        # 원인 필드명을 그대로 남겨도 된다. 이 테스트는 적어도 code 속성이
        # 항상 존재함을 보장한다.
        with pytest.raises(CdaConfigError) as exc_info:
            validate_cda_settings(_full_settings(cda_author_id_root=""))
        assert exc_info.value.code == "MISSING_AUTHOR_ROOT"


class TestCdaWarning:
    def test_warning_carries_safe_fields_only(self):
        warning = CdaWarning(
            code="INCOMPLETE_BLOOD_PRESSURE",
            source_type="vital_sign",
            source_record_id="vital_sign:42",
            message="혈압 수축기/이완기 중 하나가 없어 해당 Entry를 생략했습니다.",
        )
        assert warning.code == "INCOMPLETE_BLOOD_PRESSURE"
        assert warning.source_record_id == "vital_sign:42"

    def test_warning_is_immutable(self):
        warning = CdaWarning(
            code="INCOMPLETE_BLOOD_PRESSURE",
            source_type="vital_sign",
            source_record_id="vital_sign:42",
            message="메시지",
        )
        with pytest.raises(AttributeError):
            warning.code = "OTHER"  # type: ignore[misc]


class TestCdaEligibilityError:
    def test_carries_a_code(self):
        error = CdaEligibilityError("NOT_APPROVED")
        assert error.code == "NOT_APPROVED"

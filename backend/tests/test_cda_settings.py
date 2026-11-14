"""HL7-4A §5/§24: CDA system-level Settings 테스트.

CDA_ENABLED=false면 기존 Backend가 CDA config 없이도 정상 기동해야
한다(HL7-3 §14). 합성 테스트용 UUID만 사용한다 - 실제 UUID는 하드코딩
하지 않는다.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_VALID_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"


def _settings_with_valid_cda_config(**overrides):
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
    )
    base.update(overrides)
    return Settings(**base)


class TestCdaDisabledDefault:
    def test_default_settings_have_cda_disabled(self):
        settings = Settings()
        assert settings.cda_enabled is False

    def test_disabled_settings_allow_missing_cda_config(self):
        # CDA_ENABLED=false면 어떤 CDA 필드도 비어 있어도 Settings()
        # 생성 자체는 성공해야 한다(기존 Backend 기동에 영향 없음).
        settings = Settings(cda_enabled=False)
        assert settings.cda_document_id_root == ""

    def test_default_language_code(self):
        assert Settings().cda_language_code == "ko-KR"


class TestCdaFieldFormatValidation:
    def test_empty_root_is_allowed_at_field_level(self):
        # 필드 자체의 포맷 검증은 "비어있지 않다면 UUID 형식이어야 한다"
        # 수준이다 - "활성화 시 필수"라는 교차검증은 validate_cda_settings
        # (errors.py)가 별도로 한다(narrative_provider와 동일한 선례).
        settings = Settings(cda_document_id_root="")
        assert settings.cda_document_id_root == ""

    def test_malformed_uuid_root_is_rejected(self):
        with pytest.raises(ValidationError, match="UUID"):
            Settings(cda_document_id_root="not-a-uuid")

    def test_urn_uuid_prefix_is_rejected(self):
        with pytest.raises(ValidationError, match="urn:uuid:"):
            Settings(cda_patient_id_root=f"urn:uuid:{_VALID_ROOT}")

    def test_whitespace_in_root_is_rejected(self):
        with pytest.raises(ValidationError, match="whitespace"):
            Settings(cda_encounter_id_root=f" {_VALID_ROOT}")

    @pytest.mark.parametrize(
        "field_name",
        [
            "cda_document_id_root",
            "cda_patient_id_root",
            "cda_encounter_id_root",
            "cda_author_id_root",
            "cda_custodian_id_root",
            "cda_entry_id_root",
        ],
    )
    def test_all_six_roots_are_validated(self, field_name):
        with pytest.raises(ValidationError, match="UUID"):
            Settings(**{field_name: "bad"})


class TestCdaEnabledWithFullConfig:
    def test_valid_full_config_constructs_successfully(self):
        settings = _settings_with_valid_cda_config()
        assert settings.cda_enabled is True
        assert settings.cda_custodian_name == "EMR Synthetic Demonstration Facility"

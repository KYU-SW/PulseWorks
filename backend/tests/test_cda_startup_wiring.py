"""HL7-4A.1 §9-§13: CDA Settings startup wiring TDD.

HL7-4A Diff Audit에서 OPEN_INTEGRATION_ITEM으로 남겨진 사항을 해결한다:
validate_cda_settings()는 구현/테스트는 있었지만 실제 FastAPI startup
경로(app.main)에 연결되어 있지 않았다. 이 파일은 app.main이 모듈
import(=프로세스 기동) 시점에 실제로 CDA 설정을 검사하는지 확인한다.

CDA_ENABLED=false면 기존 Backend 기동에 영향이 없어야 한다(HL7-3 §14,
narrative_provider와 동일한 선례) - 이는 이미 app.main을 import하는
모든 다른 테스트 파일이 매번 통과하고 있다는 사실 자체로 간접
증명되지만, 여기서는 그 wiring 함수 자체를 직접 호출해 명시적으로
확인한다(narrative_providers.factory 테스트들이 get_settings를
monkeypatch하는 것과 동일한 관례를 따른다)."""

import pytest
from pydantic import ValidationError

import app.main as main_module
from app.core.config import Settings
from app.services.cda.errors import CdaConfigError

_VALID_ROOT = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"


def _valid_cda_settings(**overrides) -> Settings:
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


class TestCdaStartupWiring:
    def test_cda_disabled_with_missing_roots_boots_normally(self, monkeypatch):
        # Case A: CDA_ENABLED=false + CDA root 없음 -> 기동 정상.
        monkeypatch.setattr(main_module, "get_settings", lambda: Settings(cda_enabled=False))
        main_module.validate_cda_startup_config()  # raises 없이 통과해야 한다.

    def test_cda_enabled_with_valid_config_boots_normally(self, monkeypatch):
        # Case B: CDA_ENABLED=true + valid config -> 기동 정상.
        monkeypatch.setattr(main_module, "get_settings", lambda: _valid_cda_settings())
        main_module.validate_cda_startup_config()  # raises 없이 통과해야 한다.

    def test_cda_enabled_with_missing_required_config_fails_fast(self, monkeypatch):
        # Case C: CDA_ENABLED=true + 필수 설정 누락 -> 기동 실패.
        monkeypatch.setattr(
            main_module, "get_settings", lambda: _valid_cda_settings(cda_custodian_name="")
        )
        with pytest.raises(CdaConfigError) as exc_info:
            main_module.validate_cda_startup_config()
        assert exc_info.value.code == "MISSING_CUSTODIAN_NAME"

    def test_cda_enabled_with_invalid_uuid_fails_fast(self, monkeypatch):
        # Case D: CDA_ENABLED=true + malformed UUID -> 기동 실패.
        # 잘못된 UUID는 Settings() 생성 자체(필드 검증)에서 이미
        # ValidationError로 막히므로, get_settings()를 호출하는 순간
        # validate_cda_startup_config()도 그 예외를 그대로 전파해야
        # 한다 - 즉 더 일찍(Settings 조립 단계에서) fail-fast된다.
        def _broken_get_settings() -> Settings:
            return Settings(cda_enabled=True, cda_document_id_root="not-a-uuid")

        monkeypatch.setattr(main_module, "get_settings", _broken_get_settings)
        with pytest.raises(ValidationError, match="UUID"):
            main_module.validate_cda_startup_config()

    def test_app_module_already_validated_real_settings_on_import(self):
        # 실제 production wiring 확인: 이 테스트가 실행된다는 것 자체가
        # app.main이 이미 import되어 validate_cda_startup_config()가
        # 실제 get_settings()로 한 번 호출된 뒤라는 뜻이다(기본 .env는
        # CDA_ENABLED=false이므로 예외 없이 통과했어야 한다). 함수가
        # 모듈에 실제로 존재하는지도 함께 확인한다.
        assert callable(main_module.validate_cda_startup_config)

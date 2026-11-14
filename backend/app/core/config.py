from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.cda.models import validate_uuid_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://emr:emr@localhost:5432/emr"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480

    # Narrative Provider 기반(향후 실제 LLM 연결용). 기본값 mock은 항상
    # 안전해야 한다. "llm 모드에는 api key와 model이 필요하다"는 교차
    # 검증은 일부러 여기(Settings) 대신
    # app/services/narrative_providers/factory.py가 요청 시점에 한다 -
    # db.py/security.py 등 narrative와 무관한 모듈도 앱 시작 시점에
    # get_settings()를 그대로 가져다 쓰므로, 여기서 그 교차 검증을 하면
    # llm 모드 설정 실수 하나가 앱 전체를 못 띄우게 만든다. 아래 세
    # 필드 검증은 모드와 무관하게 항상 참이어야 하는 값 범위 검사라
    # 여기 둬도 그런 위험이 없다.
    narrative_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str = ""
    llm_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 1000
    # Task B: 어떤 벤더를 쓸지(예: "ollama")와 그 벤더의 API 주소.
    # "이 값이 있으면 어떤 벤더인지" 같은 교차 검증은 여기서 하지 않고
    # factory.py가 한다 - 위 llm_api_key와 같은 이유(narrative_provider와
    # 무관한 모듈도 앱 시작 시 Settings()를 그대로 쓰기 때문).
    llm_vendor: str = ""
    llm_base_url: str = ""

    # HL7-3/HL7-3A: CDA export system-level config. CDA_ENABLED=false가
    # 기본값이라 이 10개 필드가 전부 비어 있어도 기존 Backend 기동에
    # 영향이 없다(narrative_provider와 같은 이유 - 한 기능의 설정
    # 부재가 앱 전체를 막으면 안 된다). "CDA_ENABLED=true일 때 이
    # 필드들이 전부 채워져 있어야 한다"는 교차검증은 여기(Settings)가
    # 아니라 app/services/cda/errors.py::validate_cda_settings()가
    # 한다 - 그 이유도 narrative_provider와 동일하다(db.py/security.py
    # 등 CDA와 무관한 모듈도 앱 시작 시 get_settings()를 그대로 쓴다).
    # 아래 필드별 검증은 "값이 있다면 형식이 올바른가"만 본다 - 항상
    # 참이어야 하는 검사라 narrative_provider 교차검증 문제와 무관하다.
    cda_enabled: bool = False
    cda_document_id_root: str = ""
    cda_patient_id_root: str = ""
    cda_encounter_id_root: str = ""
    cda_author_id_root: str = ""
    cda_custodian_id_root: str = ""
    cda_entry_id_root: str = ""
    cda_custodian_id_extension: str = ""
    cda_custodian_name: str = ""
    cda_language_code: str = "ko-KR"

    @field_validator(
        "cda_document_id_root",
        "cda_patient_id_root",
        "cda_encounter_id_root",
        "cda_author_id_root",
        "cda_custodian_id_root",
        "cda_entry_id_root",
    )
    @classmethod
    def _validate_cda_root_format(cls, value: str) -> str:
        if value == "":
            # 비어 있는 것은 "CDA_ENABLED=false라 아직 설정 안 함"일 수
            # 있으므로 여기서는 허용한다 - 필수 여부는
            # validate_cda_settings()가 별도로 검사한다.
            return value
        validate_uuid_root(value)
        return value

    @field_validator("narrative_provider")
    @classmethod
    def _validate_narrative_provider(cls, value: str) -> str:
        if value not in ("mock", "llm"):
            raise ValueError('narrative_provider must be "mock" or "llm"')
        return value

    @field_validator("llm_timeout_seconds")
    @classmethod
    def _validate_llm_timeout_seconds(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("llm_timeout_seconds must be positive")
        return value

    @field_validator("llm_max_output_tokens")
    @classmethod
    def _validate_llm_max_output_tokens(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("llm_max_output_tokens must be positive")
        return value


def get_settings() -> Settings:
    return Settings()

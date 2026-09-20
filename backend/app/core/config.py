from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

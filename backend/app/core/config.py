from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://emr:emr@localhost:5432/emr"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()

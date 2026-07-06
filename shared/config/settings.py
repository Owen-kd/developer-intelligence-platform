"""중앙 설정. 환경변수(.env)를 단일 소스로 로드한다.

modules/ 는 이 설정을 직접 읽지 않고, infrastructure/ 계층이 사용한다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "local"
    app_debug: bool = True

    # Auth (내부 도구 최소 모델 — 로컬 기본값. 운영은 시크릿 매니저로 주입)
    api_token: str = "dev-token"

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "dip"
    postgres_password: str = "dip"
    postgres_db: str = "dip"

    # LLM (infrastructure 계층에서만 사용)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"  # 분류/요약엔 가장 저렴한 모델. 필요 시 상향.

    # Jira (infrastructure 계층에서만 사용)
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """프로세스당 한 번만 로드되는 설정 싱글턴."""
    return Settings()

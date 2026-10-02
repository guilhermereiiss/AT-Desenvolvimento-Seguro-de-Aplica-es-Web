from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas as credenciais vêm de variáveis de ambiente / .env (sem defaults sensíveis)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "clinicas-api"
    jwt_audience: str = "clinicas-api"
    access_token_minutes: int = 15
    bcrypt_rounds: int = Field(default=12, ge=4, le=15)
    mfa_simulated_code: str
    cors_origins: list[str] = []  # allowlist explícita, JSON no .env
    lab_client_id: str
    lab_client_secret: str
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60
    m2m_rate_limit: int = 20

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

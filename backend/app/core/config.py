from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "車なし生活リハーサル"
    routing_provider: str = Field(default="mock", alias="ROUTING_PROVIDER")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )
    otp_graphql_url: str | None = Field(default=None, alias="OTP_GRAPHQL_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        origins = []
        for raw_origin in self.cors_origins.split(","):
            cleaned = raw_origin.strip().rstrip("/")
            if cleaned:
                origins.append(cleaned)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "車なし生活リハーサル"
    routing_provider: Literal["mock", "otp"] = Field(default="mock", alias="ROUTING_PROVIDER")
    otp_route_rules_path: str = Field(
        default=str(Path(__file__).resolve().parents[3] / "data/hakusan/route-rules.json"),
        alias="OTP_ROUTE_RULES_PATH",
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )
    otp_graphql_url: str | None = Field(default=None, alias="OTP_GRAPHQL_URL")
    otp_identity_audience: str | None = Field(default=None, alias="OTP_IDENTITY_AUDIENCE")

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

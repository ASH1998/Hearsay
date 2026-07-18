from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HEARSAY_",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="HEARSAY_ENV")
    log_level: str = "INFO"
    web_origin: str = "http://localhost:3000"
    director_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from hearsay_api.persistence.database import derive_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HEARSAY_",
        case_sensitive=True,
        extra="ignore",
    )

    environment: str = Field(default="development", alias="HEARSAY_ENV")
    log_level: str = Field(default="INFO", alias="HEARSAY_LOG_LEVEL")
    web_origin: str = Field(
        default="http://localhost:3000",
        alias="HEARSAY_WEB_ORIGIN",
    )
    director_enabled: bool = Field(
        default=False,
        alias="HEARSAY_DIRECTOR_ENABLED",
    )
    persistence_backend: Literal["memory", "cockroachdb"] = Field(
        default="memory",
        alias="HEARSAY_PERSISTENCE_BACKEND",
    )
    database_url: SecretStr | None = Field(default=None, validation_alias="DATABASE_URL")
    database_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("COCKROACH_USERNAME", "username"),
        exclude=True,
    )
    database_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("COCKROACH_PASSWORD", "password"),
        exclude=True,
    )
    database_connection_command: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("COMMAND_TO_CONNECT", "command_to_connect"),
        exclude=True,
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        alias="HEARSAY_DATABASE_POOL_SIZE",
    )
    transaction_max_retries: int = Field(
        default=4,
        ge=0,
        le=20,
        alias="HEARSAY_TRANSACTION_MAX_RETRIES",
    )
    llm_provider: Literal["auto", "fallback", "modal"] = Field(
        default="auto",
        alias="HEARSAY_LLM_PROVIDER",
    )
    modal_proxy_url: str | None = Field(
        default=None,
        validation_alias="MODAL_PROXY_URL",
        exclude=True,
    )
    modal_proxy_token_id: SecretStr | None = Field(
        default=None,
        validation_alias="MODAL_PROXY_TOKEN_ID",
        exclude=True,
    )
    modal_proxy_token_secret: SecretStr | None = Field(
        default=None,
        validation_alias="MODAL_PROXY_TOKEN_SECRET",
        exclude=True,
    )
    modal_model: str = Field(
        default="thinkingmachines/Inkling-NVFP4",
        alias="HEARSAY_MODAL_MODEL",
    )
    inference_timeout_seconds: float = Field(
        default=45,
        ge=1,
        le=180,
        alias="HEARSAY_INFERENCE_TIMEOUT_SECONDS",
    )
    inference_max_attempts: int = Field(
        default=2,
        ge=1,
        le=3,
        alias="HEARSAY_INFERENCE_MAX_ATTEMPTS",
    )

    @model_validator(mode="after")
    def derive_legacy_database_url(self) -> Settings:
        if self.database_url is not None or self.database_connection_command is None:
            return self
        password = (
            self.database_password.get_secret_value()
            if self.database_password is not None
            else None
        )
        self.database_url = SecretStr(
            derive_database_url(
                self.database_connection_command.get_secret_value(),
                username=self.database_username,
                password=password,
                database_name="hearsay",
            )
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

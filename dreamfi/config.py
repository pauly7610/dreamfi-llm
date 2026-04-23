"""DreamFi runtime configuration."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://dreamfi:dreamfi@localhost:5433/dreamfi"
    )
    onyx_base_url: str = Field(default="http://localhost:8080")
    onyx_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    default_llm_model: str = Field(default="claude-3-5-sonnet-20241022")
    fallback_llm_models: list[str] = Field(
        default_factory=lambda: ["claude-3-5-haiku-20241022", "gpt-4o-mini"]
    )
    llm_request_timeout_seconds: float = Field(default=60.0)
    llm_max_cost_usd_per_call: float = Field(default=1.0)
    log_level: str = Field(default="INFO")

    # Thresholds — documented units below.
    dreamfi_confidence_threshold: float = Field(default=0.75)  # 0–1
    dreamfi_improvement_threshold: float = Field(default=0.02)  # fraction, e.g. 0.02 == 2%
    dreamfi_freshness_halflife_days: float = Field(default=14.0)  # days
    dreamfi_export_readiness_threshold: float = Field(default=0.80)  # 0–1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

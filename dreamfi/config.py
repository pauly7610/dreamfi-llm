"""DreamFi runtime configuration."""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+psycopg://dreamfi:dreamfi@localhost:5433/dreamfi"


def normalize_database_url(url: str) -> str:
    """Prefer the psycopg dialect while preserving any existing query params."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    database_url: str | None = Field(
        default=None,
    )
    pg_host: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PGHOST", "PG_HOST"),
    )
    pg_port: int | None = Field(
        default=None,
        validation_alias=AliasChoices("PGPORT", "PG_PORT"),
    )
    pg_user: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PGUSER", "PG_USER"),
    )
    pg_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PGPASSWORD", "PG_PASSWORD"),
    )
    pg_database: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PGDATABASE", "PG_DATABASE"),
    )
    onyx_base_url: str = Field(default="http://localhost:8080")
    onyx_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    default_llm_model: str = Field(default="claude-3-5-sonnet-20241022")
    log_level: str = Field(default="INFO")
    dreamfi_auth_enabled: bool = Field(default=True)
    dreamfi_auth_username: str = Field(default="dreamfi")
    dreamfi_auth_password: str = Field(default="")
    dreamfi_api_token: str = Field(
        default="",
        validation_alias=AliasChoices("DREAMFI_API_TOKEN", "DREAMFI_API_KEY"),
    )

    # Thresholds -- documented units below.
    dreamfi_confidence_threshold: float = Field(default=0.75)  # 0-1
    dreamfi_improvement_threshold: float = Field(default=0.02)  # fraction
    dreamfi_freshness_halflife_days: float = Field(default=14.0)  # days
    dreamfi_ask_search_limit: int = Field(default=5)
    dreamfi_claim_lineage_target_citations: int = Field(default=3)
    dreamfi_min_outputs_per_eval_input: int = Field(default=1)
    dreamfi_max_outputs_per_eval_input: int = Field(default=10)
    dreamfi_probe_connector_status: bool = Field(default=True)
    dreamfi_connector_probe_search_limit: int = Field(default=1)
    dreamfi_connector_stale_after_days: int = Field(default=14)
    dreamfi_workflow_min_citations: int = Field(default=1)
    dreamfi_workflow_min_section_words: int = Field(default=3)
    dreamfi_workflow_require_scope: bool = Field(default=True)
    dreamfi_audit_enabled: bool = Field(default=True)
    dreamfi_audit_log_reads: bool = Field(default=True)
    dreamfi_learning_cluster_min_count: int = Field(default=2)
    dreamfi_learning_cluster_window_days: int = Field(default=30)
    dreamfi_learning_stale_freshness_threshold: float = Field(default=0.5)  # 0-1
    dreamfi_learning_replay_default_cadence_days: int = Field(default=7)
    dreamfi_slo_hard_gate_pass_rate: float = Field(default=0.8)  # 0-1
    dreamfi_slo_blocked_rate: float = Field(default=0.2)  # 0-1
    dreamfi_slo_publish_success_rate: float = Field(default=0.75)  # 0-1
    dreamfi_backup_dir: str = Field(default="backups")
    dreamfi_backup_retention_days: int = Field(default=14)
    dreamfi_backup_max_files: int = Field(default=30)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return normalize_database_url(self.database_url)

        if (
            self.pg_host
            and self.pg_user
            and self.pg_password
            and self.pg_database
        ):
            pg_port = self.pg_port or 5432
            user = quote(self.pg_user, safe="")
            password = quote(self.pg_password, safe="")
            database = quote(self.pg_database, safe="")
            return (
                f"postgresql+psycopg://{user}:{password}"
                f"@{self.pg_host}:{pg_port}/{database}"
            )

        return LOCAL_DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()

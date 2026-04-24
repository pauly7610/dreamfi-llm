from __future__ import annotations

import pytest

from dreamfi.config import LOCAL_DATABASE_URL, Settings, normalize_database_url


def test_normalize_database_url_converts_generic_postgres_scheme() -> None:
    assert (
        normalize_database_url("postgresql://user:pass@db.internal:5432/app")
        == "postgresql+psycopg://user:pass@db.internal:5432/app"
    )


def test_normalize_database_url_converts_legacy_postgres_scheme() -> None:
    assert (
        normalize_database_url("postgres://user:pass@db.internal:5432/app?sslmode=require")
        == "postgresql+psycopg://user:pass@db.internal:5432/app?sslmode=require"
    )


def test_settings_resolved_database_url_prefers_explicit_database_url() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://railway:secret@postgres.railway.internal:5432/railway",
    )

    assert (
        settings.resolved_database_url
        == "postgresql+psycopg://railway:secret@postgres.railway.internal:5432/railway"
    )


def test_settings_resolved_database_url_builds_from_pg_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PGHOST", "postgres.railway.internal")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGUSER", "dreamfi")
    monkeypatch.setenv("PGPASSWORD", "s3cr3t!")
    monkeypatch.setenv("PGDATABASE", "dreamfi")

    settings = Settings(_env_file=None, database_url=None)

    assert (
        settings.resolved_database_url
        == "postgresql+psycopg://dreamfi:s3cr3t%21@postgres.railway.internal:5432/dreamfi"
    )


def test_settings_resolved_database_url_falls_back_to_local_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for var_name in [
        "DATABASE_URL",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
    ]:
        monkeypatch.delenv(var_name, raising=False)
    settings = Settings(_env_file=None, database_url=None)

    assert settings.resolved_database_url == LOCAL_DATABASE_URL

"""Alembic migrations apply and reverse on SQLite in-memory."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def alembic_cfg(tmp_path: Path) -> Config:
    db_path = tmp_path / "dreamfi.db"
    url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = url
    from dreamfi.config import get_settings

    get_settings.cache_clear()

    cfg = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_head_creates_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    names = set(inspect(engine).get_table_names())
    expected = {
        "skills",
        "prompt_versions",
        "eval_rounds",
        "eval_outputs",
        "gold_examples",
        "publish_log",
        "console_topics",
        "onyx_document_map",
        "alembic_version",
    }
    assert expected.issubset(names), f"Missing tables: {expected - names}"


def test_upgrade_then_downgrade_clean(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    tables = set(inspect(engine).get_table_names())
    # Only alembic_version metadata table may survive.
    leftover = tables - {"alembic_version"}
    assert leftover == set(), f"Tables leaked across downgrade: {leftover}"

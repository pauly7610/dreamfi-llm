"""T2'/T3': metric catalog + snapshot discrepancy detection."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.context.bundle import ContextClaim
from dreamfi.db.models import Base
from dreamfi.trust.metrics import (
    find_discrepancies,
    latest_snapshot,
    record_snapshot,
    upsert_metric,
)


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_upsert_metric_idempotent(session: Session) -> None:
    row1 = upsert_metric(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        display_name="Activation Rate",
        source_systems=["posthog"],
    )
    row2 = upsert_metric(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        display_name="Activation Rate (PH)",
        source_systems=["posthog", "metabase"],
    )
    assert row1.row_id == row2.row_id
    assert row2.display_name == "Activation Rate (PH)"
    assert row2.source_systems_json == ["posthog", "metabase"]


def test_latest_snapshot_returns_most_recent(session: Session) -> None:
    upsert_metric(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        display_name="Activation Rate",
    )
    record_snapshot(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        source_system="posthog",
        as_of_date=datetime(2026, 4, 18, tzinfo=timezone.utc),
        value=Decimal("0.82"),
    )
    record_snapshot(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        source_system="posthog",
        as_of_date=datetime(2026, 4, 20, tzinfo=timezone.utc),
        value=Decimal("0.80"),
    )
    latest = latest_snapshot(
        session, workspace_id="w1", metric_id="activation_rate"
    )
    assert latest is not None
    assert latest.value == Decimal("0.80")


def test_missing_catalog_entry_is_a_lineage_error(session: Session) -> None:
    claim = ContextClaim(
        statement="Activation holds at 0.80",
        sot_id="metric_id=activation_rate;value=0.80",
        citation_ids=["metabase:42"],
    )
    issues = find_discrepancies(
        session,
        workspace_id="w1",
        claims=[claim],
        metric_ids_in_claims={str(claim.claim_id): ["activation_rate"]},
    )
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "not in the workspace's metric catalog" in issues[0].message


def test_snapshot_mismatch_yields_warning(session: Session) -> None:
    upsert_metric(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        display_name="Activation Rate",
    )
    record_snapshot(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        source_system="posthog",
        as_of_date=datetime(2026, 4, 20, tzinfo=timezone.utc),
        value=Decimal("0.82"),
    )
    claim = ContextClaim(
        statement="Activation is 0.75",
        sot_id="metric_id=activation_rate;value=0.75",
        citation_ids=["posthog:funnel"],
    )
    issues = find_discrepancies(
        session,
        workspace_id="w1",
        claims=[claim],
        metric_ids_in_claims={str(claim.claim_id): ["activation_rate"]},
    )
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert "0.75" in issues[0].message
    assert "0.82" in issues[0].message


def test_snapshot_within_tolerance_no_issue(session: Session) -> None:
    upsert_metric(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        display_name="Activation Rate",
    )
    record_snapshot(
        session,
        workspace_id="w1",
        metric_id="activation_rate",
        source_system="posthog",
        as_of_date=datetime(2026, 4, 20, tzinfo=timezone.utc),
        value=Decimal("0.820"),
    )
    claim = ContextClaim(
        statement="Activation is 0.819",
        sot_id="metric_id=activation_rate;value=0.819",
        citation_ids=["posthog:funnel"],
    )
    issues = find_discrepancies(
        session,
        workspace_id="w1",
        claims=[claim],
        metric_ids_in_claims={str(claim.claim_id): ["activation_rate"]},
    )
    assert issues == []

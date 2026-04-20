"""C1: ContextBundle.is_stale semantics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dreamfi.context import ContextBundle


def test_fresh_bundle_is_not_stale() -> None:
    now = datetime.now(timezone.utc)
    bundle = ContextBundle(
        workspace_id="w",
        topic="t",
        topic_key="t",
        refreshed_at=now - timedelta(minutes=5),
        ttl_seconds=3600,  # 1h
    )
    assert bundle.is_stale(now=now) is False


def test_bundle_past_ttl_is_stale() -> None:
    now = datetime.now(timezone.utc)
    bundle = ContextBundle(
        workspace_id="w",
        topic="t",
        topic_key="t",
        refreshed_at=now - timedelta(hours=2),
        ttl_seconds=3600,  # 1h
    )
    assert bundle.is_stale(now=now) is True


def test_is_stale_tolerates_naive_refreshed_at() -> None:
    naive_now = datetime(2026, 4, 20, 12, 0, 0)  # no tzinfo
    bundle = ContextBundle(
        workspace_id="w",
        topic="t",
        topic_key="t",
        refreshed_at=naive_now,
        ttl_seconds=60,
    )
    reference = datetime(2026, 4, 20, 12, 2, 0, tzinfo=timezone.utc)
    assert bundle.is_stale(now=reference) is True

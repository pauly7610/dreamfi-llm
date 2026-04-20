"""Live-Onyx smoke test. Skipped unless ONYX_BASE_URL is set."""
from __future__ import annotations

import os

import httpx
import pytest


@pytest.mark.live_onyx
def test_onyx_health() -> None:
    base = os.environ.get("ONYX_BASE_URL")
    if not base:
        pytest.skip("ONYX_BASE_URL not set")
    r = httpx.get(f"{base}/api/health", timeout=5)
    assert r.status_code == 200

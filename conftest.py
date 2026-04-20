"""Top-level pytest config for DreamFi.

Unit tests are fully self-contained (SQLite in-memory or temp file).
Integration tests marked `live_onyx` hit a real Onyx pointed at by $ONYX_BASE_URL.
"""
from __future__ import annotations


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    config.addinivalue_line(
        "markers", "live_onyx: tests that require a running Onyx"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests requiring docker"
    )
    config.addinivalue_line(
        "markers", "critical: critical-path tests"
    )

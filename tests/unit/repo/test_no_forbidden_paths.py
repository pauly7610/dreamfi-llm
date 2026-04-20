"""Repo hygiene — ensure deleted paths stay deleted."""
from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

FORBIDDEN = [
    "services/knowledge_hub/db/schema.sql",
    "services/knowledge_hub/db/migrations",
    "services/knowledge_hub/src/retrieval",
    "services/knowledge_hub/src/connectors",
    "integrations/jira_client.py",
    "integrations/confluence_client.py",
    "integrations/dragonboat_client.py",
    "integrations/metabase_client.py",
    "integrations/posthog_client.py",
    "integrations/google_analytics_client.py",
    "integrations/klaviyo_client.py",
    "integrations/sardine_client.py",
    "integrations/socure_client.py",
    "integrations/ledger_netxd_client.py",
    "services/planning-sync",
    "services/ui-support",
    "services/generators/src/templates",
    "services/reporting",
    "autoresearch-toolkit",
    "config.py",
    "package.json",
    "setup.py",
    "requirements.txt",
    ".env.local",
]


def test_forbidden_paths_absent() -> None:
    found = [p for p in FORBIDDEN if (REPO_ROOT / p).exists()]
    assert not found, f"These paths should be removed: {found}"

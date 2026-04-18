"""
DreamFi Knowledge Hub -- LLM-maintained product wiki.

Phase 1 of the DreamFi intelligence layer.  Uses Andrej Karpathy's
knowledge-base pattern: structured markdown pages governed by a strict
schema, ingested from multiple source systems, queryable via natural
language, and kept healthy by automated linting.

Quick-start
-----------
    # Ingest a Confluence space
    python -m knowledge_hub.ingest confluence --space-key PROD

    # Ask a question
    python -m knowledge_hub.query "How does KYC work end-to-end?"

    # Run health checks
    python -m knowledge_hub.lint
"""

from knowledge_hub.ingest import ingest_cli
from knowledge_hub.query import query_cli
from knowledge_hub.lint import lint_cli

__all__ = [
    "ingest_cli",
    "query_cli",
    "lint_cli",
]

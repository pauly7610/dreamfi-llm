"""FastAPI dependency providers."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.context.builder import ConnectorRegistry, ContextBuilder
from dreamfi.context.model_router import ModelRouter
from dreamfi.db.session import get_sessionmaker
from dreamfi.onyx.client import OnyxClient


def get_db_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def get_onyx_client() -> OnyxClient:
    s = get_settings()
    return OnyxClient(base_url=s.onyx_base_url, api_key=s.onyx_api_key)


def get_context_builder() -> ContextBuilder:
    """Placeholder production factory for the ContextBuilder.

    Production wiring (real Jira / Confluence clients + LiteLLM router) is
    P9 work; for now this raises so that the FastAPI app fails loudly if
    the Ask endpoint is hit without a test override.
    """
    raise RuntimeError(
        "Production ContextBuilder not wired yet — override "
        "dreamfi.api.deps.get_context_builder in tests or P9 setup."
    )


def build_context_builder(
    *,
    session: Session,
    connectors: ConnectorRegistry,
    llm: ModelRouter,
) -> ContextBuilder:
    """Convenience constructor used by tests and P9 wiring."""
    return ContextBuilder(connectors=connectors, llm=llm, session=session)

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


def get_llm_router() -> ModelRouter:
    """P9 — the production ModelRouter backed by LiteLLM."""
    from dreamfi.context.litellm_router import LiteLLMRouter

    s = get_settings()
    return LiteLLMRouter(
        primary_model=s.default_llm_model,
        fallback_models=s.fallback_llm_models,
        timeout_seconds=s.llm_request_timeout_seconds,
        max_cost_usd=s.llm_max_cost_usd_per_call,
    )


def get_context_builder() -> ContextBuilder:
    """Production factory for the ContextBuilder.

    Connector configuration (per-workspace Jira/Confluence credentials) is
    P13 onboarding work; until then this factory only provides the LLM
    router and leaves ``connectors`` empty. Tests and the P13 onboarding
    flow override this dependency with a registry that has real clients.
    """
    return ContextBuilder(connectors=ConnectorRegistry(), llm=get_llm_router())


def build_context_builder(
    *,
    session: Session,
    connectors: ConnectorRegistry,
    llm: ModelRouter,
) -> ContextBuilder:
    """Convenience constructor used by tests and P9 wiring."""
    return ContextBuilder(connectors=connectors, llm=llm, session=session)

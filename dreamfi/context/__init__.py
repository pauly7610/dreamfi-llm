"""Shared context engine (Phase C).

The ContextBundle is the typed, persisted unit of "what we know about a
topic right now" that every PM question and every generation consumes.
"""

from dreamfi.context.bundle import (
    ContextBundle,
    ContextClaim,
    ContextEntity,
    ContextSource,
    EntityRelation,
    OpenQuestion,
    compute_coverage_score,
)
from dreamfi.context.litellm_router import LiteLLMRouter, ModelBudgetExceeded
from dreamfi.context.topics import (
    TopicHint,
    TopicResolution,
    add_alias,
    link_entities,
    normalize_alias,
    resolve_topic,
)

__all__ = [
    "ContextBundle",
    "ContextClaim",
    "ContextEntity",
    "ContextSource",
    "EntityRelation",
    "LiteLLMRouter",
    "ModelBudgetExceeded",
    "OpenQuestion",
    "TopicHint",
    "TopicResolution",
    "add_alias",
    "compute_coverage_score",
    "link_entities",
    "normalize_alias",
    "resolve_topic",
]

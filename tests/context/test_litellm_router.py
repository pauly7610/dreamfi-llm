"""P9: LiteLLMRouter structured completion + fallback + budget."""
from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from dreamfi.context.litellm_router import (
    LiteLLMRouter,
    ModelBudgetExceeded,
)
from dreamfi.context.model_router import ContextStructuringError


class _Reply(BaseModel):
    summary: str
    points: list[str]


def _litellm_response(
    content: str, *, cost: float | None = None
) -> dict[str, Any]:
    """Minimal dict shape matching LiteLLM's completion output."""
    out: dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": content}}]
    }
    if cost is not None:
        out["_hidden_params"] = {"response_cost": cost}
    return out


def test_structured_complete_happy_path() -> None:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _litellm_response(
            json.dumps({"summary": "S", "points": ["a", "b"]}), cost=0.01
        )

    router = LiteLLMRouter(primary_model="claude-3-5-sonnet", completion=fake)
    reply = router.structured_complete(prompt="Topic: onboarding", schema=_Reply)

    assert reply.summary == "S"
    assert reply.points == ["a", "b"]
    # Request was issued with JSON-object response format.
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["model"] == "claude-3-5-sonnet"


def test_falls_back_when_primary_returns_invalid_json() -> None:
    attempts: list[str] = []

    def fake(**kwargs: Any) -> dict[str, Any]:
        attempts.append(kwargs["model"])
        if kwargs["model"] == "claude-3-5-sonnet":
            return _litellm_response("not-json-at-all")
        return _litellm_response(json.dumps({"summary": "ok", "points": []}))

    router = LiteLLMRouter(
        primary_model="claude-3-5-sonnet",
        fallback_models=["gpt-4o-mini"],
        completion=fake,
    )
    reply = router.structured_complete(prompt="p", schema=_Reply)
    assert reply.summary == "ok"
    assert attempts == ["claude-3-5-sonnet", "gpt-4o-mini"]


def test_falls_back_when_primary_fails_schema_validation() -> None:
    def fake(**kwargs: Any) -> dict[str, Any]:
        if kwargs["model"] == "primary":
            return _litellm_response(json.dumps({"summary": 42}))  # wrong types
        return _litellm_response(json.dumps({"summary": "s", "points": []}))

    router = LiteLLMRouter(
        primary_model="primary", fallback_models=["backup"], completion=fake
    )
    reply = router.structured_complete(prompt="p", schema=_Reply)
    assert reply.summary == "s"


def test_exhausting_fallbacks_raises_structuring_error() -> None:
    def fake(**kwargs: Any) -> dict[str, Any]:
        return _litellm_response("{not-json")

    router = LiteLLMRouter(
        primary_model="p", fallback_models=["b"], completion=fake
    )
    with pytest.raises(ContextStructuringError) as excinfo:
        router.structured_complete(prompt="x", schema=_Reply)
    assert "invalid JSON" in str(excinfo.value)


def test_model_hint_is_tried_first() -> None:
    attempts: list[str] = []

    def fake(**kwargs: Any) -> dict[str, Any]:
        attempts.append(kwargs["model"])
        return _litellm_response(json.dumps({"summary": "s", "points": []}))

    router = LiteLLMRouter(
        primary_model="primary", fallback_models=["backup"], completion=fake
    )
    router.structured_complete(prompt="p", schema=_Reply, model_hint="cheap")
    assert attempts[0] == "cheap"


def test_cost_above_cap_raises_budget_exceeded() -> None:
    def fake(**kwargs: Any) -> dict[str, Any]:
        return _litellm_response(
            json.dumps({"summary": "s", "points": []}), cost=2.5
        )

    router = LiteLLMRouter(
        primary_model="p", completion=fake, max_cost_usd=1.0
    )
    with pytest.raises(ModelBudgetExceeded):
        router.structured_complete(prompt="x", schema=_Reply)


def test_exception_from_litellm_triggers_fallback() -> None:
    def fake(**kwargs: Any) -> dict[str, Any]:
        if kwargs["model"] == "primary":
            raise RuntimeError("rate limited")
        return _litellm_response(json.dumps({"summary": "s", "points": []}))

    router = LiteLLMRouter(
        primary_model="primary", fallback_models=["backup"], completion=fake
    )
    reply = router.structured_complete(prompt="p", schema=_Reply)
    assert reply.summary == "s"

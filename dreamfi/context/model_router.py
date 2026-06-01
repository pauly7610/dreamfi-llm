"""Lightweight ModelRouter protocol (placeholder for P9/LiteLLM).

Today the Context Engine only needs *structured* completions: give the
model a prompt and a Pydantic schema, get back an instance. The real
LiteLLM-backed router arrives with P9; until then, tests use
``FakeModelRouter`` and production wires a thin httpx client (not yet
included).
"""
from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ContextStructuringError(RuntimeError):
    """Raised when the model returns something we cannot coerce to the schema."""


class ModelRouter(Protocol):
    def structured_complete(
        self,
        *,
        prompt: str,
        schema: type[T],
        model_hint: str | None = None,
    ) -> T: ...


class FakeModelRouter:
    """Deterministic stand-in. Tests pre-load responses keyed by prompt substring.

    If a prompt contains a substring in ``responses``, that response is
    returned (validated against ``schema``). Otherwise raises
    :class:`ContextStructuringError` — the production contract when the
    model returns garbage.
    """

    def __init__(self, responses: dict[str, BaseModel] | None = None) -> None:
        self.responses: dict[str, BaseModel] = responses or {}
        self.calls: list[str] = []

    def structured_complete(
        self,
        *,
        prompt: str,
        schema: type[T],
        model_hint: str | None = None,
    ) -> T:
        self.calls.append(prompt)
        for key, value in self.responses.items():
            if key in prompt:
                if not isinstance(value, schema):
                    raise ContextStructuringError(
                        f"fake response for '{key}' is not a {schema.__name__}"
                    )
                return value
        raise ContextStructuringError(
            f"no fake response matched (prompt prefix={prompt[:60]!r})"
        )

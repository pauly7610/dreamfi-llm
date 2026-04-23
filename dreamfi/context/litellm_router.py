"""P9 — LiteLLM-backed ModelRouter.

This is the production implementation of the :class:`ModelRouter`
protocol. It wraps a single LiteLLM callable (injectable for tests) and
adds three behaviors that the Context Engine depends on:

1. **Structured output.** Callers supply a Pydantic ``schema``; we ask
   the model for JSON, then validate. A validation failure raises
   :class:`ContextStructuringError` so the builder surfaces a 502 instead
   of persisting a half-built bundle.

2. **Fallback chain.** If the primary model fails (API error, rate limit,
   malformed JSON), we walk ``fallback_models`` in order and try again.

3. **Cost guard.** Every call is capped at ``max_cost_usd`` using the
   usage/cost fields LiteLLM returns; calls that exceed the cap raise
   :class:`ModelBudgetExceeded` so runaway requests surface instead of
   silently burning spend.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from dreamfi.context.model_router import ContextStructuringError

T = TypeVar("T", bound=BaseModel)

# LiteLLM's completion signature is quite wide; we type it loosely
# (``Any``) on purpose to avoid pinning the library's internal types.
LiteLLMCallable = Callable[..., Any]


class ModelBudgetExceeded(RuntimeError):
    """Raised when the LLM call's reported cost exceeds the per-call cap."""


class LiteLLMRouter:
    """ModelRouter implementation backed by ``litellm.completion``."""

    def __init__(
        self,
        *,
        primary_model: str,
        fallback_models: list[str] | None = None,
        completion: LiteLLMCallable | None = None,
        timeout_seconds: float = 60.0,
        max_cost_usd: float = 1.0,
        temperature: float = 0.2,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_models = list(fallback_models or [])
        self._completion = completion or _default_completion
        self.timeout_seconds = timeout_seconds
        self.max_cost_usd = max_cost_usd
        self.temperature = temperature

    def structured_complete(
        self,
        *,
        prompt: str,
        schema: type[T],
        model_hint: str | None = None,
    ) -> T:
        schema_json = schema.model_json_schema()
        system = (
            "You are DreamFi's Context Engine. Reply ONLY with a JSON object "
            "that validates against the given schema. No prose, no "
            "Markdown fences, no trailing commentary.\n\n"
            f"Schema:\n{json.dumps(schema_json)}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        models_to_try: list[str] = []
        if model_hint:
            models_to_try.append(model_hint)
        models_to_try.append(self.primary_model)
        models_to_try.extend(
            m for m in self.fallback_models if m not in models_to_try
        )

        last_error: Exception | None = None
        for model in models_to_try:
            try:
                response = self._completion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    timeout=self.timeout_seconds,
                    response_format={"type": "json_object"},
                )
            except Exception as e:  # noqa: BLE001 — covers LiteLLM + network errors
                last_error = e
                continue

            cost = _extract_cost(response)
            if cost is not None and cost > self.max_cost_usd:
                raise ModelBudgetExceeded(
                    f"{model} call cost ${cost:.4f} > cap ${self.max_cost_usd:.2f}"
                )

            content = _extract_content(response)
            if not content:
                last_error = ContextStructuringError(
                    f"{model}: empty response body"
                )
                continue

            try:
                payload = json.loads(content)
            except json.JSONDecodeError as e:
                last_error = ContextStructuringError(
                    f"{model}: invalid JSON — {e}"
                )
                continue

            try:
                return schema.model_validate(payload)
            except ValidationError as e:
                last_error = ContextStructuringError(
                    f"{model}: schema validation failed — {e}"
                )
                continue

        # Exhausted fallbacks.
        if isinstance(last_error, ContextStructuringError):
            raise last_error
        raise ContextStructuringError(
            f"all models failed; last error: {last_error}"
        )


# ---------------------------------------------------------------------------


def _default_completion(**kwargs: Any) -> Any:
    """Late import so tests that stub ``completion`` don't need the package."""
    import litellm

    return litellm.completion(**kwargs)


def _extract_content(response: Any) -> str:
    """Pull the first message's content from a LiteLLM-shaped response.

    Supports both dict-like and attribute-like shapes (LiteLLM wraps
    OpenAI's object-style response but also returns dicts in some
    providers / test doubles).
    """
    try:
        choices = (
            response.choices if hasattr(response, "choices") else response["choices"]
        )
    except (KeyError, AttributeError):
        return ""
    if not choices:
        return ""
    first = choices[0]
    message = first.message if hasattr(first, "message") else first.get("message", {})
    content = (
        message.content
        if hasattr(message, "content")
        else message.get("content", "") if isinstance(message, dict) else ""
    )
    return str(content or "")


def _extract_cost(response: Any) -> float | None:
    """LiteLLM attaches ``_hidden_params["response_cost"]`` on success."""
    hidden = getattr(response, "_hidden_params", None)
    if hidden is None and isinstance(response, dict):
        hidden = response.get("_hidden_params")
    if not isinstance(hidden, dict):
        return None
    cost = hidden.get("response_cost")
    if cost is None:
        return None
    try:
        return float(cost)
    except (TypeError, ValueError):
        return None

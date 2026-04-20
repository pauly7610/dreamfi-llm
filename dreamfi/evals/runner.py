"""Wrap the locked eval runners under evals/runners/ in a typed boundary.

The runners themselves are IMMUTABLE (ADR-003). This module only translates
between their dict-returning API and DreamFi's `EvalResult` Pydantic model.
"""
from __future__ import annotations

import importlib
from typing import Any, Literal

from pydantic import BaseModel

from dreamfi.skills.registry import load_registry


class EvalResult(BaseModel):
    skill_id: str
    pass_fail: Literal["pass", "fail"]
    failed_criteria: list[str]
    criteria: dict[str, bool]
    word_count: int | None = None
    eval_score: float = 0.0
    raw: dict[str, Any]


def run_eval(skill_id: str, output: str, test_input_label: str) -> EvalResult:
    registry = load_registry()
    if skill_id not in registry:
        raise KeyError(f"unknown skill_id: {skill_id}")
    spec = registry[skill_id]

    module = importlib.import_module(spec.runner_module)
    runner_cls = getattr(module, spec.runner_class)
    runner = runner_cls()
    raw = runner.score_output(output, test_input_label)
    criteria = dict(raw.get("criterion_details") or {})
    failed = list(raw.get("failed_criteria") or [])
    total = len(criteria) if criteria else 1
    passed = sum(1 for v in criteria.values() if v) if criteria else (
        1 if raw.get("pass_fail") == "pass" else 0
    )
    eval_score = passed / total if total else 0.0
    return EvalResult(
        skill_id=skill_id,
        pass_fail=raw.get("pass_fail", "fail"),
        failed_criteria=failed,
        criteria={k: bool(v) for k, v in criteria.items()},
        word_count=raw.get("word_count"),
        eval_score=eval_score,
        raw=raw,
    )

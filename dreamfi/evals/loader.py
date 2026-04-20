"""Deterministic parser for locked eval templates (evals/*.md)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Criterion:
    id: str
    description: str


@dataclass
class TestInput:
    label: str
    text: str


@dataclass
class EvalSpec:
    path: Path
    criteria: list[Criterion] = field(default_factory=list)
    test_inputs: list[TestInput] = field(default_factory=list)


_CRITERION_RE = re.compile(r"^(C\d+):\s*(.+)$")
_INPUT_RE = re.compile(r"^Input\s+(\d+):\s*(.+)$", re.IGNORECASE)


def parse_eval_template(path: str | Path) -> EvalSpec:
    """Parse `## Criteria` and `## Test Inputs` sections."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    sections = _split_sections(text)
    criteria = _parse_criteria(sections.get("criteria", ""))
    test_inputs = _parse_test_inputs(sections.get("test inputs", ""))
    return EvalSpec(path=p, criteria=criteria, test_inputs=test_inputs)


def _split_sections(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current is not None:
                parts[current] = "\n".join(buf).strip()
            current = stripped[3:].strip().lower()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        parts[current] = "\n".join(buf).strip()
    return parts


def _parse_criteria(section: str) -> list[Criterion]:
    out: list[Criterion] = []
    for line in section.splitlines():
        m = _CRITERION_RE.match(line.strip())
        if m:
            out.append(Criterion(id=m.group(1), description=m.group(2).strip()))
    return out


def _parse_test_inputs(section: str) -> list[TestInput]:
    out: list[TestInput] = []
    for line in section.splitlines():
        m = _INPUT_RE.match(line.strip())
        if m:
            label = f"input_{m.group(1)}"
            out.append(TestInput(label=label, text=m.group(2).strip().strip('"')))
    return out

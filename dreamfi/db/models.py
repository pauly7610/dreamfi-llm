from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

GoldRole = Literal["exemplar", "regression", "counter_example", "canary"]
ResultStatus = Literal["pass", "fail"]


@dataclass
class GoldExample:
    gold_id: str
    workspace_id: str
    skill_id: str
    role: GoldRole = "exemplar"
    expected_pass_criteria: dict = field(default_factory=dict)
    last_run_round_id: str | None = None
    last_result: ResultStatus | None = None


@dataclass
class GoldDriftEvent:
    event_id: str
    workspace_id: str
    skill_id: str
    gold_id: str
    prompt_version_id: str
    previous_result: ResultStatus
    new_result: ResultStatus
    round_id: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

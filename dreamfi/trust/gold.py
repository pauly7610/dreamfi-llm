from __future__ import annotations

from collections.abc import Mapping, Sequence
import uuid

from dreamfi.db.models import GoldDriftEvent, GoldExample


def detect_drift_events(
    *,
    examples: Sequence[GoldExample],
    previous_results: Mapping[str, str],
    new_results: Mapping[str, str],
    prompt_version_id: str,
    round_id: str,
) -> list[GoldDriftEvent]:
    """Emit a drift event for any regression/canary pass->fail transition."""
    events: list[GoldDriftEvent] = []

    for example in examples:
        if example.role not in {"regression", "canary"}:
            continue

        prev = previous_results.get(example.gold_id)
        new = new_results.get(example.gold_id)
        if prev is None or new is None:
            continue

        if prev == "pass" and new == "fail":
            events.append(
                GoldDriftEvent(
                    event_id=str(uuid.uuid4()),
                    workspace_id=example.workspace_id,
                    skill_id=example.skill_id,
                    gold_id=example.gold_id,
                    prompt_version_id=prompt_version_id,
                    previous_result="pass",
                    new_result="fail",
                    round_id=round_id,
                )
            )

    return events

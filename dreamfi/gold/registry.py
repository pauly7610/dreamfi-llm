"""Gold example registry backed by the DreamFi DB."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.db.models import GoldExample


@dataclass
class GoldEntry:
    gold_id: str
    skill_id: str
    scenario_type: str
    input_context: dict[str, Any]
    output_text: str


class GoldExampleRegistry:
    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        *,
        skill_id: str,
        scenario_type: str,
        input_context: dict[str, Any],
        output_text: str,
        prompt_version_id: str,
        eval_passed: bool,
    ) -> GoldEntry | None:
        if not eval_passed:
            return None
        row = GoldExample(
            skill_id=skill_id,
            scenario_type=scenario_type,
            input_context_json=input_context,
            output_text=output_text,
            prompt_version_id=prompt_version_id,
        )
        self.session.add(row)
        self.session.commit()
        return GoldEntry(
            gold_id=row.gold_id,
            skill_id=skill_id,
            scenario_type=scenario_type,
            input_context=input_context,
            output_text=output_text,
        )

    def fetch(
        self,
        *,
        skill_id: str,
        scenario_type: str | None = None,
        limit: int = 3,
    ) -> list[GoldEntry]:
        stmt = select(GoldExample).where(GoldExample.skill_id == skill_id)
        if scenario_type:
            stmt = stmt.where(GoldExample.scenario_type == scenario_type)
        stmt = stmt.order_by(GoldExample.captured_at.desc()).limit(limit)
        rows = self.session.scalars(stmt).all()
        return [
            GoldEntry(
                gold_id=r.gold_id,
                skill_id=r.skill_id,
                scenario_type=r.scenario_type,
                input_context=r.input_context_json,
                output_text=r.output_text,
            )
            for r in rows
        ]

    def render_fewshot(
        self,
        *,
        skill_id: str,
        scenario_type: str | None = None,
        num_examples: int = 2,
    ) -> str:
        entries = self.fetch(
            skill_id=skill_id, scenario_type=scenario_type, limit=num_examples
        )
        if not entries:
            return ""
        blocks = []
        for idx, entry in enumerate(entries, start=1):
            blocks.append(
                f"Example (gold) {idx} — scenario={entry.scenario_type}\n"
                f"Output:\n{entry.output_text}\n"
            )
        return "\n".join(blocks)

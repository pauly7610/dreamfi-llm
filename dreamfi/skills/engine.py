"""Generation orchestration: prompt → Onyx chat → eval → confidence → persist."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.confidence.scorer import ConfidenceResult, ConfidenceScorer
from dreamfi.config import get_settings
from dreamfi.db.models import EvalOutput, GoldExample, PromptVersion, Skill
from dreamfi.evals.runner import EvalResult, run_eval
from dreamfi.gold.registry import GoldExampleRegistry
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.models import ChatResult
from dreamfi.trust.artifact import (
    ExportReadinessInput,
    ExportReadinessScore,
    compute_export_readiness,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_FILE_BY_SKILL = {
    "meeting_summary": "meeting_summary.jinja",
    "cold_email": "cold_email.jinja",
    "landing_page_copy": "landing_page_copy.jinja",
    "newsletter_headline": "newsletter_headline.jinja",
    "product_description": "product_description.jinja",
    "resume_bullet": "resume_bullet.jinja",
    "short_form_script": "short_form_script.jinja",
    "agent_system_prompt": "agent_system_prompt.jinja",
    "support_agent": "support_agent.jinja",
}


@dataclass
class GenerationResult:
    output_id: str
    generated_text: str
    eval: EvalResult
    confidence: ConfidenceResult
    onyx_chat_session_id: str | None
    onyx_message_id: int | None
    onyx_citations: dict[int, str]
    export_readiness: ExportReadinessScore | None = None


class SkillEngine:
    def __init__(
        self,
        *,
        db: Session,
        onyx: OnyxClient,
        gold: GoldExampleRegistry | None = None,
        scorer: ConfidenceScorer | None = None,
    ) -> None:
        self.db = db
        self.onyx = onyx
        self.gold = gold or GoldExampleRegistry(db)
        self.scorer = scorer or ConfidenceScorer(
            freshness_halflife_days=get_settings().dreamfi_freshness_halflife_days
        )
        self._jinja = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _persona_id(self, skill_id: str) -> int:
        skill = self.db.get(Skill, skill_id)
        if skill is None or skill.onyx_persona_id is None:
            raise RuntimeError(f"Skill {skill_id} has no onyx_persona_id (run `make seed`).")
        return skill.onyx_persona_id

    def _active_prompt(self, skill_id: str) -> PromptVersion:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True))
            .limit(1)
        )
        pv = self.db.scalar(stmt)
        if pv is None:
            raise RuntimeError(f"No active prompt version for skill {skill_id}")
        return pv

    def _prompt_version(
        self, skill_id: str, *, prompt_version_id: str | None = None
    ) -> PromptVersion:
        if prompt_version_id is None:
            return self._active_prompt(skill_id)
        pv = self.db.get(PromptVersion, prompt_version_id)
        if pv is None or pv.skill_id != skill_id:
            raise RuntimeError(
                f"Prompt version {prompt_version_id} not found for skill {skill_id}"
            )
        return pv

    def _render_prompt(
        self,
        skill_id: str,
        input_context: dict[str, Any] | str,
        *,
        prompt_version: PromptVersion | None = None,
        include_gold: bool = True,
        scenario_type: str | None = None,
    ) -> str:
        pv = prompt_version or self._active_prompt(skill_id)
        gold = ""
        if include_gold:
            gold = self.gold.render_fewshot(
                skill_id=skill_id, scenario_type=scenario_type, num_examples=2
            )
        template_name = pv.template.strip()
        template_path = PROMPTS_DIR / template_name
        if template_name and template_path.exists():
            template = self._jinja.get_template(template_name)
        elif template_name and ("{{" in template_name or "{%" in template_name or "\n" in template_name):
            template = self._jinja.from_string(template_name)
        else:
            template = self._jinja.get_template(PROMPT_FILE_BY_SKILL[skill_id])
        rendered = template.render(input_context=input_context, gold_examples=gold)
        system_prompt = pv.system_prompt.strip()
        if not system_prompt:
            return rendered
        return f"{system_prompt}\n\n{rendered}"

    def _regression_pass_rate(self, skill_id: str) -> float | None:
        """Pass rate across this skill's regression gold examples.

        Returns None when the skill has no scored regression examples; in that
        case we cannot compute an export readiness score and must fall back to
        NULL (blocking publish by policy).
        """
        stmt = select(GoldExample).where(
            GoldExample.skill_id == skill_id,
            GoldExample.role == "regression",
        )
        rows = list(self.db.scalars(stmt))
        scored = [r for r in rows if r.last_result in {"pass", "fail"}]
        if not scored:
            return None
        passes = sum(1 for r in scored if r.last_result == "pass")
        return passes / len(scored)

    def _export_readiness(
        self,
        *,
        skill_id: str,
        eval_result: EvalResult,
        conf: ConfidenceResult,
    ) -> ExportReadinessScore | None:
        hard_gate_pass = eval_result.pass_fail == "pass"
        # Claim lineage proxy: Onyx citations are our only provenance signal today.
        claim_lineage_rate = 1.0 if conf.citation_count > 0 else 0.0

        if not hard_gate_pass:
            # Deterministic short-circuit: hard-gate fail → readiness 0.0.
            return compute_export_readiness(
                ExportReadinessInput(
                    hard_gate_pass=False,
                    confidence=conf.confidence,
                    gold_regression_pass_rate=0.0,
                    claim_lineage_rate=claim_lineage_rate,
                    metric_freshness=conf.freshness_score,
                    planning_hygiene_score=None,
                )
            )

        regression_rate = self._regression_pass_rate(skill_id)
        if regression_rate is None:
            # Missing input → cannot certify; persist NULL (guard will refuse).
            return None

        return compute_export_readiness(
            ExportReadinessInput(
                hard_gate_pass=True,
                confidence=conf.confidence,
                gold_regression_pass_rate=regression_rate,
                claim_lineage_rate=claim_lineage_rate,
                metric_freshness=conf.freshness_score,
                planning_hygiene_score=None,
            )
        )

    def _freshness_from_chat(self, chat: ChatResult) -> float:
        updated_ats = []
        for doc in chat.documents:
            u = doc.get("updated_at")
            if u is None:
                continue
            try:
                from datetime import datetime

                if isinstance(u, str):
                    updated_ats.append(datetime.fromisoformat(u.replace("Z", "+00:00")))
                elif isinstance(u, datetime):
                    updated_ats.append(u)
            except ValueError:
                continue
        return self.scorer.freshness_from_updated_at(updated_ats)

    def generate(
        self,
        *,
        skill: str,
        input_context: dict[str, Any] | str,
        test_input_label: str,
        prompt_version_id: str | None = None,
        round_id: str | None = None,
        attempt: int = 1,
        scenario_type: str | None = None,
    ) -> GenerationResult:
        prompt_version = self._prompt_version(skill, prompt_version_id=prompt_version_id)
        rendered = self._render_prompt(
            skill,
            input_context,
            prompt_version=prompt_version,
            scenario_type=scenario_type,
        )
        session = self.onyx.create_chat_session(
            persona_id=self._persona_id(skill),
            description=f"dreamfi:{skill}:{test_input_label}",
        )
        chat = self.onyx.send_message_sync(
            chat_session_id=session.id,
            parent_message_id=None,
            message=rendered,
        )

        eval_result = run_eval(skill, chat.text, test_input_label)
        freshness = self._freshness_from_chat(chat)
        conf = self.scorer.score(
            eval_score=eval_result.eval_score,
            freshness_score=freshness,
            citation_count=len(chat.citations),
            hard_gate_passed=eval_result.pass_fail == "pass",
        )

        readiness = self._export_readiness(
            skill_id=skill, eval_result=eval_result, conf=conf
        )

        # Persist (only if a round is provided — eval rounds own aggregation)
        output_id: str | None = None
        if round_id is not None:
            row = EvalOutput(
                round_id=round_id,
                test_input_label=test_input_label,
                attempt=attempt,
                generated_text=chat.text,
                criteria_json=eval_result.criteria,
                pass_fail=eval_result.pass_fail,
                onyx_chat_session_id=session.id,
                onyx_message_id=chat.message_id,
                onyx_citations_json={str(k): v for k, v in chat.citations.items()},
                freshness_score=conf.freshness_score,
                confidence=conf.confidence,
                export_readiness=(None if readiness is None else readiness.value),
                export_breakdown_json=(
                    None if readiness is None else dict(readiness.breakdown)
                ),
            )
            self.db.add(row)
            self.db.flush()
            output_id = row.output_id

        return GenerationResult(
            output_id=output_id or "",
            generated_text=chat.text,
            eval=eval_result,
            confidence=conf,
            onyx_chat_session_id=session.id,
            onyx_message_id=chat.message_id,
            onyx_citations=chat.citations,
            export_readiness=readiness,
        )

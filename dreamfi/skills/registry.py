"""Skill registry — maps the 9 locked skills to their templates + runners."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from dreamfi.db.models import Skill
from dreamfi.evals.loader import parse_eval_template


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    display_name: str
    description: str
    eval_template_path: str
    eval_runner_path: str
    runner_module: str
    runner_class: str


# Source of truth: the 9 locked skills.
SKILLS: tuple[SkillSpec, ...] = (
    SkillSpec(
        "meeting_summary",
        "Meeting Summary",
        "Generates meeting summaries with decisions, action items, open questions.",
        "evals/meeting-summary.md",
        "evals/runners/run_meeting_summary_eval.py",
        "evals.runners.run_meeting_summary_eval",
        "MeetingSummaryEval",
    ),
    SkillSpec(
        "cold_email",
        "Cold Email",
        "Generates short, specific cold outreach emails.",
        "evals/cold-email.md",
        "evals/runners/run_cold_email_eval.py",
        "evals.runners.run_cold_email_eval",
        "ColdEmailEval",
    ),
    SkillSpec(
        "landing_page_copy",
        "Landing Page Copy",
        "Generates landing page hero + body copy.",
        "evals/landing-page-copy.md",
        "evals/runners/run_landing_page_eval.py",
        "evals.runners.run_landing_page_eval",
        "LandingPageCopyEval",
    ),
    SkillSpec(
        "newsletter_headline",
        "Newsletter Headline",
        "Generates newsletter headlines with a specific hook.",
        "evals/newsletter-headline.md",
        "evals/runners/run_newsletter_headline_eval.py",
        "evals.runners.run_newsletter_headline_eval",
        "NewsletterHeadlineEval",
    ),
    SkillSpec(
        "product_description",
        "Product Description",
        "Generates product descriptions with benefit + spec.",
        "evals/product-description.md",
        "evals/runners/run_product_description_eval.py",
        "evals.runners.run_product_description_eval",
        "ProductDescriptionEval",
    ),
    SkillSpec(
        "resume_bullet",
        "Resume Bullet",
        "Generates resume bullets with metric + outcome.",
        "evals/resume-bullet.md",
        "evals/runners/run_resume_bullet_eval.py",
        "evals.runners.run_resume_bullet_eval",
        "ResumeBulletEval",
    ),
    SkillSpec(
        "short_form_script",
        "Short-form Script",
        "Generates short-form video scripts with hook + CTA.",
        "evals/short-form-script.md",
        "evals/runners/run_short_form_script_eval.py",
        "evals.runners.run_short_form_script_eval",
        "ShortFormScriptEval",
    ),
    SkillSpec(
        "agent_system_prompt",
        "Agent System Prompt",
        "Generates robust agent system prompts.",
        "evals/agent-system-prompt.md",
        "evals/runners/run_agent_system_prompt_eval.py",
        "evals.runners.run_agent_system_prompt_eval",
        "AgentSystemPromptEval",
    ),
    SkillSpec(
        "support_agent",
        "Support Agent",
        "Generates support-agent replies with empathy + resolution.",
        "evals/support-agent.md",
        "evals/runners/run_support_agent_eval.py",
        "evals.runners.run_support_agent_eval",
        "SupportAgentEval",
    ),
)


def load_registry() -> dict[str, SkillSpec]:
    return {s.skill_id: s for s in SKILLS}


def seed_registry(session: Session, repo_root: Path | None = None) -> int:
    """Idempotently upsert all 9 skills into the `skills` table.

    Returns the count of skills after seeding.
    """
    root = repo_root or Path.cwd()
    for spec in SKILLS:
        template_path = root / spec.eval_template_path
        runner_path = root / spec.eval_runner_path
        if not template_path.exists():
            raise FileNotFoundError(template_path)
        if not runner_path.exists():
            raise FileNotFoundError(runner_path)
        eval_spec = parse_eval_template(template_path)
        criteria_json = {c.id: c.description for c in eval_spec.criteria}
        existing = session.get(Skill, spec.skill_id)
        if existing is None:
            session.add(
                Skill(
                    skill_id=spec.skill_id,
                    display_name=spec.display_name,
                    description=spec.description,
                    eval_template_path=spec.eval_template_path,
                    eval_runner_path=spec.eval_runner_path,
                    criteria_json=criteria_json,
                )
            )
        else:
            existing.display_name = spec.display_name
            existing.description = spec.description
            existing.eval_template_path = spec.eval_template_path
            existing.eval_runner_path = spec.eval_runner_path
            existing.criteria_json = criteria_json
    session.commit()
    return session.query(Skill).count()

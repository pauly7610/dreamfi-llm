"""Seed Onyx with one document-set + persona per DreamFi skill.

Requires ONYX_BASE_URL and an admin ONYX_API_KEY.
"""
from __future__ import annotations

import sys

import click
from sqlalchemy import func, select

from dreamfi.api.deps import get_onyx_client
from dreamfi.connectors import CONNECTORS
from dreamfi.db.models import PromptVersion, Skill
from dreamfi.db.session import get_sessionmaker
from dreamfi.onyx.errors import OnyxError
from dreamfi.skills.engine import PROMPTS_DIR, PROMPT_FILE_BY_SKILL
from dreamfi.skills.registry import SKILLS, seed_registry


def _ensure_active_prompt_version(session, *, skill_id: str, template: str) -> None:
    active = session.scalar(
        select(PromptVersion)
        .where(PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True))
        .limit(1)
    )
    if active is not None:
        return

    latest_version = session.scalar(
        select(func.max(PromptVersion.version)).where(PromptVersion.skill_id == skill_id)
    ) or 0
    session.add(
        PromptVersion(
            skill_id=skill_id,
            version=int(latest_version) + 1,
            template=template,
            system_prompt="",
            is_active=True,
        )
    )


@click.command()
def main() -> None:
    session = get_sessionmaker()()
    onyx = get_onyx_client()
    try:
        seed_registry(session)
        try:
            doc_sets = onyx.list_document_sets()
        except OnyxError as e:
            click.echo(f"Could not list Onyx doc-sets: {e}", err=True)
            sys.exit(1)
        doc_sets_by_name = {d.name: d for d in doc_sets}
        personas = onyx.list_personas()
        personas_by_name = {p.name: p for p in personas}
        for connector in CONNECTORS:
            if connector.expected_document_set in doc_sets_by_name:
                click.echo(
                    f"connector={connector.connector_id} doc_set={connector.expected_document_set} exists"
                )
                continue
            created = onyx.create_document_set(
                name=connector.expected_document_set,
                description=f"DreamFi source evidence for {connector.name}",
            )
            doc_sets_by_name[connector.expected_document_set] = created
            click.echo(
                f"connector={connector.connector_id} doc_set={connector.expected_document_set} doc_set_id={created.id}"
            )
        for spec in SKILLS:
            ds_name = f"dreamfi-{spec.skill_id}"
            ds = doc_sets_by_name.get(ds_name)
            if ds is None:
                ds = onyx.create_document_set(
                    name=ds_name, description=f"Docs for {spec.display_name}"
                )
            system_prompt = (PROMPTS_DIR / PROMPT_FILE_BY_SKILL[spec.skill_id]).read_text(
                encoding="utf-8"
            )
            persona_name = f"DreamFi {spec.display_name}"
            persona = personas_by_name.get(persona_name)
            persona_fields = {
                "description": spec.description,
                "system_prompt": system_prompt,
                "document_set_ids": [ds.id],
                "tool_ids": [1],
            }
            if persona is None:
                persona = onyx.create_persona(
                    name=persona_name,
                    **persona_fields,
                )
                personas_by_name[persona_name] = persona
            else:
                persona = onyx.update_persona(persona.id, **persona_fields)
            skill = session.get(Skill, spec.skill_id)
            if skill is not None:
                skill.onyx_persona_id = persona.id
            _ensure_active_prompt_version(
                session,
                skill_id=spec.skill_id,
                template=PROMPT_FILE_BY_SKILL[spec.skill_id],
            )
            click.echo(
                f"skill={spec.skill_id} persona_id={persona.id} doc_set_id={ds.id}"
            )
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()

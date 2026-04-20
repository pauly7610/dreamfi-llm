"""Seed Onyx with one document-set + persona per DreamFi skill.

Requires ONYX_BASE_URL and an admin ONYX_API_KEY.
"""
from __future__ import annotations

import sys

import click

from dreamfi.api.deps import get_onyx_client
from dreamfi.db.models import Skill
from dreamfi.db.session import get_sessionmaker
from dreamfi.onyx.errors import OnyxError
from dreamfi.skills.engine import PROMPTS_DIR, PROMPT_FILE_BY_SKILL
from dreamfi.skills.registry import SKILLS, seed_registry


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
            persona = onyx.create_persona(
                name=f"DreamFi {spec.display_name}",
                description=spec.description,
                system_prompt=system_prompt,
                document_set_ids=[ds.id],
                tool_ids=[1],
            )
            skill = session.get(Skill, spec.skill_id)
            if skill is not None:
                skill.onyx_persona_id = persona.id
            click.echo(
                f"skill={spec.skill_id} persona_id={persona.id} doc_set_id={ds.id}"
            )
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()

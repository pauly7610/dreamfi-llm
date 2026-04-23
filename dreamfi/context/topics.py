"""C5 — Topic Graph: canonical topic resolution and upsert helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.context.bundle import ContextBundle
from dreamfi.db.models import TopicAliasRow, TopicRelationRow, TopicRow

TopicType = Literal[
    "epic", "issue", "doc", "metric", "person", "squad", "release", "experiment",
    "generic",
]


@dataclass(frozen=True)
class TopicResolution:
    topic_id: str
    canonical_name: str
    type: str
    is_new: bool


_ALIAS_STRIP = re.compile(r"[^a-z0-9]+")


def normalize_alias(text: str) -> str:
    """Cheap slug: lowercase, strip punctuation, collapse whitespace.

    Good enough to make "activation", "the activation squad" and "act squad"
    share a resolution. Anything more intelligent belongs in the builder.
    """
    lowered = text.strip().lower()
    # Drop leading articles.
    for prefix in ("the ", "a ", "an "):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix):]
    slug = _ALIAS_STRIP.sub("-", lowered).strip("-")
    # Drop trailing stop-words that add no signal.
    parts = [p for p in slug.split("-") if p and p not in {"squad", "team", "group"}]
    return "-".join(parts) or slug


@dataclass(frozen=True)
class TopicHint:
    epic_key: str | None = None
    squad: str | None = None
    type: TopicType | None = None
    time_window_days: int | None = None


def resolve_topic(
    session: Session,
    *,
    workspace_id: str,
    question: str,
    hint: TopicHint | None = None,
    create_if_missing: bool = True,
) -> TopicResolution:
    """Return the canonical topic id for a natural-language question.

    Resolution order:
    1. If the hint supplies an ``epic_key``, look up (or create) a topic of
       type ``epic`` with that canonical name.
    2. Otherwise normalize the question + hint text into an alias slug and
       look that up in ``topic_aliases``.
    3. Falling back, create a new generic topic with the alias attached.
    """
    if hint is not None and hint.epic_key:
        existing = session.scalar(
            select(TopicRow).where(
                TopicRow.workspace_id == workspace_id,
                TopicRow.type == "epic",
                TopicRow.canonical_name == hint.epic_key,
            )
        )
        if existing is not None:
            return TopicResolution(
                topic_id=existing.topic_id,
                canonical_name=existing.canonical_name,
                type=existing.type,
                is_new=False,
            )
        if not create_if_missing:
            raise LookupError(f"no topic for epic_key={hint.epic_key}")
        row = TopicRow(
            workspace_id=workspace_id,
            type="epic",
            canonical_name=hint.epic_key,
            attributes_json={},
        )
        session.add(row)
        session.flush()
        session.add(
            TopicAliasRow(
                workspace_id=workspace_id,
                topic_id=row.topic_id,
                alias=hint.epic_key,
                alias_norm=normalize_alias(hint.epic_key),
            )
        )
        session.commit()
        return TopicResolution(
            topic_id=row.topic_id,
            canonical_name=row.canonical_name,
            type="epic",
            is_new=True,
        )

    alias_seed = question if hint is None or not hint.squad else f"{hint.squad} {question}"
    alias_norm = normalize_alias(alias_seed)
    hit = session.scalar(
        select(TopicAliasRow).where(
            TopicAliasRow.workspace_id == workspace_id,
            TopicAliasRow.alias_norm == alias_norm,
        )
    )
    if hit is not None:
        topic = session.get(TopicRow, hit.topic_id)
        if topic is not None:
            return TopicResolution(
                topic_id=topic.topic_id,
                canonical_name=topic.canonical_name,
                type=topic.type,
                is_new=False,
            )

    if not create_if_missing:
        raise LookupError(f"no topic for alias={alias_norm}")

    topic_type: str = (hint.type if hint and hint.type else "generic")
    canonical = (hint.squad if hint and hint.squad else None) or question.strip().title()
    row = TopicRow(
        workspace_id=workspace_id,
        type=topic_type,
        canonical_name=canonical,
        attributes_json={},
    )
    session.add(row)
    session.flush()
    session.add(
        TopicAliasRow(
            workspace_id=workspace_id,
            topic_id=row.topic_id,
            alias=alias_seed,
            alias_norm=alias_norm,
        )
    )
    session.commit()
    return TopicResolution(
        topic_id=row.topic_id,
        canonical_name=row.canonical_name,
        type=topic_type,
        is_new=True,
    )


def add_alias(
    session: Session, *, workspace_id: str, topic_id: str, alias: str
) -> None:
    """Attach a new alias to an existing topic, idempotently."""
    norm = normalize_alias(alias)
    existing = session.scalar(
        select(TopicAliasRow).where(
            TopicAliasRow.workspace_id == workspace_id,
            TopicAliasRow.alias_norm == norm,
        )
    )
    if existing is not None:
        return
    session.add(
        TopicAliasRow(
            workspace_id=workspace_id,
            topic_id=topic_id,
            alias=alias,
            alias_norm=norm,
        )
    )
    session.commit()


def link_entities(
    session: Session, *, bundle: ContextBundle, topic_id: str
) -> list[TopicRelationRow]:
    """Upsert the bundle's entities as nodes and add edges from ``topic_id``.

    Each entity becomes a TopicRow (by type + canonical_name), and a
    ``related_to`` edge is written from the source topic. Called after
    every bundle build (per the C5 spec).
    """
    emitted: list[TopicRelationRow] = []
    for entity in bundle.entities:
        existing = session.scalar(
            select(TopicRow).where(
                TopicRow.workspace_id == bundle.workspace_id,
                TopicRow.type == entity.entity_type,
                TopicRow.canonical_name == entity.canonical_name,
            )
        )
        if existing is None:
            node = TopicRow(
                workspace_id=bundle.workspace_id,
                type=entity.entity_type,
                canonical_name=entity.canonical_name,
                attributes_json={"entity_id": entity.entity_id},
            )
            session.add(node)
            session.flush()
        else:
            node = existing

        # Dedup: skip edge if one exists with same from/to/type.
        edge_exists = session.scalar(
            select(TopicRelationRow).where(
                TopicRelationRow.from_id == topic_id,
                TopicRelationRow.to_id == node.topic_id,
                TopicRelationRow.relation_type == "related_to",
            )
        )
        if edge_exists is not None:
            continue
        edge = TopicRelationRow(
            from_id=topic_id,
            to_id=node.topic_id,
            relation_type="related_to",
            source_bundle_id=str(bundle.bundle_id),
        )
        session.add(edge)
        emitted.append(edge)

    if emitted:
        session.commit()
    return emitted

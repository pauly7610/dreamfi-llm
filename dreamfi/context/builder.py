"""C3 — ContextBuilder.

Fans out across connectors, normalizes into a ContextBundle, and asks
the model router to distill claims + open questions. Jira and Confluence
are wired first; other connectors are accepted via ``ConnectorRegistry``
but not required to be present.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dreamfi.connectors.confluence import ConfluenceClient
from dreamfi.connectors.jira import JiraClient, fetch_topic_jira
from dreamfi.context.bundle import (
    ContextBundle,
    ContextClaim,
    ContextEntity,
    ContextSource,
    EntityRelation,
    OpenQuestion,
    OpenQuestionReason,
    compute_coverage_score,
)
from dreamfi.context.model_router import (
    ContextStructuringError,
    ModelRouter,
)
from dreamfi.context.topics import (
    TopicHint,
    TopicResolution,
    link_entities,
    normalize_alias,
    resolve_topic,
)


# ----------------------------------------------------------------------------
# Structured output the model must produce.
# ----------------------------------------------------------------------------


class ClaimDraft(BaseModel):
    statement: str
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.7


class OpenQuestionDraft(BaseModel):
    question: str
    why_open: OpenQuestionReason = "ambiguous"
    suggested_owner: str | None = None


class ClaimDistillation(BaseModel):
    claims: list[ClaimDraft] = Field(default_factory=list)
    open_questions: list[OpenQuestionDraft] = Field(default_factory=list)


# ----------------------------------------------------------------------------


@dataclass
class ConnectorRegistry:
    """Opt-in connector bag. Only Jira + Confluence are required for C3."""

    jira: JiraClient | None = None
    confluence: ConfluenceClient | None = None

    def available(self) -> list[str]:
        names: list[str] = []
        if self.jira is not None:
            names.append("jira")
        if self.confluence is not None:
            names.append("confluence")
        return names


def _sha(obj: object) -> str:
    return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()[:32]


class ContextBuilder:
    """Assemble a ContextBundle from connector reads + LLM claim distillation."""

    def __init__(
        self,
        *,
        connectors: ConnectorRegistry,
        llm: ModelRouter,
        session: Session | None = None,
    ) -> None:
        self.connectors = connectors
        self.llm = llm
        self.session = session

    # --- public --------------------------------------------------------------

    def build(
        self,
        *,
        workspace_id: str,
        topic: str,
        topic_hint: TopicHint | None = None,
    ) -> ContextBundle:
        now = datetime.now(timezone.utc)

        sources: list[ContextSource] = []
        entities: list[ContextEntity] = []

        # --- Jira fan-out ----------------------------------------------------
        if self.connectors.jira is not None:
            jira_bundle = fetch_topic_jira(
                self.connectors.jira,
                workspace_id=workspace_id,
                topic=topic,
                epic_key=(topic_hint.epic_key if topic_hint else None),
            )
            for issue in jira_bundle.issues:
                sources.append(
                    ContextSource(
                        source_type="jira",
                        source_id=issue.key,
                        fetched_at=now,
                        payload_hash=_sha(
                            (issue.key, issue.status, issue.summary, issue.updated_at)
                        ),
                        raw_ref=f"jira:{issue.key}",
                    )
                )
                rels: list[EntityRelation] = []
                if issue.parent_key:
                    rels.append(
                        EntityRelation(
                            relation_type="child_of", target_entity_id=issue.parent_key
                        )
                    )
                for link in issue.links:
                    rels.append(
                        EntityRelation(
                            relation_type=(
                                "blocked_by" if link.link_type.lower().startswith("block")
                                and link.direction == "inward"
                                else "related_to"
                            ),
                            target_entity_id=link.target_key,
                        )
                    )
                entities.append(
                    ContextEntity(
                        entity_type="issue",
                        entity_id=issue.key,
                        canonical_name=issue.key,
                        relationships=rels,
                    )
                )

        # --- Confluence fan-out ---------------------------------------------
        if self.connectors.confluence is not None and (
            topic_hint is None or topic_hint.epic_key is None
        ):
            # When a Jira epic is the anchor we skip Confluence search; a real
            # builder would run both and dedup by title. C3 keeps it focused.
            try:
                pages = self.connectors.confluence.search(f'text ~ "{topic}"')
            except Exception:  # noqa: BLE001 — connector resilience
                pages = []
            for page in pages:
                sources.append(
                    ContextSource(
                        source_type="confluence",
                        source_id=page.id,
                        fetched_at=now,
                        payload_hash=_sha((page.id, page.title, page.updated_at)),
                        raw_ref=f"confluence:{page.id}",
                    )
                )
                entities.append(
                    ContextEntity(
                        entity_type="doc",
                        entity_id=page.id,
                        canonical_name=page.title,
                        relationships=[],
                    )
                )

        # --- entity dedup by (type, entity_id) ------------------------------
        entities = _dedup_entities(entities)

        # --- freshness signal (every fetched source is "fresh-as-of-now";
        # real staleness detection against raw payloads lives in P12).
        stale_questions: list[OpenQuestion] = []
        freshness = 1.0 if sources else 0.0

        # --- LLM-assisted claim distillation (structured) -------------------
        prompt = _build_distillation_prompt(
            topic=topic, sources=sources, entities=entities
        )
        try:
            distill = self.llm.structured_complete(
                prompt=prompt, schema=ClaimDistillation
            )
        except ContextStructuringError:
            # Never persist a half-built bundle (spec acceptance).
            raise

        claims = [
            ContextClaim(
                statement=c.statement,
                citation_ids=list(c.source_refs),
                confidence=c.confidence,
            )
            for c in distill.claims
        ]
        open_questions: list[OpenQuestion] = [
            OpenQuestion(
                question=q.question,
                why_open=q.why_open,
                suggested_owner=q.suggested_owner,
            )
            for q in distill.open_questions
        ] + stale_questions

        coverage = compute_coverage_score(
            answered_subquestions=len(claims),
            total_subquestions=max(len(claims) + len(open_questions), 1),
        )
        confidence = sum(c.confidence for c in claims) / len(claims) if claims else 0.0

        bundle = ContextBundle(
            workspace_id=workspace_id,
            topic=topic,
            topic_key=normalize_alias(topic),
            created_at=now,
            refreshed_at=now,
            ttl_seconds=3600,
            sources=sources,
            entities=entities,
            claims=claims,
            open_questions=open_questions,
            freshness_score=freshness,
            coverage_score=coverage,
            confidence=confidence,
        )
        return bundle

    def build_and_link(
        self,
        *,
        workspace_id: str,
        topic: str,
        topic_hint: TopicHint | None = None,
    ) -> tuple[ContextBundle, TopicResolution]:
        """Build the bundle and attach its entities to the Topic Graph."""
        if self.session is None:
            raise RuntimeError(
                "ContextBuilder.session is required to link entities"
            )
        bundle = self.build(
            workspace_id=workspace_id, topic=topic, topic_hint=topic_hint
        )
        resolution = resolve_topic(
            self.session,
            workspace_id=workspace_id,
            question=topic,
            hint=topic_hint,
        )
        link_entities(self.session, bundle=bundle, topic_id=resolution.topic_id)
        return bundle, resolution


# ---------------------------------------------------------------------------


def _dedup_entities(entities: list[ContextEntity]) -> list[ContextEntity]:
    seen: dict[tuple[str, str], ContextEntity] = {}
    for e in entities:
        key = (e.entity_type, e.entity_id)
        if key in seen:
            # Merge relationships, unique by (type, target).
            merged = list(seen[key].relationships)
            existing_keys = {(r.relation_type, r.target_entity_id) for r in merged}
            for rel in e.relationships:
                if (rel.relation_type, rel.target_entity_id) not in existing_keys:
                    merged.append(rel)
            seen[key] = e.model_copy(update={"relationships": merged})
        else:
            seen[key] = e
    return list(seen.values())


def _build_distillation_prompt(
    *,
    topic: str,
    sources: list[ContextSource],
    entities: list[ContextEntity],
) -> str:
    lines = [
        f"Topic: {topic}",
        "",
        "Sources:",
    ]
    for s in sources:
        lines.append(f"- [{s.source_type}:{s.source_id}] ({s.raw_ref})")
    lines.append("")
    lines.append("Entities:")
    for e in entities:
        lines.append(f"- {e.entity_type}:{e.entity_id} — {e.canonical_name}")
    lines.append("")
    lines.append(
        "Distill: produce claims citing source refs like 'jira:KEY' or "
        "'confluence:ID'. Every claim must cite >=1 source. Flag open "
        "questions where you lack sources."
    )
    return "\n".join(lines)

"""C7 — tiny Q&A memory with token-overlap similarity.

Embeddings and pgvector are out of scope for the first backend slice; the
spec only asks that if you ask "same question, different words" within the
same workspace, the prior answer surfaces. Token overlap (Jaccard) is good
enough for that and costs nothing at scale < 10k rows per workspace.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.db.models import ContextQuestionRow

_WORD = re.compile(r"[a-zA-Z0-9]+")
_STOP = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
        "and", "or", "of", "on", "in", "to", "for", "with", "what", "who",
        "when", "where", "why", "how", "that", "this", "be", "been", "being",
        "has", "have", "had", "it", "its", "as", "by", "at", "from", "we",
        "our", "i", "you", "me", "my",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric, stop-words removed."""
    return [w for w in (m.group(0).lower() for m in _WORD.finditer(text)) if w not in _STOP]


@dataclass
class MemoryHit:
    question_id: str
    question: str
    answer_excerpt: str
    similarity: float
    topic_id: str | None
    bundle_id: str | None


def record_question(
    session: Session,
    *,
    workspace_id: str,
    question: str,
    answer_excerpt: str,
    asker: str = "",
    topic_id: str | None = None,
    bundle_id: str | None = None,
    private: bool = False,
) -> ContextQuestionRow:
    tokens = tokenize(question)
    row = ContextQuestionRow(
        workspace_id=workspace_id,
        asker=asker,
        question=question,
        question_norm=" ".join(tokens),
        topic_id=topic_id,
        bundle_id=bundle_id,
        answer_excerpt=answer_excerpt[:2000],
        tokens_json=tokens,
        private=private,
    )
    session.add(row)
    session.commit()
    return row


def _jaccard(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union)


def similar_questions(
    session: Session,
    *,
    workspace_id: str,
    question: str,
    threshold: float = 0.5,
    limit: int = 5,
    asker: str | None = None,
) -> list[MemoryHit]:
    """Return memory rows above the similarity threshold, newest first.

    Private rows are only returned when ``asker`` matches the stored
    ``asker`` field — this enforces the private-answer rule from the spec.
    """
    tokens = tokenize(question)
    rows = list(
        session.scalars(
            select(ContextQuestionRow)
            .where(ContextQuestionRow.workspace_id == workspace_id)
            .order_by(ContextQuestionRow.asked_at.desc())
            .limit(500)
        )
    )
    hits: list[MemoryHit] = []
    for row in rows:
        if row.private and (asker is None or row.asker != asker):
            continue
        similarity = _jaccard(tokens, list(row.tokens_json or []))
        if similarity >= threshold:
            hits.append(
                MemoryHit(
                    question_id=row.question_id,
                    question=row.question,
                    answer_excerpt=row.answer_excerpt,
                    similarity=similarity,
                    topic_id=row.topic_id,
                    bundle_id=row.bundle_id,
                )
            )
    hits.sort(key=lambda h: h.similarity, reverse=True)
    return hits[:limit]

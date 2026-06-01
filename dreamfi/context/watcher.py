"""C6 — context watcher: refresh a bundle and diff against its previous version.

The watcher itself is stateless — a caller supplies the previous bundle
(loaded from the ContextBundle store) and the freshly built one; the
watcher emits ``context_changes`` rows for every material difference.

"Material" means:

- **claim_added** — new citable statement not present before.
- **claim_removed** — previously-cited statement no longer supported.
- **source_lost** — a source in the old bundle is absent in the new one.
- **question_resolved** — an open question in the old bundle is gone.

Each caller (scheduler or the Ask endpoint on rebuild) is responsible for
running this; the plan calls it out separately because the scheduler will
live in P-phase (APScheduler / Celery). Unit tests exercise the diff.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from dreamfi.context.bundle import ContextBundle
from dreamfi.db.models import ContextChangeRow

ChangeType = Literal[
    "claim_added", "claim_removed", "source_lost", "question_resolved"
]


@dataclass(frozen=True)
class DetectedChange:
    change_type: ChangeType
    detail: str


def diff_bundles(
    *, previous: ContextBundle | None, current: ContextBundle
) -> list[DetectedChange]:
    if previous is None:
        return []

    prev_claims = {c.statement.strip() for c in previous.claims}
    curr_claims = {c.statement.strip() for c in current.claims}
    prev_sources = {(s.source_type, s.source_id) for s in previous.sources}
    curr_sources = {(s.source_type, s.source_id) for s in current.sources}
    prev_questions = {q.question.strip() for q in previous.open_questions}
    curr_questions = {q.question.strip() for q in current.open_questions}

    changes: list[DetectedChange] = []
    for added in curr_claims - prev_claims:
        changes.append(DetectedChange("claim_added", added))
    for removed in prev_claims - curr_claims:
        changes.append(DetectedChange("claim_removed", removed))
    for missing in prev_sources - curr_sources:
        changes.append(
            DetectedChange("source_lost", f"{missing[0]}:{missing[1]}")
        )
    for resolved in prev_questions - curr_questions:
        changes.append(DetectedChange("question_resolved", resolved))

    return changes


def watch_and_persist(
    session: Session,
    *,
    previous: ContextBundle | None,
    current: ContextBundle,
    topic_id: str | None,
) -> list[ContextChangeRow]:
    """Compute the diff and persist one ``context_changes`` row per event."""
    changes = diff_bundles(previous=previous, current=current)
    if not changes:
        return []
    rows: list[ContextChangeRow] = []
    for ch in changes:
        row = ContextChangeRow(
            workspace_id=current.workspace_id,
            topic_id=topic_id,
            topic_key=current.topic_key,
            change_type=ch.change_type,
            detail=ch.detail,
            old_bundle_id=str(previous.bundle_id) if previous else None,
            new_bundle_id=str(current.bundle_id),
        )
        session.add(row)
        rows.append(row)
    session.commit()
    return rows

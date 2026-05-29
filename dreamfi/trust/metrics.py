"""T2' / T3' — metric catalog, snapshot capture, and lineage/discrepancy.

The catalog is the registry of every metric DreamFi is willing to quote.
Snapshots record "X = 82 as of 2026-04-20 via PostHog"; the discrepancy
checker flags claims whose numbers disagree with the latest snapshot or
are missing a catalog entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.context.bundle import ContextClaim
from dreamfi.db.models import MetricCatalogRow, MetricSnapshotRow


@dataclass(frozen=True)
class MetricLineageIssue:
    metric_id: str
    severity: str  # "error" | "warning"
    message: str


def upsert_metric(
    session: Session,
    *,
    workspace_id: str,
    metric_id: str,
    display_name: str,
    definition: str = "",
    owner: str | None = None,
    source_systems: Iterable[str] = (),
) -> MetricCatalogRow:
    existing = session.scalar(
        select(MetricCatalogRow).where(
            MetricCatalogRow.workspace_id == workspace_id,
            MetricCatalogRow.metric_id == metric_id,
        )
    )
    if existing is not None:
        existing.display_name = display_name
        existing.definition = definition
        existing.owner = owner
        existing.source_systems_json = list(source_systems)
        session.commit()
        return existing

    row = MetricCatalogRow(
        workspace_id=workspace_id,
        metric_id=metric_id,
        display_name=display_name,
        definition=definition,
        owner=owner,
        source_systems_json=list(source_systems),
    )
    session.add(row)
    session.commit()
    return row


def record_snapshot(
    session: Session,
    *,
    workspace_id: str,
    metric_id: str,
    source_system: str,
    as_of_date: datetime,
    value: Decimal | float,
) -> MetricSnapshotRow:
    row = MetricSnapshotRow(
        workspace_id=workspace_id,
        metric_id=metric_id,
        source_system=source_system,
        as_of_date=as_of_date,
        value=Decimal(str(value)),
    )
    session.add(row)
    session.commit()
    return row


def latest_snapshot(
    session: Session, *, workspace_id: str, metric_id: str
) -> MetricSnapshotRow | None:
    return session.scalar(
        select(MetricSnapshotRow)
        .where(
            MetricSnapshotRow.workspace_id == workspace_id,
            MetricSnapshotRow.metric_id == metric_id,
        )
        .order_by(MetricSnapshotRow.as_of_date.desc())
        .limit(1)
    )


def find_discrepancies(
    session: Session,
    *,
    workspace_id: str,
    claims: list[ContextClaim],
    metric_ids_in_claims: dict[str, list[str]],
    tolerance: Decimal = Decimal("0.01"),
) -> list[MetricLineageIssue]:
    """Compare claims that cite metric IDs against the latest snapshot.

    ``metric_ids_in_claims`` is ``{claim_id -> [metric_id, ...]}`` because
    we don't do NLP to extract metric references here; the builder wires
    them up. Any metric referenced by a claim without a catalog entry is
    a lineage error; mismatches with the latest snapshot are warnings.
    """
    issues: list[MetricLineageIssue] = []
    for claim in claims:
        ids = metric_ids_in_claims.get(str(claim.claim_id), [])
        for metric_id in ids:
            catalog = session.scalar(
                select(MetricCatalogRow).where(
                    MetricCatalogRow.workspace_id == workspace_id,
                    MetricCatalogRow.metric_id == metric_id,
                )
            )
            if catalog is None:
                issues.append(
                    MetricLineageIssue(
                        metric_id=metric_id,
                        severity="error",
                        message=(
                            f"claim cites metric '{metric_id}' which is not "
                            "in the workspace's metric catalog"
                        ),
                    )
                )
                continue
            # If a claim carries a numeric sot-of-truth, compare. We
            # expose a simple ``sot_value`` convention: the claim's
            # ``sot_id`` carries ``metric_id=<id>;value=<n>`` when the
            # builder attached one.
            if claim.sot_id and f"metric_id={metric_id}" in claim.sot_id:
                try:
                    claim_val = Decimal(
                        claim.sot_id.split("value=", 1)[1].split(";", 1)[0]
                    )
                except (IndexError, ValueError):
                    continue
                snap = latest_snapshot(
                    session, workspace_id=workspace_id, metric_id=metric_id
                )
                if snap is None:
                    continue
                if abs(snap.value - claim_val) > tolerance:
                    issues.append(
                        MetricLineageIssue(
                            metric_id=metric_id,
                            severity="warning",
                            message=(
                                f"claim says {claim_val} but latest snapshot "
                                f"({snap.source_system} @ {snap.as_of_date.isoformat()})"
                                f" says {snap.value}"
                            ),
                        )
                    )
    return issues

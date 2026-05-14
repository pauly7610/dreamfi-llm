"""DreamFi API-key-ready setup and operations CLI."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import click
from sqlalchemy import select

from dreamfi.api.deps import get_onyx_client
from dreamfi.connectors import CONNECTOR_BY_ID
from dreamfi.connector_sync import sync_connector
from dreamfi.db.models import ReplaySchedule
from dreamfi.db.session import get_sessionmaker
from dreamfi.learning.loop import run_replay_schedule
from dreamfi.ops.backups import write_database_snapshot
from dreamfi.ops.demo import ensure_active_prompts, seed_demo_data
from dreamfi.ops.readiness import (
    bootstrap_connector_document_sets,
    connector_readiness,
    environment_readiness,
    ops_status,
)


def _echo_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


@click.group()
def main() -> None:
    """Prepare DreamFi so live setup mostly requires API keys."""


@main.command("env-check")
@click.option("--strict", is_flag=True, help="Exit non-zero when required values are missing.")
def env_check(strict: bool) -> None:
    """Validate production-critical environment settings."""
    payload = environment_readiness()
    _echo_json(payload)
    if strict and not payload["ready"]:
        raise click.ClickException("environment is not ready")


@main.command("seed-local")
def seed_local() -> None:
    """Seed DreamFi skills and active prompt versions without live Onyx calls."""
    session = get_sessionmaker()()
    try:
        ensure_active_prompts(session)
        session.commit()
        click.echo("seeded skills and active prompt versions")
    finally:
        session.close()


@main.command("seed-demo")
def seed_demo() -> None:
    """Seed realistic demo topics, artifacts, feedback, outcomes, and replay state."""
    session = get_sessionmaker()()
    try:
        payload = seed_demo_data(session)
        _echo_json(payload)
    finally:
        session.close()


@main.command("bootstrap-docsets")
@click.option("--apply", is_flag=True, help="Create missing expected Onyx document sets.")
def bootstrap_docsets(apply: bool) -> None:
    """Create or dry-run expected source connector document sets in Onyx."""
    onyx = get_onyx_client()
    rows = bootstrap_connector_document_sets(onyx=onyx, apply=apply)
    _echo_json({"applied": apply, "document_sets": rows})


@main.command("validate-connectors")
@click.option("--skip-probe", is_flag=True, help="Only validate document-set presence.")
@click.option("--strict", is_flag=True, help="Exit non-zero on missing/degraded connectors.")
def validate_connectors(skip_probe: bool, strict: bool) -> None:
    """Validate source connector document sets and retrieval freshness."""
    onyx = get_onyx_client()
    payload = connector_readiness(onyx=onyx, probe_search=not skip_probe)
    _echo_json(payload)
    counts = payload.get("counts", {})
    if strict and (
        payload.get("status") != "ok"
        or counts.get("not_configured")
        or counts.get("degraded")
    ):
        raise click.ClickException("connectors are not ready")


@main.command("sync-connector")
@click.argument("connector_id")
@click.option("--limit", default=None, type=click.IntRange(1, 500))
def sync_connector_command(connector_id: str, limit: int | None) -> None:
    """Run one custom connector pull and ingest changed documents into Onyx."""
    connector = CONNECTOR_BY_ID.get(connector_id.strip().lower())
    if connector is None:
        raise click.ClickException(f"unknown connector: {connector_id}")
    session = get_sessionmaker()()
    onyx = get_onyx_client()
    try:
        run = sync_connector(
            session=session,
            onyx=onyx,
            connector=connector,
            actor_id="cli",
            trigger="cli",
            limit=limit,
        )
        session.commit()
        _echo_json(
            {
                "sync_run_id": run.sync_run_id,
                "connector_id": run.connector_id,
                "status": run.status,
                "pulled_count": run.pulled_count,
                "persisted_count": run.persisted_count,
                "ingested_count": run.ingested_count,
                "skipped_count": run.skipped_count,
                "error_count": run.error_count,
                "reason": run.reason,
            }
        )
        if run.status != "success":
            raise click.ClickException(run.reason or "connector sync failed")
    finally:
        session.close()


@main.command("run-replay")
@click.option("--limit", default=10, show_default=True, type=click.IntRange(1, 50))
def run_replay(limit: int) -> None:
    """Run due gold, workflow, and source-refresh schedules."""
    session = get_sessionmaker()()
    onyx = get_onyx_client()
    try:
        now = datetime.now(timezone.utc)
        schedules = session.scalars(
            select(ReplaySchedule)
            .where(
                ReplaySchedule.is_active.is_(True),
                ReplaySchedule.next_run_at <= now,
            )
            .order_by(ReplaySchedule.next_run_at)
            .limit(limit)
        ).all()
        runs = [
            run_replay_schedule(session, schedule=schedule, onyx=onyx)
            for schedule in schedules
        ]
        session.commit()
        _echo_json(
            {
                "schedule_count": len(schedules),
                "runs": [
                    {
                        "replay_run_id": run.replay_run_id,
                        "schedule_id": run.schedule_id,
                        "status": run.status,
                        "round_id": run.round_id,
                        "output_id": run.output_id,
                        "reason": run.reason,
                    }
                    for run in runs
                ],
            }
        )
    finally:
        session.close()


@main.command("backup-db")
@click.option("--backup-dir", default=None, type=click.Path(file_okay=False, path_type=str))
def backup_db(backup_dir: str | None) -> None:
    """Write a compressed logical database snapshot for recovery evidence."""
    session = get_sessionmaker()()
    try:
        payload = write_database_snapshot(session, backup_dir=backup_dir)
        _echo_json(payload)
    finally:
        session.close()


@main.command("ops-status")
@click.option("--strict", is_flag=True, help="Exit non-zero when ops status is degraded.")
def ops_status_command(strict: bool) -> None:
    """Print the same operational readiness payload exposed by /api/ops/status."""
    session = get_sessionmaker()()
    onyx = get_onyx_client()
    try:
        payload = ops_status(session, onyx)
        _echo_json(payload)
        if strict and payload.get("status") != "ok":
            failures = ", ".join(str(item) for item in payload.get("failures", []))
            raise click.ClickException(f"operational status is degraded: {failures}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

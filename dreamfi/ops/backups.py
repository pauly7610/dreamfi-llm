"""Logical database backups for scheduled production snapshots."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.compiler import IdentifierPreparer

from dreamfi.config import get_settings


def _json_default(value: Any) -> str | int | float | bool | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return str(value)


def _backup_files(backup_dir: Path) -> list[Path]:
    return sorted(
        backup_dir.glob("dreamfi-db-*.jsonl.gz"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _prune_backups(
    backup_dir: Path,
    *,
    retention_days: int,
    max_files: int,
) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    files = _backup_files(backup_dir)
    keep = set(files[:max_files])
    pruned: list[str] = []
    for path in files:
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if path not in keep or modified < cutoff:
            path.unlink(missing_ok=True)
            pruned.append(path.name)
    return pruned


def write_database_snapshot(
    session: Session,
    *,
    backup_dir: str | Path | None = None,
    retention_days: int | None = None,
    max_files: int | None = None,
) -> dict[str, Any]:
    """Write a compressed JSONL database snapshot and prune old snapshots."""
    settings = get_settings()
    destination = Path(backup_dir or settings.dreamfi_backup_dir)
    destination.mkdir(parents=True, exist_ok=True)

    bind = session.get_bind()
    inspector = inspect(bind)
    preparer = IdentifierPreparer(bind.dialect)
    tables = sorted(inspector.get_table_names())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = destination / f"dreamfi-db-{timestamp}.jsonl.gz"

    try:
        alembic_version = session.execute(text("select version_num from alembic_version")).scalar()
    except Exception:
        alembic_version = None

    table_counts: dict[str, int] = {}
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        metadata = {
            "record_type": "metadata",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "alembic_version": alembic_version,
            "tables": tables,
        }
        handle.write(json.dumps(metadata, sort_keys=True, default=_json_default) + "\n")
        for table in tables:
            quoted_table = preparer.quote(table)
            rows = session.execute(text(f"select * from {quoted_table}")).mappings()
            count = 0
            for row in rows:
                handle.write(
                    json.dumps(
                        {
                            "record_type": "row",
                            "table": table,
                            "data": dict(row),
                        },
                        sort_keys=True,
                        default=_json_default,
                    )
                    + "\n"
                )
                count += 1
            table_counts[table] = count

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pruned = _prune_backups(
        destination,
        retention_days=retention_days or settings.dreamfi_backup_retention_days,
        max_files=max_files or settings.dreamfi_backup_max_files,
    )
    return {
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest,
        "alembic_version": alembic_version,
        "table_counts": table_counts,
        "pruned": pruned,
    }

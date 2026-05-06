from __future__ import annotations

import gzip
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.db.models import Base
from dreamfi.ops.backups import write_database_snapshot
from dreamfi.ops.demo import seed_demo_data


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_write_database_snapshot_exports_rows_and_metadata(tmp_path: Path) -> None:
    session = _session(tmp_path)
    seed_demo_data(session)

    payload = write_database_snapshot(
        session,
        backup_dir=tmp_path / "backups",
        retention_days=14,
        max_files=30,
    )

    path = Path(payload["path"])
    assert path.exists()
    assert payload["bytes"] > 0
    assert len(payload["sha256"]) == 64
    assert payload["table_counts"]["console_topics"] == 2
    assert payload["table_counts"]["eval_outputs"] == 3

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        first = json.loads(handle.readline())
        rows = [json.loads(line) for line in handle]

    assert first["record_type"] == "metadata"
    assert "console_topics" in first["tables"]
    assert any(row["record_type"] == "row" and row["table"] == "console_topics" for row in rows)


def test_write_database_snapshot_prunes_to_max_files(tmp_path: Path) -> None:
    session = _session(tmp_path)
    backup_dir = tmp_path / "backups"

    first = write_database_snapshot(session, backup_dir=backup_dir, max_files=30)
    second = write_database_snapshot(session, backup_dir=backup_dir, max_files=1)

    assert Path(second["path"]).exists()
    assert first["filename"] in second["pruned"]
    assert not (backup_dir / first["filename"]).exists()

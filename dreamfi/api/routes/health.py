"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.onyx.client import OnyxClient
from dreamfi.ops.readiness import ops_status

router = APIRouter()


@router.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/health")
def health(onyx: OnyxClient = Depends(get_onyx_client)) -> dict[str, str]:
    return {"status": "ok", "onyx": onyx.ping()}


@router.get("/api/ops/status")
def operational_status(
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, object]:
    return ops_status(session, onyx)

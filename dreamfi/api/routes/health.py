"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from dreamfi.api.deps import get_onyx_client
from dreamfi.onyx.client import OnyxClient

router = APIRouter()


@router.get("/health")
def health(onyx: OnyxClient = Depends(get_onyx_client)) -> dict[str, str]:
    return {"status": "ok", "onyx": onyx.ping()}

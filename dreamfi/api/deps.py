"""FastAPI dependency providers."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.db.session import get_sessionmaker
from dreamfi.onyx.client import OnyxClient


def get_db_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def get_onyx_client() -> OnyxClient:
    s = get_settings()
    return OnyxClient(base_url=s.onyx_base_url, api_key=s.onyx_api_key)

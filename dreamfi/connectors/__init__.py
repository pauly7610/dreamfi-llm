"""External connectors (C2).

Each service DreamFi reads from lives under ``dreamfi/connectors/<name>/``
and is the ONLY allowed import path for that service — mirroring the
OnyxClient rule in AGENTS.md.

Connectors share :mod:`dreamfi.connectors.base` for retries, caching and a
uniform error taxonomy.
"""

from dreamfi.connectors.base import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorServerError,
    ConnectorTimeoutError,
    HttpConnector,
    TTLCache,
)

__all__ = [
    "ConnectorAuthError",
    "ConnectorError",
    "ConnectorNotFoundError",
    "ConnectorServerError",
    "ConnectorTimeoutError",
    "HttpConnector",
    "TTLCache",
]

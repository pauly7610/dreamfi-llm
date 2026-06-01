"""External connectors (C2).

Each service DreamFi reads from lives under ``dreamfi/context_connectors/<name>/``
and is the ONLY allowed import path for that service — mirroring the
OnyxClient rule in AGENTS.md.

Connectors share :mod:`dreamfi.context_connectors.base` for retries, caching and a
uniform error taxonomy.
"""

from dreamfi.context_connectors.base import (
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

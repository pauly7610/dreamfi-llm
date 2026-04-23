"""Shared connector primitives: errors, HTTP base class, TTL cache, retries."""
from __future__ import annotations

import time
from typing import Any, Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class ConnectorError(Exception):
    """Base class for any connector error."""


class ConnectorAuthError(ConnectorError):
    """401/403 from the upstream service."""


class ConnectorNotFoundError(ConnectorError):
    """404 from the upstream service."""


class ConnectorServerError(ConnectorError):
    """5xx (or unexpected 4xx) from the upstream service."""


class ConnectorTimeoutError(ConnectorError):
    """The connector's HTTP call timed out."""


# Retry envelope — matches OnyxClient's shape (AGENTS.md).
connector_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2.0),
    retry=retry_if_exception_type((ConnectorServerError, httpx.TransportError)),
    reraise=True,
)


class TTLCache:
    """Tiny in-process TTL cache keyed on ``(workspace_id, endpoint, params)``.

    Intentionally minimal: no LRU, no size cap. Connector fetchers should
    pick TTLs short enough that unbounded growth is not a concern, and a
    process restart flushes everything.
    """

    def __init__(self, *, default_ttl_seconds: float = 60.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._store: dict[tuple[str, str, str], tuple[float, Any]] = {}

    @staticmethod
    def _params_key(params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        return "&".join(f"{k}={params[k]}" for k in sorted(params))

    def get(
        self,
        *,
        workspace_id: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        key = (workspace_id, endpoint, self._params_key(params))
        hit = self._store.get(key)
        if hit is None:
            return None
        expires_at, value = hit
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(
        self,
        *,
        workspace_id: str,
        endpoint: str,
        value: Any,
        params: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
    ) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        key = (workspace_id, endpoint, self._params_key(params))
        self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


class HttpConnector:
    """Common HTTP base used by every connector.

    Subclasses override ``_auth_headers`` and expose typed domain methods.
    All outbound HTTP goes through :meth:`_get` / :meth:`_post` / :meth:`_put`
    which normalize error handling.
    """

    health_path: str = "/"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._auth_headers(),
            timeout=timeout,
            transport=transport,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    # --- error handling ------------------------------------------------------

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise ConnectorAuthError(
                f"{self.__class__.__name__}: auth failed ({resp.status_code})"
            )
        if resp.status_code == 404:
            raise ConnectorNotFoundError(
                f"{self.__class__.__name__}: 404 {resp.request.url}"
            )
        if 500 <= resp.status_code < 600:
            raise ConnectorServerError(
                f"{self.__class__.__name__}: {resp.status_code} {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise ConnectorServerError(
                f"{self.__class__.__name__}: {resp.status_code} {resp.text[:200]}"
            )

    # --- HTTP primitives -----------------------------------------------------

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.get(path, **kwargs)
        except httpx.TimeoutException as e:
            raise ConnectorTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return resp

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.post(path, **kwargs)
        except httpx.TimeoutException as e:
            raise ConnectorTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return resp

    def _put(self, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.put(path, **kwargs)
        except httpx.TimeoutException as e:
            raise ConnectorTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return resp

    # --- public ---------------------------------------------------------------

    def ping(self) -> Literal["reachable", "unreachable"]:
        """Cheap reachability check — every connector must implement this."""
        try:
            resp = self._client.get(self.health_path, timeout=5.0)
        except (httpx.HTTPError, ConnectorError):
            return "unreachable"
        return "reachable" if 200 <= resp.status_code < 400 else "unreachable"

    def close(self) -> None:
        self._client.close()

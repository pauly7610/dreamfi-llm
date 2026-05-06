"""HTTP authentication for the DreamFi API and console."""
from __future__ import annotations

import base64
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from dreamfi.config import get_settings

AUTH_EXEMPT_PATHS = {"/ready", "/health"}
PLACEHOLDER_SECRETS = {"", "change-me", "change-me-before-deploy"}


def _stamp_auth_context(
    request: Request,
    *,
    actor_id: str,
    actor_type: str,
    auth_method: str,
    outcome: str,
    reason: str | None = None,
) -> None:
    request.state.actor_id = actor_id
    request.state.actor_type = actor_type
    request.state.auth_method = auth_method
    request.state.auth_outcome = outcome
    if reason is not None:
        request.state.auth_failure_reason = reason


def _auth_challenge(detail: str = "authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": 'Basic realm="DreamFi", Bearer'},
    )


def _bearer_token(authorization: str) -> str | None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _basic_credentials(authorization: str) -> tuple[str, str] | None:
    scheme, _, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded.strip():
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return username, password


def require_auth(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Protect console and API routes with Basic auth or a Bearer token."""
    if request.url.path in AUTH_EXEMPT_PATHS:
        _stamp_auth_context(
            request,
            actor_id="healthcheck",
            actor_type="system",
            auth_method="exempt",
            outcome="success",
        )
        return

    settings = get_settings()
    if not settings.dreamfi_auth_enabled:
        _stamp_auth_context(
            request,
            actor_id="auth-disabled",
            actor_type="system",
            auth_method="disabled",
            outcome="success",
        )
        return

    expected_password = (
        ""
        if settings.dreamfi_auth_password in PLACEHOLDER_SECRETS
        else settings.dreamfi_auth_password
    )
    expected_token = (
        ""
        if settings.dreamfi_api_token in PLACEHOLDER_SECRETS
        else settings.dreamfi_api_token
    )
    if not expected_password and not expected_token:
        _stamp_auth_context(
            request,
            actor_id="anonymous",
            actor_type="anonymous",
            auth_method="none",
            outcome="failure",
            reason="auth_not_configured",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "DreamFi auth is enabled but DREAMFI_AUTH_PASSWORD or "
                "DREAMFI_API_TOKEN is not configured"
            ),
        )

    if authorization is None:
        _stamp_auth_context(
            request,
            actor_id="anonymous",
            actor_type="anonymous",
            auth_method="none",
            outcome="failure",
            reason="missing_credentials",
        )
        raise _auth_challenge()

    token = _bearer_token(authorization)
    if token is not None and expected_token:
        if secrets.compare_digest(token, expected_token):
            _stamp_auth_context(
                request,
                actor_id="api_token",
                actor_type="service_account",
                auth_method="bearer",
                outcome="success",
            )
            return

    credentials = _basic_credentials(authorization)
    if credentials is not None and expected_password:
        username, password = credentials
        if secrets.compare_digest(username, settings.dreamfi_auth_username) and secrets.compare_digest(
            password,
            expected_password,
        ):
            _stamp_auth_context(
                request,
                actor_id=username,
                actor_type="user",
                auth_method="basic",
                outcome="success",
            )
            return

    if credentials is not None:
        actor_id = credentials[0] or "anonymous"
        auth_method = "basic"
    elif token is not None:
        actor_id = "api_token"
        auth_method = "bearer"
    else:
        actor_id = "anonymous"
        auth_method = "unknown"
    _stamp_auth_context(
        request,
        actor_id=actor_id,
        actor_type="anonymous",
        auth_method=auth_method,
        outcome="failure",
        reason="invalid_credentials",
    )

    raise _auth_challenge("invalid credentials")

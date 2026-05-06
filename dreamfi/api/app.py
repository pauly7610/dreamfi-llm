"""DreamFi FastAPI app."""
from __future__ import annotations

import time
import uuid

from fastapi import Depends, FastAPI
from starlette.requests import Request
from starlette.responses import Response

from dreamfi.api.auth import require_auth
from dreamfi.api.routes import console, eval_rounds, health, learning, publish, settings, skills, workflows
from dreamfi.audit import write_audit_event_best_effort
from dreamfi.config import get_settings


def _should_audit_request(request: Request) -> bool:
    settings = get_settings()
    if not settings.dreamfi_audit_enabled:
        return False
    if request.url.path in {"/ready", "/health"}:
        return False
    if request.url.path in {"/favicon.svg", "/console/favicon.svg"}:
        return False
    if request.url.path.startswith("/console/assets/"):
        return False
    return bool(settings.dreamfi_audit_log_reads or request.method not in {"GET", "HEAD", "OPTIONS"})


def _request_outcome(status_code: int) -> str:
    if status_code >= 500:
        return "error"
    if status_code in {401, 403, 409, 422}:
        return "blocked"
    if status_code >= 400:
        return "failure"
    return "success"


def _request_severity(status_code: int) -> str:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "warning"
    return "info"


def _audit_request(
    request: Request,
    *,
    status_code: int,
    duration_ms: int,
    reason: str | None = None,
) -> None:
    if not _should_audit_request(request):
        return
    action = "auth_failure" if getattr(request.state, "auth_outcome", None) == "failure" else "http_request"
    write_audit_event_best_effort(
        category="access",
        action=action,
        outcome=_request_outcome(status_code),  # type: ignore[arg-type]
        request=request,
        severity=_request_severity(status_code),  # type: ignore[arg-type]
        reason=reason or getattr(request.state, "auth_failure_reason", None),
        status_code=status_code,
        metadata={
            "duration_ms": duration_ms,
            "query_param_keys": sorted(request.query_params.keys()),
            "auth_outcome": getattr(request.state, "auth_outcome", None),
        },
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="DreamFi",
        version="0.2.0",
        dependencies=[Depends(require_auth)],
    )

    @app.middleware("http")
    async def audit_requests(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            _audit_request(
                request,
                status_code=500,
                duration_ms=duration_ms,
                reason=type(exc).__name__,
            )
            raise
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        response.headers["X-Request-ID"] = request.state.request_id
        _audit_request(
            request,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    app.include_router(health.router)
    app.include_router(skills.router, prefix="/v1/skills")
    app.include_router(eval_rounds.router, prefix="/v1/skills")
    app.include_router(publish.router, prefix="/v1/skills")
    app.include_router(workflows.router)
    app.include_router(learning.router)
    app.include_router(settings.router)
    app.include_router(console.router)
    return app


app = create_app()

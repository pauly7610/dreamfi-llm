"""DreamFi FastAPI app."""
from __future__ import annotations

from fastapi import FastAPI

from dreamfi.api.routes import console, eval_rounds, health, publish, skills


def create_app() -> FastAPI:
    app = FastAPI(title="DreamFi", version="0.2.0")
    app.include_router(health.router)
    app.include_router(skills.router, prefix="/v1/skills")
    app.include_router(eval_rounds.router, prefix="/v1/skills")
    app.include_router(publish.router, prefix="/v1/skills")
    app.include_router(console.router)
    return app


app = create_app()

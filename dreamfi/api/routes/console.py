"""Minimal operator console (server-rendered Jinja)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.db.models import EvalRound, Skill

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

router = APIRouter()


@router.get("/console", response_class=HTMLResponse)
def console(session: Session = Depends(get_db_session)) -> HTMLResponse:
    skills = session.scalars(select(Skill).order_by(Skill.skill_id)).all()
    rounds_by_skill: dict[str, list[dict[str, object]]] = {}
    for s in skills:
        rounds = session.scalars(
            select(EvalRound)
            .where(EvalRound.skill_id == s.skill_id)
            .order_by(desc(EvalRound.completed_at))
            .limit(20)
        ).all()
        rounds_by_skill[s.skill_id] = [
            {
                "round_id": r.round_id,
                "score": float(r.score),
                "completed_at": (r.completed_at.isoformat() if r.completed_at else "n/a"),
            }
            for r in rounds
        ]
    tpl = _env.get_template("console.html")
    return HTMLResponse(tpl.render(skills=skills, rounds_by_skill=rounds_by_skill))

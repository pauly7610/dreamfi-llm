"""C4: POST /v1/context/ask integration (ContextBuilder + grounding + memory)."""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_context_builder, get_db_session
from dreamfi.connectors.confluence import ConfluenceClient
from dreamfi.connectors.jira import JiraClient
from dreamfi.context.builder import (
    ClaimDistillation,
    ClaimDraft,
    ConnectorRegistry,
    ContextBuilder,
    OpenQuestionDraft,
)
from dreamfi.context.model_router import FakeModelRouter
from dreamfi.db.models import Base, ContextQuestionRow

JIRA_URL = "https://acme.atlassian.net"
CONF_URL = "https://acme.atlassian.net"


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def _mock_jira(keys: list[str]) -> None:
    respx.get(f"{JIRA_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": k,
                        "fields": {
                            "summary": f"summary {k}",
                            "status": {"name": "In Progress"},
                            "issuetype": {"name": "Task"},
                            "parent": {"key": "ACT-321"},
                        },
                    }
                    for k in keys
                ],
                "total": len(keys),
            },
        )
    )
    respx.get(re.compile(f"{JIRA_URL}/rest/api/3/issue/.*/changelog")).mock(
        return_value=httpx.Response(200, json={"values": []})
    )


def _client_with_builder(
    session: Session, builder: ContextBuilder
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: (yield session)  # type: ignore[misc]
    app.dependency_overrides[get_context_builder] = lambda: builder
    return TestClient(app)


def _make_builder(session: Session, llm: FakeModelRouter) -> ContextBuilder:
    jira = JiraClient(base_url=JIRA_URL, email="p", api_token="t")
    conf = ConfluenceClient(base_url=CONF_URL, email="p", api_token="t")
    return ContextBuilder(
        connectors=ConnectorRegistry(jira=jira, confluence=conf),
        llm=llm,
        session=session,
    )


@respx.mock
def test_ask_returns_grounded_claims_and_records_memory(session: Session) -> None:
    _mock_jira(["ACT-410"])

    llm = FakeModelRouter(
        responses={
            "ACT-410": ClaimDistillation(
                claims=[
                    ClaimDraft(
                        statement="ACT-410 is in progress",
                        source_refs=["jira:ACT-410"],
                        confidence=0.85,
                    )
                ],
                open_questions=[
                    OpenQuestionDraft(
                        question="Is EU legal sign-off needed?",
                        why_open="no_source",
                    )
                ],
            )
        }
    )
    client = _client_with_builder(session, _make_builder(session, llm))

    resp = client.post(
        "/v1/context/ask",
        json={
            "workspace_id": "w1",
            "asker": "laila",
            "question": "what's happening with onboarding?",
            "hint": {"epic_key": "ACT-321"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["topic_id"]
    assert body["claims"][0]["citations"] == ["jira:ACT-410"]
    assert body["open_questions"][0]["why_open"] == "no_source"
    assert body["confidence"] > 0.0

    # Memory row was persisted.
    rows = list(session.scalars(select(ContextQuestionRow)))
    assert len(rows) == 1
    assert rows[0].asker == "laila"


@respx.mock
def test_ask_rejects_ungrounded_claim_with_412(session: Session) -> None:
    _mock_jira(["ACT-411"])
    llm = FakeModelRouter(
        responses={
            "ACT-411": ClaimDistillation(
                claims=[
                    ClaimDraft(
                        statement="This claim has no citations",
                        source_refs=[],  # empty -> ungrounded
                        confidence=0.6,
                    )
                ]
            )
        }
    )
    client = _client_with_builder(session, _make_builder(session, llm))

    resp = client.post(
        "/v1/context/ask",
        json={
            "workspace_id": "w1",
            "question": "rollout status",
            "hint": {"epic_key": "ACT-321"},
        },
    )
    assert resp.status_code == 412
    assert resp.json()["detail"] == "ungrounded_claim_rejected"


@respx.mock
def test_ask_surfaces_prior_memory_hits(session: Session) -> None:
    _mock_jira(["ACT-410"])
    llm = FakeModelRouter(
        responses={
            "ACT-410": ClaimDistillation(
                claims=[
                    ClaimDraft(
                        statement="ACT-410 is in progress",
                        source_refs=["jira:ACT-410"],
                        confidence=0.8,
                    )
                ]
            )
        }
    )
    client = _client_with_builder(session, _make_builder(session, llm))

    # Ask twice with slightly different wording — second call must see memory.
    first = client.post(
        "/v1/context/ask",
        json={
            "workspace_id": "w1",
            "question": "what's happening with onboarding?",
            "hint": {"epic_key": "ACT-321"},
        },
    )
    assert first.status_code == 200
    assert first.json()["memory"] == []

    second = client.post(
        "/v1/context/ask",
        json={
            "workspace_id": "w1",
            "question": "happening with onboarding",
            "hint": {"epic_key": "ACT-321"},
        },
    )
    assert second.status_code == 200
    mem = second.json()["memory"]
    assert len(mem) == 1
    assert mem[0]["similarity"] >= 0.5


@respx.mock
def test_ask_returns_502_when_model_structuring_fails(session: Session) -> None:
    _mock_jira(["ACT-410"])
    llm = FakeModelRouter(responses={})  # no match -> ContextStructuringError
    client = _client_with_builder(session, _make_builder(session, llm))

    resp = client.post(
        "/v1/context/ask",
        json={
            "workspace_id": "w1",
            "question": "what's happening",
            "hint": {"epic_key": "ACT-321"},
        },
    )
    assert resp.status_code == 502
    assert "model_structuring_error" in resp.json()["detail"]

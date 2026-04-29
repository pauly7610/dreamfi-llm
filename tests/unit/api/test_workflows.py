from __future__ import annotations

import re
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.db.models import Base, EvalOutput, Skill
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


def _client(tmp_path: Path) -> tuple[TestClient, Session]:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_registry(session, repo_root=REPO_ROOT)
    for skill in session.query(Skill).all():
        skill.onyx_persona_id = 100
    session.commit()
    app = create_app()

    def _session_override():
        yield session

    def _onyx_override() -> OnyxClient:
        return OnyxClient(base_url="http://onyx.test", api_key="k")

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_onyx_client] = _onyx_override
    return TestClient(app), session


@respx.mock
def test_live_ask_searches_onyx_with_scope(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    route = respx.post("http://onyx.test/api/admin/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": "doc-1",
                        "semantic_identifier": "KYC funnel report",
                        "blurb": "KYC completion moved after retry policy changes.",
                        "score": 0.92,
                        "link": "https://dreamfi.test/doc-1",
                        "updated_at": "2026-04-28T00:00:00Z",
                    }
                ]
            },
        )
    )

    response = client.post(
        "/api/ask",
        json={
            "question": "Why did KYC conversion move?",
            "topic_id": "kyc-conversion",
            "source_id": "socure",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] > 0
    assert body["citations"][0]["document_id"] == "doc-1"
    assert "KYC funnel report" in body["answer"]
    assert route.calls.last.request is not None
    assert b"kyc-conversion" in route.calls.last.request.content
    assert b"socure" in route.calls.last.request.content


@respx.mock
def test_generate_workflow_persists_artifact_with_readiness(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"# Risk context\\nKYC moved.\\n# Evidence\\nSocure retry logs.\\n'
        b'# Policy decision\\nHold launch.\\n"}\n'
        b'{"citations":{"1":"doc-1","2":"doc-2","3":"doc-3"}}\n'
        b'{"documents":[{"id":"d1","updated_at":"2026-04-28T00:00:00Z"}]}\n'
        b'{"message_id":77}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )

    response = client.post(
        "/api/workflows/generate",
        json={
            "workflow_slug": "risk-brd",
            "question": "Should we change KYC retry policy?",
            "topic_id": "kyc-conversion",
            "source_id": "socure",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    output = session.get(EvalOutput, body["output_id"])
    assert output is not None
    assert output.pass_fail == "pass"
    assert output.export_readiness is not None
    assert output.criteria_json["workflow_title"] == "Risk BRD"
    assert body["destination_href"] == f"/console/review?focus={output.output_id}"

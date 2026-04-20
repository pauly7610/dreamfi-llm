"""Mocked contract tests for OnyxClient."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import (
    OnyxAuthError,
    OnyxNotFoundError,
    OnyxServerError,
    OnyxTimeoutError,
)

BASE = "http://onyx.test"


@pytest.fixture
def client() -> OnyxClient:
    return OnyxClient(base_url=BASE, api_key="onyx_pat_test")


@respx.mock
def test_ping_success(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/health").mock(return_value=httpx.Response(200))
    assert client.ping() == "reachable"


@respx.mock
def test_ping_returns_unreachable_on_error(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/health").mock(side_effect=httpx.ConnectError("down"))
    assert client.ping() == "unreachable"


@respx.mock
def test_auth_error_raises(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/persona").mock(return_value=httpx.Response(401))
    with pytest.raises(OnyxAuthError):
        client.list_personas()


@respx.mock
def test_not_found_raises(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/persona").mock(return_value=httpx.Response(404))
    with pytest.raises(OnyxNotFoundError):
        client.list_personas()


@respx.mock
def test_server_error_retries_then_raises(client: OnyxClient) -> None:
    route = respx.get(f"{BASE}/api/persona").mock(return_value=httpx.Response(500))
    with pytest.raises(OnyxServerError):
        client.list_personas()
    assert route.call_count >= 2  # retried at least once


@respx.mock
def test_timeout_raises(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/persona").mock(
        side_effect=httpx.TimeoutException("slow")
    )
    with pytest.raises(OnyxTimeoutError):
        client.list_personas()


@respx.mock
def test_list_personas(client: OnyxClient) -> None:
    respx.get(f"{BASE}/api/persona").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        )
    )
    personas = client.list_personas()
    assert [p.id for p in personas] == [1, 2]


@respx.mock
def test_create_persona_roundtrip(client: OnyxClient) -> None:
    route = respx.post(f"{BASE}/api/persona").mock(
        return_value=httpx.Response(200, json={"id": 42, "name": "X"})
    )
    p = client.create_persona(
        name="X",
        description="d",
        system_prompt="sp",
        document_set_ids=[1],
        tool_ids=[1],
    )
    assert p.id == 42
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "X"
    assert body["document_set_ids"] == [1]
    assert body["tool_ids"] == [1]
    assert body["include_citations"] is True


@respx.mock
def test_create_chat_session(client: OnyxClient) -> None:
    respx.post(f"{BASE}/api/chat/create-chat-session").mock(
        return_value=httpx.Response(
            200, json={"chat_session_id": "00000000-0000-0000-0000-000000000001"}
        )
    )
    s = client.create_chat_session(persona_id=7, description="d")
    assert s.id == "00000000-0000-0000-0000-000000000001"
    assert s.persona_id == 7


@respx.mock
def test_send_message_streaming_accumulates(client: OnyxClient) -> None:
    stream_body = (
        b'{"answer_piece":"Hello "}\n'
        b'{"answer_piece":"world."}\n'
        b'{"citations":{"1":"doc-123"}}\n'
        b'{"documents":[{"id":"d1"}]}\n'
        b'{"message_id":77}\n'
    )
    respx.post(f"{BASE}/api/chat/send-chat-message").mock(
        return_value=httpx.Response(200, content=stream_body)
    )
    result = client.send_message_sync(
        chat_session_id="00000000-0000-0000-0000-000000000001",
        parent_message_id=None,
        message="Hi",
    )
    assert result.text == "Hello world."
    assert result.citations == {1: "doc-123"}
    assert result.documents == [{"id": "d1"}]
    assert result.message_id == 77


@respx.mock
def test_admin_search_returns_hits(client: OnyxClient) -> None:
    respx.post(f"{BASE}/api/admin/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": "d1",
                        "semantic_identifier": "s",
                        "blurb": "...",
                        "score": 0.9,
                        "link": "https://x",
                        "updated_at": "2026-04-10T00:00:00Z",
                    }
                ]
            },
        )
    )
    hits = client.admin_search(query="pricing", filters={})
    assert hits[0].document_id == "d1"
    assert hits[0].score == 0.9


@respx.mock
def test_ingest_document_defaults_cc_pair(client: OnyxClient) -> None:
    route = respx.post(f"{BASE}/api/onyx-api/ingestion").mock(
        return_value=httpx.Response(
            200, json={"document_id": "d1", "already_existed": False}
        )
    )
    res = client.ingest_document(
        doc_id="d1",
        text="hello",
        semantic_identifier="s",
        metadata={"k": "v"},
        source_url="https://x",
    )
    assert res.document_id == "d1"
    body = json.loads(route.calls.last.request.content)
    assert body["document"]["id"] == "d1"
    assert body["cc_pair_id"] is None


@respx.mock
def test_bearer_header_attached(client: OnyxClient) -> None:
    route = respx.get(f"{BASE}/api/persona").mock(
        return_value=httpx.Response(200, json=[])
    )
    client.list_personas()
    auth = route.calls.last.request.headers.get("authorization", "")
    assert auth.startswith("Bearer onyx_pat_")

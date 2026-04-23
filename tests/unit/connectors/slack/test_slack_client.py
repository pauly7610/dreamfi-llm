"""C2e: SlackClient contract tests."""
from __future__ import annotations

import httpx
import pytest
import respx

from dreamfi.connectors import ConnectorAuthError, ConnectorServerError
from dreamfi.connectors.slack import SlackClient

BASE_URL = "https://slack.com"


def _client() -> SlackClient:
    return SlackClient(base_url=BASE_URL, bot_token="xoxb-test")


@respx.mock
def test_list_channels_parses_entries() -> None:
    respx.get(f"{BASE_URL}/api/conversations.list").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "channels": [
                    {"id": "C1", "name": "activation", "is_archived": False},
                    {"id": "C2", "name": "old-stuff", "is_archived": True},
                ],
            },
        )
    )
    channels = _client().list_channels()
    assert [c.name for c in channels] == ["activation", "old-stuff"]
    assert channels[1].is_archived is True


@respx.mock
def test_invalid_auth_maps_to_connector_auth_error() -> None:
    respx.get(f"{BASE_URL}/api/conversations.list").mock(
        return_value=httpx.Response(200, json={"ok": False, "error": "invalid_auth"})
    )
    with pytest.raises(ConnectorAuthError):
        _client().list_channels()


@respx.mock
def test_search_messages_extracts_matches() -> None:
    respx.get(f"{BASE_URL}/api/search.messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "channel": {"id": "C1"},
                            "ts": "1700000000.0001",
                            "user": "U1",
                            "text": "rollout blocked",
                        }
                    ]
                },
            },
        )
    )
    msgs = _client().search_messages("rollout")
    assert len(msgs) == 1
    assert msgs[0].channel_id == "C1"
    assert msgs[0].text == "rollout blocked"


@respx.mock
def test_thread_returns_messages() -> None:
    respx.get(f"{BASE_URL}/api/conversations.replies").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [
                    {"ts": "1", "user": "U1", "text": "hi"},
                    {"ts": "2", "user": "U2", "text": "reply", "thread_ts": "1"},
                ],
            },
        )
    )
    replies = _client().thread("C1", "1")
    assert [m.text for m in replies] == ["hi", "reply"]


@respx.mock
def test_unknown_error_maps_to_server_error() -> None:
    respx.get(f"{BASE_URL}/api/conversations.list").mock(
        return_value=httpx.Response(200, json={"ok": False, "error": "team_missing"})
    )
    with pytest.raises(ConnectorServerError):
        _client().list_channels()

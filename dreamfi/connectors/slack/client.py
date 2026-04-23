"""Slack Web API client — the small read-only surface we need."""
from __future__ import annotations

from typing import Any

import httpx

from dreamfi.connectors.base import (
    ConnectorAuthError,
    ConnectorServerError,
    HttpConnector,
    connector_retry,
)
from dreamfi.connectors.slack.models import SlackChannel, SlackMessage


def _check_ok(data: dict[str, Any]) -> None:
    """Slack always returns 200 but encodes success in the JSON body."""
    if data.get("ok") is True:
        return
    err = str(data.get("error") or "slack_error")
    if err in {"invalid_auth", "not_authed", "token_expired", "token_revoked"}:
        raise ConnectorAuthError(f"Slack: {err}")
    raise ConnectorServerError(f"Slack: {err}")


def _messages_from(channel_id: str, payload: list[dict[str, Any]]) -> list[SlackMessage]:
    out: list[SlackMessage] = []
    for m in payload:
        out.append(
            SlackMessage(
                channel_id=channel_id,
                ts=str(m.get("ts", "")),
                user_id=m.get("user"),
                text=str(m.get("text", "")),
                thread_ts=m.get("thread_ts"),
            )
        )
    return out


class SlackClient(HttpConnector):
    health_path = "/api/api.test"

    def __init__(
        self,
        base_url: str = "https://slack.com",
        *,
        bot_token: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._bot_token = bot_token
        super().__init__(base_url, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._bot_token}",
        }

    @connector_retry
    def list_channels(self) -> list[SlackChannel]:
        resp = self._get("/api/conversations.list", params={"limit": 200})
        data = resp.json()
        _check_ok(data)
        return [
            SlackChannel(
                id=str(c.get("id", "")),
                name=str(c.get("name", "")),
                is_archived=bool(c.get("is_archived", False)),
            )
            for c in data.get("channels") or []
        ]

    @connector_retry
    def search_messages(self, query: str, *, count: int = 20) -> list[SlackMessage]:
        resp = self._get(
            "/api/search.messages", params={"query": query, "count": count}
        )
        data = resp.json()
        _check_ok(data)
        messages: list[SlackMessage] = []
        matches = (data.get("messages") or {}).get("matches") or []
        for m in matches:
            channel_id = ((m.get("channel") or {}).get("id")) or ""
            messages.append(
                SlackMessage(
                    channel_id=str(channel_id),
                    ts=str(m.get("ts", "")),
                    user_id=m.get("user"),
                    text=str(m.get("text", "")),
                    thread_ts=m.get("thread_ts"),
                )
            )
        return messages

    @connector_retry
    def thread(self, channel: str, ts: str) -> list[SlackMessage]:
        resp = self._get(
            "/api/conversations.replies", params={"channel": channel, "ts": ts}
        )
        data = resp.json()
        _check_ok(data)
        return _messages_from(channel, list(data.get("messages") or []))

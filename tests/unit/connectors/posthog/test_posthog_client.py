"""C2c: PostHogClient contract tests."""
from __future__ import annotations

import httpx
import respx

from dreamfi.connectors.posthog import PostHogClient

BASE_URL = "https://ph.test"


def _client() -> PostHogClient:
    return PostHogClient(base_url=BASE_URL, api_key="k", project_id=1)


@respx.mock
def test_query_funnel_parses_result() -> None:
    respx.post(f"{BASE_URL}/api/projects/1/insights/funnel/").mock(
        return_value=httpx.Response(
            200,
            json={"id": "f1", "result": [{"step": 1, "count": 100}], "columns": ["step", "count"]},
        )
    )
    result = _client().query_funnel({"events": []})
    assert result.query_id == "f1"
    assert result.result[0]["count"] == 100


@respx.mock
def test_events_for_user_returns_results() -> None:
    respx.get(f"{BASE_URL}/api/projects/1/events/").mock(
        return_value=httpx.Response(
            200, json={"results": [{"event": "$pageview"}, {"event": "signup"}]}
        )
    )
    events = _client().events_for_user("user-42")
    assert [e["event"] for e in events] == ["$pageview", "signup"]


@respx.mock
def test_feature_flag_state_finds_matching_key() -> None:
    respx.get(f"{BASE_URL}/api/projects/1/feature_flags/").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"key": "onb_v3", "active": True, "rollout_percentage": 25},
                    {"key": "other", "active": False},
                ]
            },
        )
    )
    flag = _client().feature_flag_state("onb_v3")
    assert flag is not None
    assert flag.active is True
    assert flag.rollout_percentage == 25


@respx.mock
def test_feature_flag_state_returns_none_when_absent() -> None:
    respx.get(f"{BASE_URL}/api/projects/1/feature_flags/").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    assert _client().feature_flag_state("missing") is None

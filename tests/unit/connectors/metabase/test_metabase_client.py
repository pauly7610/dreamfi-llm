"""C2d: MetabaseClient contract tests."""
from __future__ import annotations

import httpx
import respx

from dreamfi.connectors.metabase import MetabaseClient

BASE_URL = "https://mb.test"


def _client() -> MetabaseClient:
    return MetabaseClient(base_url=BASE_URL, session_token="s")


@respx.mock
def test_query_card_parses_rows_and_columns() -> None:
    respx.post(f"{BASE_URL}/api/card/42/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "rows": [[1, "a"], [2, "b"]],
                    "cols": [{"name": "id"}, {"name": "name"}],
                }
            },
        )
    )
    result = _client().query_card(42)
    assert result.card_id == 42
    assert result.rows == [[1, "a"], [2, "b"]]
    assert result.columns == ["id", "name"]


@respx.mock
def test_dataset_posts_native_query() -> None:
    route = respx.post(f"{BASE_URL}/api/dataset").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "rows": [[7]],
                    "cols": [{"name": "retention"}],
                }
            },
        )
    )
    result = _client().dataset(3, "SELECT 7 AS retention")
    assert result.database_id == 3
    assert result.rows == [[7]]
    sent = route.calls.last.request.read().decode()
    assert "SELECT 7" in sent

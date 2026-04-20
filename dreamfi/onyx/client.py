"""Typed Onyx REST client."""
from __future__ import annotations

import json
from typing import Any, Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dreamfi.onyx.errors import (
    OnyxAuthError,
    OnyxError,
    OnyxNotFoundError,
    OnyxServerError,
    OnyxTimeoutError,
)
from dreamfi.onyx.models import (
    ChatResult,
    ChatSession,
    DocSet,
    IngestResult,
    Persona,
    SearchHit,
)

_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2.0),
    retry=retry_if_exception_type((OnyxServerError, httpx.TransportError)),
    reraise=True,
)


class OnyxClient:
    """Single choke point between DreamFi and Onyx.

    All HTTP to Onyx must go through this class.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._auth_headers(),
            timeout=timeout,
            transport=transport,
        )

    def _auth_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    # --- core helpers -------------------------------------------------------

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 401 or resp.status_code == 403:
            raise OnyxAuthError(f"Onyx auth failed: {resp.status_code}")
        if resp.status_code == 404:
            raise OnyxNotFoundError(f"Onyx 404: {resp.request.url}")
        if 500 <= resp.status_code < 600:
            raise OnyxServerError(f"Onyx {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise OnyxServerError(f"Onyx error {resp.status_code}: {resp.text[:200]}")

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.get(path, **kwargs)
        except httpx.TimeoutException as e:
            raise OnyxTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return resp

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.post(path, **kwargs)
        except httpx.TimeoutException as e:
            raise OnyxTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return resp

    # --- public API ---------------------------------------------------------

    def ping(self) -> Literal["reachable", "unreachable"]:
        try:
            resp = self._client.get("/api/health", timeout=5.0)
        except (httpx.HTTPError, OnyxError):
            return "unreachable"
        return "reachable" if resp.status_code == 200 else "unreachable"

    @_RETRY
    def list_personas(self) -> list[Persona]:
        resp = self._get("/api/persona")
        data = resp.json()
        items = data if isinstance(data, list) else data.get("personas", [])
        return [Persona(**p) for p in items]

    @_RETRY
    def create_persona(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str,
        document_set_ids: list[int],
        tool_ids: list[int],
        llm_model_provider_override: str | None = None,
        llm_model_version_override: str | None = None,
        num_chunks: int = 10,
        llm_relevance_filter: bool = True,
        include_citations: bool = True,
    ) -> Persona:
        body = {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
            "task_prompt": "",
            "document_set_ids": document_set_ids,
            "tool_ids": tool_ids,
            "is_public": False,
            "llm_model_provider_override": llm_model_provider_override,
            "llm_model_version_override": llm_model_version_override,
            "num_chunks": num_chunks,
            "llm_relevance_filter": llm_relevance_filter,
            "include_citations": include_citations,
            "datetime_aware": True,
            "starter_messages": [],
        }
        resp = self._post("/api/persona", json=body)
        return Persona(**resp.json())

    @_RETRY
    def update_persona(self, persona_id: int, **fields: Any) -> Persona:
        resp = self._client.patch(f"/api/persona/{persona_id}", json=fields)
        self._raise_for_status(resp)
        return Persona(**resp.json())

    @_RETRY
    def create_chat_session(
        self, *, persona_id: int, description: str = ""
    ) -> ChatSession:
        resp = self._post(
            "/api/chat/create-chat-session",
            json={"persona_id": persona_id, "description": description},
        )
        data = resp.json()
        session_id = data.get("chat_session_id") or data.get("id")
        return ChatSession(id=str(session_id), persona_id=persona_id, description=description)

    @_RETRY
    def admin_search(
        self,
        *,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        body = {"query": query, "filters": filters or {}, "limit": limit}
        resp = self._post("/api/admin/search", json=body)
        data = resp.json()
        docs = data.get("documents", [])
        return [SearchHit(**d) for d in docs]

    @_RETRY
    def ingest_document(
        self,
        *,
        doc_id: str,
        text: str,
        semantic_identifier: str,
        metadata: dict[str, Any] | None = None,
        source_url: str | None = None,
        doc_updated_at: str | None = None,
        title: str | None = None,
        cc_pair_id: int | None = None,
    ) -> IngestResult:
        body = {
            "document": {
                "id": doc_id,
                "sections": [{"text": text, "link": source_url}],
                "source": "ingestion_api",
                "semantic_identifier": semantic_identifier,
                "metadata": metadata or {},
                "doc_updated_at": doc_updated_at,
                "title": title or semantic_identifier,
            },
            "cc_pair_id": cc_pair_id,
        }
        resp = self._post("/api/onyx-api/ingestion", json=body)
        return IngestResult(**resp.json())

    @_RETRY
    def list_document_sets(self) -> list[DocSet]:
        resp = self._get("/api/document-set")
        data = resp.json()
        items = data if isinstance(data, list) else data.get("document_sets", [])
        return [DocSet(**d) for d in items]

    @_RETRY
    def create_document_set(
        self, *, name: str, description: str, cc_pair_ids: list[int] | None = None
    ) -> DocSet:
        resp = self._post(
            "/api/admin/document-set",
            json={
                "name": name,
                "description": description,
                "cc_pair_ids": cc_pair_ids or [],
            },
        )
        return DocSet(**resp.json())

    def send_message_sync(
        self,
        *,
        chat_session_id: str,
        parent_message_id: int | None,
        message: str,
        search_doc_ids: list[int] | None = None,
    ) -> ChatResult:
        body = {
            "chat_session_id": chat_session_id,
            "parent_message_id": parent_message_id,
            "message": message,
            "prompt_id": None,
            "search_doc_ids": search_doc_ids,
            "file_descriptors": [],
            "retrieval_options": {"run_search": "always", "real_time": True},
            "query_override": None,
            "use_existing_user_message": False,
        }
        try:
            resp = self._client.post("/api/chat/send-chat-message", json=body)
        except httpx.TimeoutException as e:
            raise OnyxTimeoutError(str(e)) from e
        self._raise_for_status(resp)
        return _parse_chat_stream(resp.content)


# -----------------------------------------------------------------------------


def _parse_chat_stream(body: bytes) -> ChatResult:
    text_parts: list[str] = []
    citations: dict[int, str] = {}
    documents: list[dict[str, Any]] = []
    message_id: int | None = None

    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        try:
            obj = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "answer_piece" in obj and obj["answer_piece"] is not None:
            text_parts.append(str(obj["answer_piece"]))
        if "citations" in obj and isinstance(obj["citations"], dict):
            for k, v in obj["citations"].items():
                try:
                    citations[int(k)] = str(v)
                except (TypeError, ValueError):
                    continue
        if "documents" in obj and isinstance(obj["documents"], list):
            documents.extend(obj["documents"])
        if "message_id" in obj and isinstance(obj["message_id"], int):
            message_id = obj["message_id"]

    return ChatResult(
        text="".join(text_parts),
        citations=citations,
        documents=documents,
        message_id=message_id,
    )



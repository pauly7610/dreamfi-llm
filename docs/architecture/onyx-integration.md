# Onyx integration

DreamFi treats Onyx as its knowledge substrate. All retrieval + citation logic
lives in Onyx; DreamFi consumes it through `dreamfi.onyx.client.OnyxClient`.

## Endpoints used

| Purpose             | Method | Path                                      |
|---------------------|--------|-------------------------------------------|
| Health              | GET    | `/api/health`                             |
| List personas       | GET    | `/api/persona`                            |
| Create persona      | POST   | `/api/persona`                            |
| Update persona      | PATCH  | `/api/persona/{persona_id}`               |
| Create chat session | POST   | `/api/chat/create-chat-session`           |
| Send message        | POST   | `/api/chat/send-chat-message` (streamed)  |
| Admin search        | POST   | `/api/admin/search`                       |
| Ingest document     | POST   | `/api/onyx-api/ingestion`                 |
| List doc-sets       | GET    | `/api/document-set`                       |
| Create doc-set      | POST   | `/api/admin/document-set`                 |

## Auth

Personal Access Token (`Bearer onyx_pat_...`) passed via `Authorization`
header. Stored in `ONYX_API_KEY`. Admin endpoints (ingestion, doc-set,
connector creation) require an admin-scoped PAT.

## Streaming

`/api/chat/send-chat-message` returns newline-delimited JSON packets. The
client accumulates `answer_piece` into the final text and collects
`citations` and `documents` for the confidence scorer.

## Seed flow

`scripts/onyx_seed.py` creates one `document_set` and one persona per
DreamFi skill. Each persona's `system_prompt` is the rendered skill template
from `dreamfi/skills/prompts/`. The resulting `persona_id` is stored back
into the DreamFi `skills.onyx_persona_id` column.

## Scoped Ask

`POST /api/ask` uses Onyx admin search with optional DreamFi scope filters:

- `topic_id`
- `source_id`
- `source_ids`

When scope is provided, DreamFi sends it as `dreamfi_scope` metadata filters.
The current implementation is indexed retrieval. It does not yet run a planner
that selects authoritative sources from the question itself.

## Connector Sync

Custom connector sync normalizes source payloads into `ConnectorDocument`
records and ingests changed documents into Onyx through `OnyxClient`.

The synced document metadata includes `dreamfi_scope.source_ids`, which lets
Ask, readiness checks, and workflow generation query only the relevant source.

Current custom sync adapters cover:

- Dragonboat
- Metabase
- PostHog
- Google Analytics
- Klaviyo
- NetXD
- Sardine
- Socure

## Freshness Boundary

Onyx document `updated_at` values feed DreamFi freshness scoring and connector
readiness. That is useful for indexed context, but it is not enough for recent
operational fintech questions.

Example: if NetXD has real-time ledger state but Sardine fraud data in Onyx is
two hours old, DreamFi should not infer the fraud reason from NetXD. The
outstanding architecture work is a source-specific runtime freshness contract:

- identify the authoritative source for the claim
- require exact identifiers for recent operational records
- fetch the exact source-of-truth record when indexed data is stale
- block the conclusion if the authoritative source cannot be proven fresh

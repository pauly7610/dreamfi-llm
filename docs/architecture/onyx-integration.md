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

# ADR-010: Minimal DreamFi-owned database

Status: Active

## Context

With Onyx owning all document content, citations, and retrieval, DreamFi's
Postgres only needs to track the eval and prompt lifecycle.

## Decision

DreamFi Postgres tables (all optional outside the skill layer):

- `skills`
- `prompt_versions` (with one-active-per-skill partial unique index)
- `eval_rounds`
- `eval_outputs`
- `gold_examples`
- `publish_log`
- `onyx_document_map`

No `core_entities`, `citations`, or `relationships` tables. Those live in Onyx.

## Consequences

- Migrations stay small and rarely change.
- DreamFi can be reset without touching Onyx's index.
- Cross-system joins happen in application code via `onyx_chat_session_id` and
  `onyx_message_id` columns on `eval_outputs`.

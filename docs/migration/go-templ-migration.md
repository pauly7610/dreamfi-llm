# Go and templ Migration

The VP of Eng direction is clear: backend repos should move to Go and the
frontend should move to templ. This is a full, complete migration to where the
product is at now, not a prototype or partial rewrite. It is a large undertaking,
but each phase should be eng-ready, test-driven, and backed by true code paths
instead of mock-only happy paths.

The current Python FastAPI backend and React/Vite console remain the parity
oracle until every behavior below has Go/templ tests and cutover evidence.

## Guardrails

- Do not modify locked files under `evals/`.
- Do not hand-edit shipped Alembic revisions; add new migrations only.
- Keep all Onyx HTTP behind one client package. In Go that package is
  `internal/onyx`.
- Unit tests must mock Onyx with local HTTP test servers. Live Onyx coverage
  stays opt-in.
- Keep unit database tests on local SQLite/tmp-path equivalents or isolated
  test databases. No network calls in unit tests.

## Migration Slices

1. Phase 1 runtime foundation: Go module, config loading, auth middleware, request IDs,
   health endpoints, Onyx client contract tests, and templ console shell.
2. Phase 2 persistence: Go repository package over the existing SQL schema, with model
   parity tests for prompt versions, rounds, outputs, publish logs, connector
   settings, audit events, and learning-loop tables.
3. Phase 3 Onyx and connector sync: port persona, chat, admin search, document-set, and
   ingestion flows through `internal/onyx`; port custom connector adapters with
   mocked HTTP tests.
4. Phase 4 skill engine and governance: port prompt rendering, confidence scoring,
   eval-round persistence, promotion decisions, publish guards, gold drift, and
   learning proposal flows.
5. Phase 5 workflow API parity: move Ask, workflow catalog, and generated
   artifact creation onto Go routes backed by the real Onyx client, store,
   confidence scoring, export-readiness checks, and audit events.
6. Phase 6 templ console parity: replace React routes with templ pages backed directly
   by Go handlers for Ask, topic rooms, sources, generated artifacts, review,
   trust, methodology, and settings.
7. Phase 7 cutover: switch local/Docker/Railway entry points to the Go binary after all
   old API contracts and frontend smoke paths are covered by Go tests.

## Phase 1 Scope

- `cmd/dreamfi` starts the Go service.
- `internal/config` ports environment resolution for Go drivers.
- `internal/httpapi` ports auth, request IDs, health, ops status, console data,
  and templ console rendering.
- `internal/onyx` is the Go-only choke point for Onyx HTTP.
- `web/templates` owns templ components.
- `Makefile` gets explicit Go/templ targets so reviewers can run the migrated
  path directly.

## Phase 2 Scope

- `internal/store` starts the Go persistence layer over DreamFi's existing SQL
  tables.
- The repository uses dialect-aware placeholders so the migrated code path can
  run against Postgres while tests stay local.
- SQLite-backed tests exercise true persistence paths for skills, prompt
  versions, eval rounds, outputs, publish logs, connector settings, audit
  events, artifact feedback, learning proposals, and replay schedules.
- CI runs templ generation checks and Go tests alongside the existing Python
  and frontend parity suites.
- This phase still does not edit shipped Alembic revisions or cut traffic over
  from the Python app.

## Phase 3 Scope

- `internal/connectors` ports the connector catalog, document-set aliases, and
  source document normalization into Go.
- Custom connector adapters fetch real HTTP payloads from configured source
  APIs and normalize them into DreamFi source documents.
- Connector sync runs persist pulled documents, skip unchanged content hashes,
  and ingest changed documents into Onyx through `internal/onyx`.
- Store coverage now includes `connector_sync_runs` and `connector_documents`.
- Tests use local HTTP servers for source APIs and mocked Onyx ingestion, so the
  migrated path exercises real fetch, persist, and ingest behavior without live
  network dependencies.

## Phase 4 Scope

- `internal/governance` ports confidence scoring, promotion decisions, gold
  regression blocking, canary alerts, and publish guards into Go.
- `internal/skills` ports the fixed nine-skill registry metadata so the Go path
  has the same governed skill set as the current Python backend.
- Tests mirror the existing Python confidence, promotion, publish, and registry
  behavior before the heavier eval runner and prompt-rendering port lands.

## Phase 5 Scope

- `internal/httpapi` ports `/api/ask`, `/api/workflows`, and
  `/api/workflows/generate` onto the Go service.
- Ask uses `internal/onyx` for scoped admin search and records best-effort audit
  events through the Go store when persistence is configured.
- Workflow generation creates chat sessions and sends prompts through
  `internal/onyx`, computes required-section and citation gates, scores
  confidence and export readiness, and persists true eval rounds/outputs.
- `cmd/dreamfi` now wires the Go store into the runtime so the migrated backend
  path is available from the Go binary instead of only from tests.
- This keeps the VP of Eng migration moving in phases: full complete migration
  to where DreamFi is at now, eng-ready, test-driven, and backed by true code
  paths.

## PR Language

Use this language in PR descriptions unless the phase has a stronger, more
specific framing:

> VP of Eng asked for backend repos to move to Go and frontend to move to templ.
> This phase is part of the full complete migration to where DreamFi is at now.
> The goal is eng-ready migration work with test-driven coverage on true code
> paths, not a throwaway rewrite.

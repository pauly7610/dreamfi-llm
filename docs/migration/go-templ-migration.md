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
5. Phase 5 templ console parity: replace React routes with templ pages backed directly
   by Go handlers for Ask, topic rooms, sources, generated artifacts, review,
   trust, methodology, and settings.
6. Phase 6 cutover: switch local/Docker/Railway entry points to the Go binary after all
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

## PR Language

Use this language in PR descriptions unless the phase has a stronger, more
specific framing:

> VP of Eng asked for backend repos to move to Go and frontend to move to templ.
> This phase is part of the full complete migration to where DreamFi is at now.
> The goal is eng-ready migration work with test-driven coverage on true code
> paths, not a throwaway rewrite.

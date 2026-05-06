# Settings / Activation Page

## Purpose

Make DreamFi self-service after the production shell is in place. An admin should be able to add required keys, validate each integration, confirm Onyx document sets, and turn on data persistence without asking engineering to manually inspect the database or backend logs.

This page is not a password vault UI. It is an activation console: it proves that secrets, connectors, storage, jobs, and audit evidence are working.

## User Outcome

An admin can open Settings and answer three questions quickly:

- Is DreamFi connected to persistent production storage?
- Which source systems are active, stale, or missing credentials?
- What still blocks the platform from using real company data?

## Scope

### Environment

Show production readiness for:

- persistent Postgres, not local SQLite
- current Alembic migration head
- Onyx base URL and admin API key
- application auth enabled with non-placeholder secrets
- audit logging enabled and recently writable
- replay and connector-health jobs configured

### Connectors

Support activation status for:

- Jira
- Confluence
- Dragonboat
- Metabase
- PostHog
- Klaviyo
- NetXD
- Sardine
- Socure
- Google Analytics

Each connector should show:

- credential status
- validation status
- expected Onyx document set
- document set existence
- latest health probe result
- freshest retrieved document timestamp
- activation status
- last sync or probe error

### Data Persistence

Confirm persistence for:

- audit events
- eval rounds
- eval outputs
- feedback
- gold examples
- learning proposals
- replay schedules
- replay runs
- production outcomes

## Security Requirements

- Never return raw API keys to the browser after submission.
- Store only masked metadata in DreamFi tables, such as provider, last four characters, created by, validated at, status, and failure reason.
- Prefer a production secret manager for actual secret values.
- For local/dev only, encrypted DB-backed secrets may be allowed behind an explicit setting and a server-side encryption key.
- Every key create, rotate, delete, validation attempt, activation, and deactivation must write an audit event.
- API key form fields must clear after submit and never prefill existing values.
- Connector activation requires admin permission.
- Viewer/editor roles may read status, but cannot read, submit, rotate, or delete secrets.

## TDD Plan

### Backend Unit Tests

Write these before implementation:

- `POST /api/settings/connectors/{id}/secret` stores masked secret metadata and never returns the raw secret.
- Secret submission rejects unsupported connector IDs.
- Secret submission rejects empty, placeholder, or obviously malformed values.
- Secret rotation updates `last_four`, `validated_at`, status, and audit metadata.
- Secret delete deactivates the connector and writes an audit event.
- Connector validation uses the connector-specific validator through a single service boundary.
- Connector validation failure stores a safe failure reason without storing raw provider responses that might contain secrets.
- Activation is blocked until credential validation passes.
- Activation is blocked until the expected Onyx document set exists or is successfully created.
- Activation is blocked until persistence readiness confirms non-SQLite Postgres and current migrations.
- Activation is blocked when audit logging is disabled or audit writes fail.
- Successful activation writes a connector activation audit event.
- Deactivation stops future scheduled probes for that connector.
- Settings status endpoint includes environment, connector, persistence, and job readiness.

### Onyx / Connector Tests

Use `respx` for all Onyx calls:

- Dry-run document-set creation reports what would be created and performs no write.
- Apply mode creates missing `dreamfi-source-{connector}` document sets.
- Existing document sets are reused case-insensitively.
- Search probe marks connector `fresh` when retrieved documents are within freshness policy.
- Search probe marks connector `stale` when latest document is too old.
- Search probe marks connector `empty` when no documents are retrieved.
- Onyx 401/403 produces `validation_failed`, not `active`.
- Onyx 5xx produces `degraded` and keeps prior activation state unchanged.

### Persistence Tests

Use SQLite unit tests where possible and a Postgres-marked integration test for the production gate:

- Local SQLite returns `persistence_ready=false`.
- Missing Alembic version returns `persistence_ready=false`.
- Current migration head returns `persistence_ready=true`.
- Audit write probe creates and reads back a synthetic settings audit event.
- Learning-loop persistence probe can insert and delete a harmless test schedule in a transaction.
- The status endpoint redacts database URLs and secret values.

### Scheduler Tests

- Enabling a connector schedules a health-check job for that connector.
- Disabling a connector prevents new health-check jobs.
- Replay schedule readiness reports due jobs, failed jobs, and latest run.
- Failed connector probes are visible in Settings without marking the app globally down.

### API Authorization Tests

- Unauthenticated requests cannot read settings status when app auth is enabled.
- Viewer can read connector/environment status.
- Editor cannot submit or rotate secrets.
- Admin can submit, validate, activate, deactivate, and delete connector credentials.
- Audit events bind actor id, auth method, role, request id, and target connector.

### Frontend Tests

Use Vitest + Testing Library:

- Settings page renders Environment, Connectors, and Data Persistence tabs.
- Connectors table shows all expected connectors and their statuses.
- Key form clears after successful submit.
- Raw secret text is never rendered after submit.
- Validate action shows loading, success, and failure states.
- Activate button is disabled until validation, document set, persistence, and audit gates pass.
- Activation success changes connector status to active and triggers console data refresh.
- Failure states show actionable copy without exposing raw provider response bodies.
- Viewer role hides secret forms and mutation buttons.
- Admin role sees rotate/delete/validate/activate actions.

### Acceptance / E2E Tests

Run against a local app with mocked Onyx:

- Admin opens Settings, adds a Jira key, validates it, creates the Jira document set, activates Jira, and sees `active`.
- Admin repeats the flow for a connector with bad credentials and sees `validation_failed`; the connector remains inactive.
- Admin opens Data Persistence with SQLite and sees a hard blocker.
- Admin opens Data Persistence with Postgres and current migrations and sees persistence ready.
- After activation, connector readiness appears in Trust and Source workspace surfaces without a manual refresh.
- Audit export includes secret submission, validation, document-set creation, activation, and deactivation events.

## Acceptance Criteria

### Environment

- Settings shows a single overall state: `Ready`, `Blocked`, or `Degraded`.
- `Ready` requires persistent Postgres, current migrations, Onyx reachable, auth configured, audit writable, and scheduled jobs configured.
- SQLite can never show as production-ready.
- Placeholder values such as `change-me-before-deploy`, `onyx_pat_XXX`, and `sk-ant-XXX` are blocked.
- Environment details never expose full URLs with embedded credentials.

### Connector Activation

- A connector cannot become active only because an API key was submitted.
- A connector can become active only after credential validation succeeds.
- A connector can become active only after its expected Onyx document set exists.
- A connector can become active only after a health probe runs and records a result.
- A stale or empty connector may be `configured` or `degraded`, but not `fresh`.
- Activation and deactivation are auditable control events.
- A failed activation leaves the prior connector state unchanged.

### Secret Handling

- Raw secrets are accepted only over authenticated HTTPS in production.
- Raw secrets are not logged, audited, returned, indexed, or stored in normal metadata columns.
- UI shows masked secrets only, such as `••••1234`.
- Rotating a key invalidates the previous key metadata.
- Deleting a key disables the connector and removes the secret reference.

### Persistence

- The page explicitly shows whether DreamFi is writing to persistent Postgres.
- The page shows migration status and the current Alembic revision.
- The page shows the latest successful audit write.
- The page shows counts for persisted eval outputs, feedback, gold examples, replay runs, and production outcomes.
- Data persistence cannot be marked ready while audit writes fail.

### Jobs and Freshness

- Settings shows whether connector health checks are scheduled.
- Settings shows whether replay jobs are scheduled.
- Each connector shows the latest probe time and latest retrieved document timestamp.
- A connector becomes `stale` when the freshest document exceeds the configured freshness window.
- Job failures appear as degraded operational status, not silent success.

### UX

- The first empty-state screen tells the admin exactly what is missing.
- Each blocker has one obvious next action.
- Mutating actions use explicit buttons: Validate, Create document set, Activate, Rotate, Delete, Deactivate.
- Dangerous actions require confirmation.
- Loading states prevent duplicate submission.
- Errors are short, actionable, and safe to screenshot.

## Definition of Done

- Backend tests cover settings status, secret metadata, validation, activation gates, document-set setup, persistence readiness, scheduler readiness, auth, and audit events.
- Frontend tests cover page rendering, role-based controls, key submission, validation, activation, error states, and redaction.
- E2E acceptance tests cover happy path, bad credentials, persistence blocker, and audit evidence.
- `ruff`, backend pytest, frontend Vitest, frontend build, and coverage checks pass.
- No raw secret value appears in logs, API responses, audit metadata, local storage, or rendered HTML.
- Settings can truthfully answer: "What is blocking DreamFi from operating on real company data?"

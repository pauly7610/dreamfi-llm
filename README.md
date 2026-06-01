# DreamFi

This repo contains DreamFi's internal ProductOS, built on top of [Onyx](https://github.com/onyx-dot-app/onyx). It gives the product team a place to ask questions, inspect evidence from connected systems, manage topic rooms, and generate reviewable artifacts. The backend handles prompt rendering, retrieval, evaluation, confidence scoring, audit logging, and publish controls.

![DreamFi ProductOS trust console](../docs/screenshots/dreamfi-llm-console.png)

## Product Brief

| Lens | Summary |
| --- | --- |
| Problem | Product questions, source evidence, generated artifacts, and trust decisions can live in separate systems, which makes AI-assisted work hard to verify or publish safely. |
| What we built | A governed ProductOS on top of Onyx with Ask, topic rooms, source workspaces, artifact generation, eval-backed skills, confidence scoring, audit logs, and publish controls. |
| Business value | DreamFi can turn product evidence into reusable work while keeping citations, freshness, review state, and approval history attached to the output. |
| Technical approach | Go/templ console paths, Python ops, eval, and context workflows, Postgres persistence, scoped Onyx retrieval, custom connector sync, context-bundle APIs, Jinja prompt versions, immutable eval rounds, confidence scoring, export readiness, and audit-safe APIs. |
| Proposed solutions | Keep connector context lean, keep source freshness explicit at runtime, preserve Go/templ parity with Python support APIs, keep replay schedules covering high-risk workflows, and turn freshness plus eval failures into harder blockers before publish. |

## What the system does

- Gives DreamFi's product team a shared frontend for asking questions, browsing source systems, reviewing topic rooms, and managing generated work.
- Seeds one Onyx document set and one Onyx persona per DreamFi skill.
- Renders Jinja prompt templates for the active prompt version of each skill.
- Sends prompts through `dreamfi.onyx.client.OnyxClient`, captures citations, and reads source freshness from retrieved documents.
- Scopes Ask searches with topic and source filters when a caller provides `topic_id`, `source_id`, or `source_ids`.
- Builds typed context bundles through `/v1/context/ask`, with source-grounded claims, open questions, topic linking, and memory.
- Runs immutable eval runners for every generated output.
- Computes per-output confidence from eval score, citation count, freshness, and hard-gate status.
- Stores prompt versions, eval rounds, outputs, publish logs, gold examples, and drift events in SQL.
- Computes export readiness for artifacts that may be safe to review or publish.
- Writes structured audit events for access, generation, governance, configuration, and publish decisions.
- Captures human feedback and production outcomes so recurring failures can become reviewed prompt-improvement candidates.
- Exposes an operator console plus HTTP endpoints for round execution, history, promotion, and publish decisions.

## Internal Access

DreamFi ProductOS is an internal operator tool. Browser users authenticate with
HTTP Basic auth, and API clients can use `Authorization: Bearer <token>`.
Placeholder auth values are rejected at runtime so local defaults cannot drift
into production.

The Go service sets baseline browser security headers, uses request timeouts,
and shuts down gracefully on process termination. Connector credentials are
never returned through API payloads; custom connector keys are encrypted at rest
when `DREAMFI_CONNECTOR_SECRET_KEY` is configured.

## ProductOS

The frontend is organized around product work rather than model operations. The main surfaces are:

- `Ask`: start with a product question, retrieve evidence from connected systems, and keep citations attached to the answer.
- `Topic rooms`: work inside recurring decision spaces like KYC conversion, onboarding, funding, and lifecycle messaging.
- `Source workspaces`: open connected systems such as Jira, Confluence, Dragonboat, Metabase, PostHog, Klaviyo, NetXD, Sardine, Socure, and Google Analytics in a product-friendly workspace view.
- `Generated artifacts`: turn grounded context into workflows like weekly PM briefs, technical PRDs, and risk BRDs.
- `Trust review`: inspect blocked work, risky work, publish readiness, and the health of the connected evidence behind each artifact.

The intended operating model is:

1. Start with the product question.
2. Narrow into the right topic room or source workspace.
3. Inspect the evidence and gaps.
4. Generate a reusable artifact from that grounded context.
5. Use the trust checks to decide whether the output needs review, can move forward, or can publish.

The console includes a Settings / Activation page for confirming Onyx document
sets, validating source freshness, and proving persistent storage readiness.
Jira and Confluence stay native in Onyx. Dragonboat, Metabase, PostHog, Google
Analytics, Klaviyo, NetXD, Sardine, and Socure use DreamFi's custom connector
sync layer or the bridge ingest endpoint. DreamFi never returns raw API keys;
custom connector keys are encrypted at rest when
`DREAMFI_CONNECTOR_SECRET_KEY` is configured.

## Freshness model

DreamFi treats connectors as available data surfaces, not automatic prompt
context. The current Ask path is intentionally scoped, but it is still indexed
retrieval:

```text
Question
    |
    v
Optional topic/source scope
    |
    v
Onyx admin search with dreamfi_scope filters
    |
    v
Citations + updated_at freshness signals
```

Connector readiness checks prove document-set presence, scoped retrieval, and
document freshness using `DREAMFI_CONNECTOR_STALE_AFTER_DAYS`. Workflow
confidence and export readiness also read Onyx document `updated_at` values, so
stale evidence can lower trust and block publish decisions.

Ask responses include a `source_plan` alongside the answer and citations. The
plan tells the console whether the question was scoped, which authoritative
sources were used, whether the question is freshness sensitive, and what
blockers remain before the answer should be treated as decision-grade.

The repo does not yet ship identifier-scoped live reads for recent operational
questions. For fintech cases like a fraud decline that happened two hours ago,
the next architecture step is a source-specific freshness contract: if Sardine
fraud data is stale, DreamFi should either fetch the exact Sardine decision by
identifier or block the fraud conclusion. A fresh NetXD ledger record should not
stand in for stale Sardine fraud evidence.

## Custom connector sync

Custom connectors follow the same control path:

```text
Settings config + encrypted key
        |
        v
Provider adapter or source bridge
        |
        v
ConnectorDocument persistence
        |
        v
Onyx ingestion via OnyxClient
        |
        v
Freshness probe + activation gate
```

The first adapter set covers the current non-native sources:

- Dragonboat: roadmap initiatives, features, and objectives from configured REST endpoints.
- Metabase: cards and dashboards through the Metabase API.
- PostHog: insights and dashboards for a configured project.
- Google Analytics: GA4 report rows for a configured property.
- Klaviyo: campaigns, flows, and segments.
- NetXD, Sardine, and Socure: configurable REST endpoint pulls for payment, risk, and identity evidence.

The Settings page exposes the sync knobs for these sources: base URLs,
endpoint paths, REST auth header/scheme where applicable, GA4 report date
ranges, GA4 dimensions/metrics, Klaviyo API revision, and optional DreamFi
metadata defaults for product area, topic IDs, and owner.

Every pulled item is normalized into a `ConnectorDocument`, tagged with
`dreamfi_scope.source_ids`, persisted in Postgres, and ingested into Onyx through
`dreamfi.onyx.client.OnyxClient`. Sync attempts are stored in
`connector_sync_runs`, including counts, status, reason, and timestamps. For
systems whose production API shape needs a custom exporter, clients can post
pre-normalized records to `/api/settings/connectors/{connector_id}/documents`;
DreamFi still persists and ingests them through the same path.

Custom sync remains platform plumbing. It warms indexed context and keeps
Onyx-backed source packets useful. It is not an agent-facing skill and it is
not designed to run every second.

## Skill layer

DreamFi's active Python skill registry currently ships 3 PM-adjacent
eval-backed skills:

- `meeting_summary`
- `agent_system_prompt`
- `support_agent`

Those skills are the governed generation layer behind the product workflows.
They provide prompt versioning, evals, scoring, promotion checks, and publish
checks. The six older marketing/copy skills remain on disk under `evals/` and
in `ARCHIVED_SKILLS` for historical compatibility, but they are not part of the
active Python registry and do not seed or surface in the Python console path.

Current migration notes:

- `make seed` and the Python eval path use the 3-skill active registry as the operational source of truth.
- The Go `internal/skills` registry follows the same 3-skill active set. Historical skills are kept separately for compatibility and audit history.
- The live workflow catalog is limited to `weekly-brief`, `technical-prd`, and `risk-brd`. Business PRD generation was removed from the active catalog until it has a real active skill mapping.

## Workflow traces and skill candidates

DreamFi can now track repeated user workflows as reviewed skill candidates.
This is the practical version of "putting your coworker into a skill": capture
the repeatable work pattern, mine it for contracts, then let a human decide
whether it should become a governed skill.

Workflow traces store:

- workflow type, workspace, actor, topic, and outcome
- selected source systems and required identifiers
- ordered steps, tools, accepted evidence, and rejected evidence
- human edits and final artifact references
- a redacted starter-question pattern plus a SHA-256 hash, not the raw starter question

Skill mining clusters non-private traces by workspace and workflow type. When a
workflow repeats often enough, DreamFi creates a draft `SkillCandidate` with:

- intent summary
- required inputs
- source contract
- tool plan
- freshness contract
- answer contract
- refusal rules
- eval seed cases based on redacted historical traces

This does not modify the active skill registry or write locked files under
`evals/`. It gives Product and Engineering a reviewable candidate package for
the next real skill PR.

## Core flow

```text
Onyx doc sets + personas
        |
        v
PromptVersion + Jinja rendering
        |
        v
Onyx chat generation via OnyxClient
        |
        v
Locked eval runner + confidence scoring
        |
        v
EvalRound / EvalOutput persistence + artifacts
        |
        +--> PromotionGate
        |
        +--> PublishGuard
        |
        v
Console + API review surfaces
```

In practice, a round looks like this:

1. Seed skills and their Onyx personas with `make seed`.
2. Run a round for a skill with `make run-round SKILL=meeting_summary` or `POST /v1/skills/{skill_id}/eval-round`.
3. DreamFi generates `N` outputs per locked test input, evaluates each one, and writes artifacts under `evals/results/<skill>/rounds/<round_id>/`.
4. The round score is compared against the latest active prompt version.
5. Promotion is allowed only when the new round clears the improvement threshold and does not regress.
6. Publish is allowed only when the output passes the hard gate and meets the confidence threshold.

## Audit logging

DreamFi writes persistent audit events to `audit_events`. The audit trail is
intended to support SOC 2-style evidence review, not only application debugging.
Each event records:

- actor id/type and auth method
- request id, method, path, status code, client IP, and user agent
- event category/action/outcome/severity
- target type/id such as an eval round, output, prompt version, topic, or Onyx search
- safe structured metadata, with prompt text, generated text, raw questions, tokens, passwords, and API keys redacted or hashed
- deterministic `event_hash` so exported evidence can be checked for row-level tampering

The app records request-level access events for non-static routes and explicit
business-control events for Ask searches, workflow generation, eval rounds,
promotion previews, prompt promotions, publish attempts, console reads, and
topic changes. `DREAMFI_AUDIT_ENABLED=false` disables audit writes for local
debugging only. `DREAMFI_AUDIT_LOG_READS=false` suppresses read-route access
events while still recording mutating and control-decision events.

## Learning loop

DreamFi's learning loop is automatic where it is useful and reviewed where it
matters. The system captures review outcomes, clusters repeated failures,
proposes prompt changes, grows gold examples from reviewed artifacts, replays
important cases, and records whether generated work was used in decisions.
Approved proposals create inactive prompt versions; activation still goes
through eval and promotion checks.

The loop is:

```text
Artifact output
    |
    v
Human feedback + production outcome
    |
    +--> Gold exemplar/regression/canary growth
    |
    +--> Failure clustering
             |
             v
        Learning proposal
             |
             v
        Human approval creates inactive prompt candidate
             |
             v
        Scheduled gold/workflow replay + promotion gate
```

This keeps prompt changes traceable: who approved the proposal, what evidence
supported it, which prompt version was created, and how it performed on replay.

## API surface

The Go service currently exposes the cutover path:

- `GET /ready` - liveness endpoint used by deploy health checks.
- `GET /health` - service status plus Onyx reachability.
- `GET /api/ops/status` - lightweight operational readiness payload for the Go service.
- `GET /api/console` - JSON payload for the templ operator console.
- `POST /api/ask` - run a scoped Onyx evidence search for an Ask question and return the answer, citations, and source plan.
- `GET /api/workflows` - list console artifact workflow slugs and their backing skill IDs.
- `POST /api/workflows/generate` - generate a weekly brief, technical PRD, or risk BRD artifact from current console context.
- `GET /console` - active operator UI rendered by the Go/templ service.

The Python app remains the ops, eval, learning, settings, and context-engine
support layer while migration parity continues:

- `GET /v1/skills/{skill_id}/history` - recent eval rounds for a skill.
- `POST /v1/skills/{skill_id}/eval-round` - run a new eval round.
- `POST /v1/skills/{skill_id}/promote` - activate a prompt version if promotion rules pass.
- `POST /v1/skills/{skill_id}/publish` - record and enforce publish policy for an output. `return-only` is the supported destination until a real destination writer is configured.
- `POST /v1/context/ask` - build a persisted `ContextBundle` with grounded claims, open questions, topic links, and memory.
- `POST /api/ask` - run a scoped Onyx evidence search for an Ask question and return the answer, citations, and source plan.
- `POST /api/workflows/generate` and `GET /api/workflows` - Python parity versions of the console artifact APIs.
- `POST /api/learning/feedback` - record approved, edited, or rejected artifact review outcomes.
- `GET /api/learning/failure-clusters` - group recurring failures by workflow, source, criteria, missing section, evidence, freshness, and readiness signals.
- `POST /api/learning/proposals/generate` - create reviewed prompt-improvement candidates from repeated failure clusters.
- `POST /api/learning/proposals/{proposal_id}/approve` - create an inactive prompt version from an approved learning proposal.
- `POST /api/learning/feedback/{feedback_id}/gold` - convert reviewed artifacts into gold exemplars, regressions, counter examples, or canaries.
- `POST /api/learning/replay-schedules` and `POST /api/learning/replay-schedules/run-due` - schedule and run gold/workflow replay.
- `POST /api/learning/outcomes` - record whether generated work was published, revised, ignored, reverted, or used in a decision.
- `POST /api/learning/workflow-traces` - record a redacted workflow trace for mining repeatable expert work.
- `GET /api/learning/workflow-traces` - list recent non-private workflow traces.
- `POST /api/learning/skill-candidates/generate` - mine repeated traces into draft skill candidates.
- `GET /api/learning/skill-candidates` - list draft, approved, or rejected skill candidates.
- `POST /api/learning/skill-candidates/{candidate_id}/approve` and `/reject` - review a candidate without mutating the active skill registry.
- `GET /api/settings/status` - read environment, persistence, job, and connector activation readiness.
- `POST /api/settings/connectors/{connector_id}/secret` - save connector credentials without returning or auditing raw API keys; custom connector keys are encrypted when app storage is used.
- `POST /api/settings/connectors/{connector_id}/config` - save non-secret setup values such as base URLs, project IDs, property IDs, and endpoint paths.
- `POST /api/settings/connectors/{connector_id}/sync` - pull a custom connector, persist normalized documents, ingest changed records into Onyx, and record a sync run.
- `POST /api/settings/connectors/{connector_id}/documents` - accept pre-normalized documents from an external source bridge/export job.
- `POST /api/settings/connectors/{connector_id}/document-set`, `/validate`, `/activate`, and `/deactivate` - confirm Onyx document sets, run freshness probes, and gate activation.
- `GET /api/console` - JSON payload for the operator console.
- `GET /console` - Python console/parity UI when running the FastAPI app.

## Frontend

The frontend currently includes:

- a home/product source room for cross-system product questions
- ask flows with citations attached to answers
- topic rooms for recurring product decisions
- source directories and connector-specific workspaces
- artifact views for generated work
- review queues for blocked and risky artifacts
- trust and methodology pages for system health and operating model
- a settings page for connector activation, key redaction, Onyx document-set confirmation, and persistence gates

The review layer summarizes:

- skill coverage and active prompt versions
- recent round scores and improvement history
- artifact queue state such as `blocked`, `needs_review`, `publish_ready`, and `published`
- publish activity and blocked publish attempts
- integration metadata used by the current UI

The React console source remains under `generators/web/` as the parity oracle
while the frontend moves to templ. The Go service now serves the active
store-backed templ console from `web/templates/`.

## Local setup

1. Create a local Python environment and install the project:

```bash
python -m venv .venv
# activate the venv for your shell
pip install -e ".[dev]"
```

2. Copy `.env.example` to `.env` and set at least `ONYX_BASE_URL` and `ONYX_API_KEY`.
   Also replace `DREAMFI_AUTH_PASSWORD` and `DREAMFI_API_TOKEN`; the console and
   mutating API routes are protected by HTTP Basic auth or Bearer token auth, and
   placeholder auth values are rejected at runtime.
   Set `DREAMFI_CONNECTOR_SECRET_KEY` before saving custom connector API keys
   from the Settings page.

3. Choose one startup path:

Recommended end-to-end bootstrap:

```bash
make bootstrap
```

If Onyx is already running and you want just the DreamFi stack:

```bash
make dreamfi-up
make seed
```

If you want to run the API directly instead of Docker, keep Alembic and seeding
on the Python toolchain, then start the Go service:

```bash
alembic upgrade head
make seed
PORT=5001 make run-go
```

4. Open Onyx at [http://localhost:3000](http://localhost:3000) and DreamFi at [http://localhost:5001/console](http://localhost:5001/console).

`make bootstrap` runs the local Onyx installer script and then starts DreamFi. That path requires a `bash`-compatible shell and `curl`.

## API-key-ready setup

Most setup can be prepared before live source credentials are available. The
expected flow is:

```bash
make migrate
make seed-local
make seed-demo
make setup-env-check
make ops-status
```

After Onyx admin access is available:

```bash
make setup-docsets APPLY=1
make seed
make validate-connectors
```

`make setup-docsets APPLY=1` creates the expected source document sets such as
`dreamfi-source-jira`, `dreamfi-source-socure`, and
`dreamfi-source-confluence`. `make validate-connectors` then checks that each
document set exists and, when probing is enabled, that scoped retrieval returns
fresh evidence.

`make seed-local` is safe without Onyx credentials. It seeds the locked skill
registry and active prompt versions locally. `make seed-demo` adds realistic
topics, artifacts, feedback, a learning proposal, a production outcome, and a
replay schedule so the review flow can be evaluated before real connectors are
live.

`make run-replay` runs due gold/workflow replay schedules. In production, run it
from cron, Railway scheduled jobs, or the scheduler you use for internal tools.
`make ops-status` prints the same rich readiness payload exposed by the Python
`GET /api/ops/status` route, covering environment placeholders, database
migration version, Onyx reachability, connector readiness, replay failures, and
audit-log activity. The Go service also exposes `GET /api/ops/status`, but that
cutover endpoint is currently a lighter health payload.

## Environment

Important settings from `.env.example`:

- `DATABASE_URL` or the `PG*` variables for the SQL database
- `DREAMFI_AUTH_ENABLED`, `DREAMFI_AUTH_USERNAME`, `DREAMFI_AUTH_PASSWORD`, and
  `DREAMFI_API_TOKEN`
- `ONYX_BASE_URL`
- `ONYX_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `DEFAULT_LLM_MODEL`
- `FALLBACK_LLM_MODELS`
- `DREAMFI_CONFIDENCE_THRESHOLD`
- `DREAMFI_IMPROVEMENT_THRESHOLD`
- `DREAMFI_FRESHNESS_HALFLIFE_DAYS`
- `DREAMFI_ASK_SEARCH_LIMIT`
- `DREAMFI_CLAIM_LINEAGE_TARGET_CITATIONS`
- `DREAMFI_MIN_OUTPUTS_PER_EVAL_INPUT`
- `DREAMFI_MAX_OUTPUTS_PER_EVAL_INPUT`
- `DREAMFI_PROBE_CONNECTOR_STATUS`
- `DREAMFI_CONNECTOR_PROBE_SEARCH_LIMIT`
- `DREAMFI_CONNECTOR_STALE_AFTER_DAYS`
- `DREAMFI_CONNECTOR_HTTP_TIMEOUT_SECONDS`
- `DREAMFI_CONNECTOR_SYNC_BATCH_SIZE`
- `DREAMFI_CONNECTOR_SECRET_KEY`
- `DREAMFI_WORKFLOW_MIN_CITATIONS`
- `DREAMFI_WORKFLOW_MIN_SECTION_WORDS`
- `DREAMFI_WORKFLOW_REQUIRE_SCOPE`
- `DREAMFI_AUDIT_ENABLED`
- `DREAMFI_AUDIT_LOG_READS`
- `DREAMFI_LEARNING_CLUSTER_MIN_COUNT`
- `DREAMFI_LEARNING_CLUSTER_WINDOW_DAYS`
- `DREAMFI_LEARNING_STALE_FRESHNESS_THRESHOLD`
- `DREAMFI_LEARNING_REPLAY_DEFAULT_CADENCE_DAYS`
- `DREAMFI_SKILL_MINING_MIN_TRACES`
- `DREAMFI_SKILL_MINING_WINDOW_DAYS`
- `DREAMFI_SKILL_MINING_EVAL_SEED_LIMIT`
- `DREAMFI_SLO_HARD_GATE_PASS_RATE`
- `DREAMFI_SLO_BLOCKED_RATE`
- `DREAMFI_SLO_PUBLISH_SUCCESS_RATE`

## Connector readiness

DreamFi reads connector readiness from Onyx document sets and a small scoped
search probe. After you create or sync a source connector, create an Onyx
document set named with one of these patterns:

- `dreamfi-source-<connector-id>`
- `dreamfi-<connector-id>`
- `dreamfi-<connector-name>`

For example: `dreamfi-source-jira`, `dreamfi-source-socure`, or
`dreamfi-google-analytics`. Connectors with a matching document set are shown as
`connected` only when the scoped probe also returns a fresh document. Missing
document sets are shown as `not_configured`; stale, empty, or unreachable
sources are shown as `degraded`. The probe uses the same
`dreamfi_scope.source_ids` metadata filter as the Ask and workflow APIs, so each
connector's documents should carry its connector id, such as `jira` or `socure`.

Readiness is not the same thing as answer freshness. Readiness says the
connector is configured and has retrievable indexed evidence. For recent
operational questions, the repo still needs source-specific runtime freshness
contracts so DreamFi can decide whether indexed evidence is current enough,
whether to fetch an exact source record, or whether to block the conclusion.

## Development

```bash
make verify       # ruff, Python tests, Go tests, and Go build
make test         # unit + mocked integration tests
make test-go      # Go backend + templ unit tests
make build-go     # build the Go DreamFi service
make test-live    # live Onyx tests only
make lint         # ruff
make format       # ruff format
```

From the repo root, the full local parity check is:

```bash
yarn llm:verify
```

Notes:

- Unit tests mock Onyx with `respx`.
- Live Onyx tests are marked `live_onyx`.
- Runtime artifacts are written under `evals/results/`, but locked eval templates and runners under `evals/` are repository-controlled and should not be hand-edited.

## Repo layout

- `dreamfi/` - backend app, Onyx client, trust logic, DB models, and skill engine
- `generators/web/` - React operator console source and built assets
- `scripts/` - local bootstrap, seeding, and eval round CLIs
- `deployment/` - Docker Compose for local Postgres + API
- `evals/` - locked eval templates and runners, plus generated results under `evals/results/`
- `tests/` - unit and live-Onyx integration coverage

## Deployment

The repo includes a Dockerfile and `railway.json`. Railway health checks hit
`GET /ready`, and the container entrypoint runs `alembic upgrade head` before
starting the Go DreamFi binary.

# DreamFi

This repo contains DreamFi's internal ProductOS, built on top of [Onyx](https://github.com/onyx-dot-app/onyx). It gives the product team a place to ask questions, inspect evidence from connected systems, manage topic rooms, and generate reviewable artifacts. The backend handles prompt rendering, retrieval, evaluation, confidence scoring, audit logging, and publish controls.

## What the system does

- Gives DreamFi's product team a shared frontend for asking questions, browsing source systems, reviewing topic rooms, and managing generated work.
- Seeds one Onyx document set and one Onyx persona per DreamFi skill.
- Renders Jinja prompt templates for the active prompt version of each skill.
- Sends prompts through `dreamfi.onyx.client.OnyxClient`, captures citations, and reads source freshness from retrieved documents.
- Runs immutable eval runners for every generated output.
- Computes per-output confidence from eval score, citation count, freshness, and hard-gate status.
- Stores prompt versions, eval rounds, outputs, publish logs, gold examples, and drift events in SQL.
- Computes export readiness for artifacts that may be safe to review or publish.
- Writes structured audit events for access, generation, governance, configuration, and publish decisions.
- Captures human feedback and production outcomes so recurring failures can become reviewed prompt-improvement candidates.
- Exposes an operator console plus HTTP endpoints for round execution, history, promotion, and publish decisions.

## ProductOS

The frontend is organized around product work rather than model operations. The main surfaces are:

- `Ask`: start with a product question, retrieve evidence from connected systems, and keep citations attached to the answer.
- `Topic rooms`: work inside recurring decision spaces like KYC conversion, onboarding, funding, and lifecycle messaging.
- `Source workspaces`: open connected systems such as Jira, Confluence, Dragonboat, Metabase, PostHog, Klaviyo, NetXD, Sardine, Socure, and Google Analytics in a product-friendly workspace view.
- `Generated artifacts`: turn grounded context into workflows like weekly PM briefs, technical PRDs, business PRDs, and risk BRDs.
- `Trust review`: inspect blocked work, risky work, publish readiness, and the health of the connected evidence behind each artifact.

The intended operating model is:

1. Start with the product question.
2. Narrow into the right topic room or source workspace.
3. Inspect the evidence and gaps.
4. Generate a reusable artifact from that grounded context.
5. Use the trust checks to decide whether the output needs review, can move forward, or can publish.

The console includes a Settings / Activation page for validating connector
credentials, confirming Onyx document sets, and proving persistent storage
readiness without exposing raw API keys.

## Skill layer

DreamFi currently ships a fixed skill layer of 9 locked eval-backed skills:

- `meeting_summary`
- `cold_email`
- `landing_page_copy`
- `newsletter_headline`
- `product_description`
- `resume_bullet`
- `short_form_script`
- `agent_system_prompt`
- `support_agent`

Those skills are the governed generation layer behind the product workflows. They provide prompt versioning, evals, scoring, promotion checks, and publish checks.

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

The current backend exposes:

- `GET /ready` - liveness endpoint used by deploy health checks.
- `GET /health` - service status plus Onyx reachability.
- `GET /v1/skills/{skill_id}/history` - recent eval rounds for a skill.
- `POST /v1/skills/{skill_id}/eval-round` - run a new eval round.
- `POST /v1/skills/{skill_id}/promote` - activate a prompt version if promotion rules pass.
- `POST /v1/skills/{skill_id}/publish` - record and enforce publish policy for an output. `return-only` is the supported destination until a real destination writer is configured.
- `POST /api/ask` - run a scoped Onyx evidence search for an Ask question.
- `POST /api/workflows/generate` - generate a weekly brief, technical PRD, business PRD, or risk BRD artifact from current console context.
- `GET /api/workflows` - list console artifact workflow slugs and their backing skill IDs.
- `POST /api/learning/feedback` - record approved, edited, or rejected artifact review outcomes.
- `GET /api/learning/failure-clusters` - group recurring failures by workflow, source, criteria, missing section, evidence, freshness, and readiness signals.
- `POST /api/learning/proposals/generate` - create reviewed prompt-improvement candidates from repeated failure clusters.
- `POST /api/learning/proposals/{proposal_id}/approve` - create an inactive prompt version from an approved learning proposal.
- `POST /api/learning/feedback/{feedback_id}/gold` - convert reviewed artifacts into gold exemplars, regressions, counter examples, or canaries.
- `POST /api/learning/replay-schedules` and `POST /api/learning/replay-schedules/run-due` - schedule and run gold/workflow replay.
- `POST /api/learning/outcomes` - record whether generated work was published, revised, ignored, reverted, or used in a decision.
- `GET /api/settings/status` - read environment, persistence, job, and connector activation readiness.
- `POST /api/settings/connectors/{connector_id}/secret` - save masked connector credential metadata without returning or storing raw API keys.
- `POST /api/settings/connectors/{connector_id}/document-set`, `/validate`, `/activate`, and `/deactivate` - confirm Onyx document sets, run freshness probes, and gate activation.
- `GET /api/console` - JSON payload for the operator console.
- `GET /console` - operator UI, backed by the checked-in React build when present.

## Frontend

The frontend currently includes:

- a home/product source room for cross-system product questions
- ask flows with evidence receipts
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

The React console source lives under `generators/web/`, and the backend serves the built assets from `generators/web/dist/` when they exist.

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

If you want to run the API directly from your local Python environment instead of Docker:

```bash
alembic upgrade head
make seed
uvicorn dreamfi.api.app:app --host 0.0.0.0 --port 5001
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
`make ops-status` prints the same readiness payload exposed at
`GET /api/ops/status`, covering environment placeholders, database migration
version, Onyx reachability, connector readiness, replay failures, and audit-log
activity.

## Environment

Important settings from `.env.example`:

- `DATABASE_URL` or the `PG*` variables for the SQL database
- `DREAMFI_AUTH_ENABLED`, `DREAMFI_AUTH_USERNAME`, `DREAMFI_AUTH_PASSWORD`, and
  `DREAMFI_API_TOKEN`
- `ONYX_BASE_URL`
- `ONYX_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEFAULT_LLM_MODEL`
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
- `DREAMFI_WORKFLOW_MIN_CITATIONS`
- `DREAMFI_WORKFLOW_MIN_SECTION_WORDS`
- `DREAMFI_WORKFLOW_REQUIRE_SCOPE`
- `DREAMFI_AUDIT_ENABLED`
- `DREAMFI_AUDIT_LOG_READS`
- `DREAMFI_LEARNING_CLUSTER_MIN_COUNT`
- `DREAMFI_LEARNING_CLUSTER_WINDOW_DAYS`
- `DREAMFI_LEARNING_STALE_FRESHNESS_THRESHOLD`
- `DREAMFI_LEARNING_REPLAY_DEFAULT_CADENCE_DAYS`
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

## Development

```bash
make test        # unit + mocked integration tests
make test-live   # live Onyx tests only
make lint        # ruff
make format      # ruff format
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

The repo includes a Dockerfile and `railway.json`. Railway health checks hit `GET /ready`, and the container entrypoint runs `alembic upgrade head` before starting `uvicorn`.

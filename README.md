# DreamFi

DreamFi is a FastAPI service and operator console that sits on top of [Onyx](https://github.com/onyx-dot-app/onyx). It runs grounded generation for a fixed set of skills, evaluates every output against locked skill-specific gates, scores trust signals like freshness and citations, and only allows promotion or publish when the artifact clears policy.

## What the system does

- Seeds one Onyx document set and one Onyx persona per DreamFi skill.
- Renders Jinja prompt templates for the active prompt version of each skill.
- Sends prompts through `dreamfi.onyx.client.OnyxClient`, captures citations, and reads source freshness from retrieved documents.
- Runs immutable eval runners for every generated output.
- Computes per-output confidence from eval score, citation count, freshness, and hard-gate status.
- Stores prompt versions, eval rounds, outputs, publish logs, gold examples, and drift events in SQL.
- Computes export readiness for artifacts that may be safe to review or publish.
- Exposes an operator console plus HTTP endpoints for round execution, history, promotion, and publish decisions.

## Locked skills

DreamFi currently ships 9 locked skills:

- `meeting_summary`
- `cold_email`
- `landing_page_copy`
- `newsletter_headline`
- `product_description`
- `resume_bullet`
- `short_form_script`
- `agent_system_prompt`
- `support_agent`

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

## API surface

The current backend exposes:

- `GET /ready` - liveness endpoint used by deploy health checks.
- `GET /health` - service status plus Onyx reachability.
- `GET /v1/skills/{skill_id}/history` - recent eval rounds for a skill.
- `POST /v1/skills/{skill_id}/eval-round` - run a new eval round.
- `POST /v1/skills/{skill_id}/promote` - activate a prompt version if promotion rules pass.
- `POST /v1/skills/{skill_id}/publish` - record and enforce publish policy for an output.
- `GET /api/console` - JSON payload for the operator console.
- `GET /console` - operator UI, backed by the checked-in React build when present.

## Operator console

The console is the review surface for the system. Today it summarizes:

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

## Environment

Important settings from `.env.example`:

- `DATABASE_URL` or the `PG*` variables for the SQL database
- `ONYX_BASE_URL`
- `ONYX_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEFAULT_LLM_MODEL`
- `DREAMFI_CONFIDENCE_THRESHOLD`
- `DREAMFI_IMPROVEMENT_THRESHOLD`
- `DREAMFI_FRESHNESS_HALFLIFE_DAYS`

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

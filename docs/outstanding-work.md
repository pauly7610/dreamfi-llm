# DreamFi — Outstanding Work

> **Re-anchored mission:** DreamFi is a **shared context engine for PMs** — a
> living understanding of the product, its Jira issues, its analytics, its docs,
> and its decisions, that any PM on the team can query, trust, and reuse.
> Generation and publishing are *outputs* of that brain, not the brain itself.

This is the gap between today's repo and that mission, in priority order. Every
item lists scope, files, acceptance criteria, and TDD steps so it can be handed
straight to an implementation agent.

---

## North star, restated

A PM should be able to ask DreamFi:

- "What's actually shipping in the activation squad this sprint, and which
  tickets are at risk?"
- "Why did week-2 retention drop, and what does each source say about it?"
- "Show me everything we know about the onboarding redesign — the PRD, the Jira
  epic, the dashboard, the research, the open questions."
- "Has anyone on the team already answered this?"

…and get a single grounded, cited, current answer with a confidence breakdown —
*not* a generated marketing email.

Today the repo can generate a cold email or a meeting summary against Onyx
retrieval (see `dreamfi/skills/registry.py`, 9 locked skills). It cannot answer
any of the four questions above. The work below closes that gap.

---

## How this list is organized

- **C-phases (Context)** — the shared-context engine itself. *The new spine.*
- **T-phases (Trust)** — make the context defensible. Carried forward.
- **S-phases (Skills)** — generation skills that *consume* the context engine.
- **P-phases (Productization)** — multi-tenancy, model routing, publish, etc.
- **X-phases (Cleanup)** — debt blocking the above.

C, T, S, P, X. Within each, items are ordered by dependency.

---

## Phase X — Cleanup we have to do first (~1 day)

### X1. Wire export readiness end-to-end

**Status today (verified against the repo):** the model columns
(`eval_outputs.export_readiness`, `eval_outputs.export_breakdown_json`) and the
`compute_export_readiness` function in `dreamfi/trust/artifact.py` already
exist — but nothing calls `compute_export_readiness`, and
`PublishGuard.check` (in `dreamfi/promotion/gate.py`) only looks at
`pass_fail` and `confidence`. `design.md` §4.7 promises three enforcement
layers; today there are zero. X1 wires them up.

**Files to change**

- `dreamfi/skills/engine.py` — after `eval_result` and `conf` are computed in
  `SkillEngine.generate`, build an `ExportReadinessInput`, call
  `compute_export_readiness`, and persist `export_readiness` +
  `export_breakdown_json` on the `EvalOutput` row.
- `dreamfi/promotion/gate.py::PublishGuard.check` — accept `export_readiness`
  and a workspace threshold (default from settings); refuse below threshold;
  refuse when `export_readiness is None`.
- `dreamfi/api/routes/publish.py` — pass `output.export_readiness` to the
  guard.
- `dreamfi/config.py` — add `dreamfi_export_readiness_threshold` (default
  `0.80`) alongside the other thresholds.
- `dreamfi/db/migrations/versions/20260420_0003_publish_log_trigger.py` — new
  migration adding a Postgres `BEFORE INSERT` trigger on `publish_log` that
  raises if the cited output's `export_readiness` is NULL or below the
  threshold. Sqlite-only environments skip the trigger.

**Tests (write first)**

- `tests/test_engine_writes_export_readiness.py` — happy path, hard-gate-fail
  path (`readiness == 0.0`), missing-fields path (readiness stays `NULL` when
  regression signal is unavailable).
- `tests/test_publish_guard_uses_readiness.py` — pass, blocked-by-readiness,
  blocked-by-missing.
- `tests/test_publish_log_trigger.py` — Postgres-only, skipped on SQLite.
  Direct `INSERT INTO publish_log` below threshold raises.

**Acceptance**

- Every `EvalOutput` row produced after this lands has
  `export_readiness`/`export_breakdown_json` set (or explicitly `NULL` for the
  missing-fields case, documented).
- `PublishGuard` rejects with reason `low_export_readiness:<value>` when below
  threshold, and `missing_export_readiness` when `NULL`.
- A direct SQL `INSERT INTO publish_log` with a bad output is rejected by the
  DB trigger on Postgres.

---

### X2. Wire drift detection into the eval round

`dreamfi/trust/gold.py::detect_drift_events` is implemented but never called;
`GoldDriftEvent` rows are never written.

**Files**

- `dreamfi/autoresearch/loop.py::run_round` — at end of round, build
  `previous_results` from the prior round's `EvalOutput` rows joined by
  `test_input_label`, build `new_results` from this round's outputs, call
  `detect_drift_events`, insert returned `GoldDriftEvent` rows.
- `dreamfi/promotion/gate.py` — already accepts `regression_failures`; just
  pass them in from `run_round` when computing promotion eligibility.

**Tests**

- `tests/test_run_round_emits_drift_events.py` — round N passes g1, round
  N+1 fails g1 → exactly one drift row written, regression list contains g1.

**Acceptance**

- A round that flips a regression example pass→fail writes a
  `gold_drift_events` row and the next promotion attempt is refused.

---

### X3. Fix `missing_regression_examples` to report zero-count skills

The current implementation (`dreamfi/trust/seeding.py`) only reports skills
*that already have* some regression examples. A skill with zero is silently
passing.

**Files**

- `dreamfi/trust/seeding.py` — accept `all_skill_ids` (or read from registry)
  and report any not present in counts.
- `dreamfi/skills/registry.py::seed_registry` — call
  `missing_regression_examples` post-seed; raise if any skill is below the
  minimum.

**Tests**

- `tests/test_seeding_zero_count.py` — registry has skills A, B; only A has
  gold examples → deficit reports both A (deficit) and B (5).

**Acceptance**

- Registering a skill with fewer than 5 regression examples raises at boot.
  (The "no shortcuts" rule from `design.md` §4.3 is now enforced.)

---

### X4. Add mypy-strict to CI

`design.md` §10 promises strict mypy; CI (`.github/workflows/ci.yml`) runs
ruff + pytest only.

**Files**

- `.github/workflows/ci.yml` — add `mypy --strict dreamfi/` step.
- `pyproject.toml` — `[tool.mypy]` config: `strict = true`,
  `python_version = "3.11"`, `plugins = ["pydantic.mypy"]`.

**Acceptance:** CI fails on a deliberately added `Any` return.

---

### X5. Retire the marketing skills that don't fit the PM mission

Today's skill list (`dreamfi/skills/registry.py`) is
`meeting_summary, cold_email, landing_page_copy, newsletter_headline,
product_description, resume_bullet, short_form_script, agent_system_prompt,
support_agent`. Six are marketing/copy skills that have nothing to do with
shared PM context.

**Decision required:**

- **Option A — Archive them.** Move the six marketing skills into
  `evals/_archive/` with a note preserving them for eval-history reasons but
  no longer in the active registry. Keep `meeting_summary`,
  `agent_system_prompt`, `support_agent` (the three that arguably touch PM
  workflow).
- **Option B — Demote to a "starter" registry.** Keep them runnable for demo
  purposes but excluded from the default console and any PM-context surfaces.

**Constraint:** ADR-003 locks `evals/` templates and runners. Any move
requires either (a) treating the archive move as a *registry-level* change
(files stay in place, registry tuple shrinks) or (b) an ADR amendment. Option
A implemented as a registry-only change is the lightest path.

**Recommendation:** Option A, registry-only.

---

## Phase C — The Shared Context Engine *(the new spine)*

### C1. The Context Object — first-class, structured, reusable

A **ContextBundle** is what every PM question and every generation consumes.
It is not a string of retrieved chunks; it is a typed, persisted object that
encodes *what we know about a topic right now*.

**Schema**

```python
class ContextBundle(BaseModel):
    bundle_id: UUID
    workspace_id: str
    topic: str                           # natural-language topic
    topic_key: str                       # normalized slug
    created_at: datetime
    refreshed_at: datetime
    ttl_seconds: int                     # auto-stale after this
    sources: list[ContextSource]
    entities: list[ContextEntity]
    claims: list[ContextClaim]
    open_questions: list[OpenQuestion]
    freshness_score: float
    coverage_score: float
    confidence: float

class ContextSource(BaseModel):
    source_type: Literal["jira", "confluence", "metabase", "posthog", "ga",
                         "slack", "doc", "onyx"]
    source_id: str
    fetched_at: datetime
    payload_hash: str
    raw_ref: str

class ContextEntity(BaseModel):
    entity_type: Literal["epic", "issue", "doc", "metric", "person", "squad",
                         "release", "experiment"]
    entity_id: str
    canonical_name: str
    relationships: list[EntityRelation]

class ContextClaim(BaseModel):
    claim_id: UUID
    statement: str
    sot_id: str | None
    citation_ids: list[str]
    confidence: float
    last_verified_at: datetime

class OpenQuestion(BaseModel):
    question: str
    why_open: Literal["no_source", "stale_source", "conflicting_sources",
                      "ambiguous"]
    suggested_owner: str | None
```

**Tables** (new migration `20260421_0004_context_engine.py`):
`context_bundles`, `context_sources`, `context_entities`, `context_claims`,
`open_questions`. Workspace-scoped; `context_bundles` indexed on `topic_key`
and `refreshed_at`.

**Tests**

- `tests/context/test_bundle_schema.py` — Pydantic round-trip, JSON
  serializable.
- `tests/context/test_freshness_decay.py` — past TTL → `is_stale == True`.
- `tests/context/test_coverage_score.py` —
  `claims_covering_question / total_subquestions`.

**Acceptance:** a ContextBundle can be persisted, retrieved, scored, and
rendered to JSON for a UI.

---

### C2. Connector layer — Jira, Confluence, Metabase, PostHog, Slack

Today only Onyx is reachable. `dreamfi/api/routes/console.py::_integrations`
advertises ten integrations, but no client exists for any of them. To answer
"what's going on with X" we need first-party reads from Jira and Confluence on
day 1, metric sources soon after.

**Design rule:** every connector lives under `dreamfi/connectors/<name>/`
with the same shape:

```
dreamfi/connectors/jira/
  client.py        # typed client, single class, no module-level state
  models.py        # Pydantic types for what we read
  fetcher.py       # high-level "give me everything about epic X"
  cache.py         # response cache keyed on (workspace_id, endpoint, params)
  errors.py
```

Each client is the **only** allowed import path for that service (mirrors the
`OnyxClient` rule in `AGENTS.md`).

**C2a. Jira** *(highest priority — half the questions a PM asks are about
Jira)*

- `client.py`: `list_issues(jql)`, `get_issue(key)`, `get_epic_children(key)`,
  `get_changelog(key)`, `list_sprints(board_id)`, `current_sprint(board_id)`.
- `fetcher.py::fetch_topic_jira(topic, *, since)`: JQL search → issues → for
  each, fetch changelog and child links.
- Auth: API token via `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
  (workspace-scoped later).
- Tests: respx-mocked happy / error / pagination paths.

**C2b. Confluence** — `get_page`, `search(cql)`, `list_children`,
`get_page_history`.

**C2c. PostHog** — `query_funnel`, `query_trend`, `events_for_user`,
`feature_flag_state`.

**C2d. Metabase** — `query_card`, `dataset(database_id, native_query)`.

**C2e. Slack** (read-only first) — `search_messages`, `thread`,
`list_channels`.

**Common acceptance**

- Each connector has `ping()` returning reachable/unreachable.
- 100% respx-mocked contract tests + 1 live test gated by env
  (`pytest -m live_<connector>`).
- All retries via tenacity, same shape as `OnyxClient`.

---

### C3. The Context Builder

`dreamfi/context/builder.py`:

```python
class ContextBuilder:
    def __init__(self, connectors: ConnectorRegistry, onyx: OnyxClient,
                 llm: ModelRouter): ...

    def build(self, *, workspace_id: str, topic: str,
              topic_hint: TopicHint | None = None) -> ContextBundle:
        # 1. Topic resolution → entities + slug
        # 2. Parallel fan-out to relevant connectors
        # 3. Onyx semantic search across the workspace
        # 4. Entity extraction + dedup
        # 5. LLM-assisted claim distillation (structured output)
        # 6. Open-question detection (LLM, structured)
        # 7. Score (freshness, coverage, confidence)
        # 8. Persist
```

`TopicHint` is optional metadata: `{ epic_key: "ACT-321", squad: "activation",
time_window_days: 14 }`. The builder uses it to bias the fan-out.

**Tests**

- `tests/context/test_builder_uses_topic_hint.py` — `epic_key=ACT-321` causes
  Jira `get_epic_children` to be called and Metabase to *not* be called.
- `tests/context/test_builder_dedups_entities.py` — same Jira issue surfaced
  via Confluence link and via Jira search appears once.
- `tests/context/test_builder_marks_stale_sources.py` — sources older than
  `staleness_threshold` produce open-questions of type `stale_source`.
- `tests/context/test_builder_llm_returns_structured_claims.py` — mocked LLM
  returns garbage → raises `ContextStructuringError`; never persists a
  half-built bundle.

**Acceptance:** calling `builder.build(topic="onboarding redesign")` against a
seeded fixture produces a bundle with ≥3 sources, ≥1 entity per source type
present, ≥1 claim per source, non-NULL `coverage_score`.

---

### C4. The Ask endpoint — the PM-facing API

`POST /v1/context/ask`

```json
{
  "workspace_id": "ws_abc",
  "question": "what's at risk in the activation squad this sprint?",
  "topic_hint": { "squad": "activation", "time_window_days": 14 },
  "use_cache": true
}
```

Response includes `answer`, `claims` (with `citation_ids`), `open_questions`,
`bundle_id`, `freshness_score`, `coverage_score`, `confidence`, and a `trace`
with connectors called, latency, model, cache hit.

- `dreamfi/context/ask.py::answer_question` — structured-output LLM call that
  assembles the answer with claim refs.
- TTL behavior: if `use_cache=True` and a fresh bundle for
  `(workspace_id, topic_key)` exists, reuse; else build new.
- Every claim in the answer must reference a `claim_id` that exists in the
  bundle. Anything else fails the response with `ungrounded_answer`.

**Tests**

- `tests/context/test_ask_round_trip.py`
- `tests/context/test_ask_refuses_ungrounded.py` (mocked LLM cites a fake
  `claim_id` → 422)
- `tests/context/test_ask_uses_cache.py`

**Acceptance:** a PM can call `POST /v1/context/ask` and get a cited, scored
answer in <10s for cached topics, <30s cold.

---

### C5. The Topic Graph

Bundles are point-in-time. The Topic Graph is the persistent view: every Jira
issue, Confluence page, metric, experiment, person we've seen, with edges.

**Tables**

- `topics` — `(topic_id, workspace_id, type, canonical_name,
  attributes_json)`
- `topic_aliases` — `(topic_id, alias)` ("activation" and "act squad" resolve
  to the same node)
- `topic_relations` — `(from_id, to_id, relation_type, confidence,
  source_bundle_id)`

**Implementation**

- `dreamfi/context/topics.py::resolve_topic(question, hint) -> TopicResolution`
- `dreamfi/context/topics.py::link_entities(bundle) -> None` runs after every
  bundle build.

**Tests**

- `test_topic_resolution_alias.py`
- `test_topic_graph_dedups.py`

**Acceptance:** `resolve_topic("the onboarding redesign")` returns the same
`topic_id` whether the user said "onboarding," "onb v3," or "the new
onboarding flow."

---

### C6. The Watcher

Scheduled job that (1) identifies bundles past TTL or with stale sources,
(2) re-runs the builder, (3) diffs old vs new and emits `context_changes`
events, (4) pushes a digest to the workspace's `#dreamfi-changes` Slack
channel.

- `dreamfi/context/watcher.py`
- `scripts/run_watcher.py` invoked by cron.

**Tests**

- `test_watcher_diffs_bundles.py`
- `test_watcher_skips_fresh.py`

**Acceptance:** a PM who didn't ask anything still gets a digest when
something material changed in topics they care about.

---

### C7. The Memory Layer

Every Ask call writes to `context_questions`. New questions similarity-search
first; if a teammate asked the same thing recently, surface the answer.

- Tables: `context_questions` with embeddings (pgvector or JSON).
- Workspace-scoped; per-user `private` flag.

**Tests**

- `test_memory_finds_similar.py`
- `test_memory_respects_workspace.py`

**Acceptance:** repeat questions cost zero LLM calls when a recent answer
exists.

---

### C8. The Frontend — Ask + Topic + Changes pages

Current `/console/knowledge/ask` route is stubbed. Add three real pages:

- `/console/ask` — single text box, recent-questions sidebar, answer view
  with claim chips that expand to source.
- `/console/topics/<topic_key>` — canonical view for any topic.
- `/console/changes` — workspace activity feed.

Files under `generators/web/src/pages/` and
`generators/web/src/components/context/`.

**Acceptance:** a PM can land on `/console/ask`, type a question, see a
cited answer in <10s, and click a claim chip to see the source.

---

## Phase T — Trust *(subordinate to Context)*

### T0. Gold optimization loop

Unchanged. When the active skill set shifts to `ask_question`,
`topic_summary`, `change_digest`, those become the skills that need 5+
regression examples.

### T2′. Metric trust scoped to Ask

Not a separate report system. A guardrail on the Ask endpoint: any answer
that quotes a metric must resolve against the catalog and flag discrepancies.

- `metric_catalog` + `metric_snapshots` tables in `dreamfi/context/metrics.py`
- `metric_discrepancy_check(metric_id, as_of_date)` called inline during
  claim assembly.

### T3′. Interpretation trust scoped to claims

Implied by C3/C4: a claim without `sot_id` *or* `citation_ids` fails the
answer. SoT catalog + anomaly detection fold in.

### T4. Artifact trust + DB trigger

Still needed when generation skills publish, operating on `context_answers`
*and* `eval_outputs`. Same trigger pattern as X1.

### T5. UI-support trust

Subsumed by C8.

### T1. Planning trust

Largely subsumed by C2a + C5. "Hygiene" probes become standing checks on
every bundle build.

---

## Phase S — Skills, recast as context consumers

### S1. `weekly_pm_brief`
Input: ContextBundle for `(workspace_id, squad_or_team)`, 7-day window.
Output: structured brief — shipped / at-risk / metrics / open questions.

### S2. `topic_summary`
Input: any `topic_id`. Output: on-demand "everything we know about X."

### S3. `discovery_brief`
Input: problem statement + topic. Output: problem framing, evidence,
hypotheses, open questions, suggested experiments.

### S4. `risk_brief`
Input: topic + risk lens. Output: what could go wrong, signals, responses.

### S5. `change_digest`
Emitted by the watcher (C6), not on demand.

For each: locked eval template, runner, output contract (Pydantic), 5
regression gold examples — same discipline as today.

---

## Phase P — Productization plumbing

- **P8. Multi-tenancy** — workspaces table, RLS, `SET LOCAL
  dreamfi.workspace_id` middleware, API keys, workspace-tagged Onyx ingest.
  Blocker for any real customer.
- **P9. Model router (LiteLLM)** — swap models per question complexity.
- **P10. Structured outputs everywhere** — enforce structured-output mode at
  the model API call.
- **P11. MCP tools for Ask** — Jira/Confluence/Metabase as MCP tools the
  model can call mid-answer, bounded loop, full trace.
- **P12–P15. Publishing** — publish topic pages to Confluence, briefs to
  Notion, digests to Slack; OAuth broker, idempotent queue, DB trigger.
- **P16. Onboarding** — "Connect Jira, point at a board, see your first
  ContextBundle in 5 minutes."

---

## Suggested execution order

```
Week 1   X1, X2, X3, X4         ← finish what we started
Week 2   X5, C1                 ← decision + the Context Object
Week 3   C2a (Jira)
Week 4   C2b (Confluence)
Week 5   C3 (Builder)
Week 6   C4 (Ask endpoint)
Week 7   C5 (Topic graph)
Week 8   C8 (Ask + Topic UI)    ← show to a PM
Week 9   C2c, C2d (PostHog, Metabase)
Week 10  C6 (Watcher)
Week 11  C7 (Memory)
Week 12  T2′ + T3′ inside Ask
Week 13  S1 (weekly_pm_brief)
Week 14  P8 (multi-tenancy)
```

---

## Explicitly *not* building (yet)

- A chat UI. Ask is single-shot; threading is later.
- A document editor.
- Custom dashboards.
- A vector DB beyond pgvector.
- Fine-tuning.
- A mobile app.

---

## Risks worth naming

1. **Connector breadth vs depth.** Two great connectors beat five half-built
   ones. Jira and Confluence are non-negotiable.
2. **LLM-assisted claim distillation is the trickiest piece in C3.** A bad
   distillation poisons every downstream answer. Structured-output discipline
   + LLM-judge eval round on every prompt change.
3. **Topic resolution will be wrong sometimes.** Audit view (C8) shows the
   PM what we resolved to before answering.
4. **Watcher cost.** Re-building bundles across many topics adds up. TTL
   tuning, only-build-on-`payload_hash`-change, aggressive caching.
5. **Memory layer privacy.** Workspace-scoped, per-user `private` flag, opt
   out.

---

## First PRs to hand off

1. **X1 + X2 + X3 + X4** as one PR titled
   *"trust foundations: enforcement."* Small, mechanical, finishes what's
   started.
2. **C1** (ContextBundle schema + migration + tests) — pure data model, no
   I/O.
3. **C2a** (Jira connector) — real I/O, contract-tested.
4. **C3** (ContextBuilder, Jira-only first) — Ask endpoint becomes possible.

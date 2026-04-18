# DreamFi Vertical Slice — One Working End-to-End Path

**Goal:** Ship one provable end-to-end path that demonstrates DreamFi is real.

**Path:** locked eval contract → synced source data → knowledge query → Tier 1 generation → hard-gate decision → stored result

**Timeline:** 5 commits, 1 complete vertical slice

---

## Scope (ONLY)

### Data Sources
- ✅ Jira connector (operational source)
- ✅ Confluence connector (documentation source)

### Knowledge Hub
- ✅ Schema + migrations
- ✅ Seeded canonical data
- ✅ Query API with retrieval + confidence

### Tier 1 Skill
- ✅ **meeting_summary** (chosen for: structure, scoring, storage value)
  - Takes synced Confluence pages, Jira issues → meeting-style summary
  - Sections: Decisions, Action Items, Open Questions
  - Each action item must have owner + deadline
  - Decisions explicitly labeled
  - Questions are questions
  - Max 300 words

### Evaluation & Publishing
- ✅ Locked eval with hard gates
- ✅ Round scoring (10 outputs per 3 test inputs)
- ✅ Results artifacts (results.log, analysis.md, learnings.md, changelog.md)
- ✅ Publish guard blocking bad outputs
- ✅ Gold example promotion
- ✅ Failure pattern storage

### Observability
- ✅ Eval history endpoint
- ✅ Connector health checks
- ✅ Query confidence visibility

### NOT in scope yet
- ❌ Agent system prompt (different logic flow)
- ❌ Support agent (requires message threading)
- ❌ All 11 connectors (only Jira + Confluence)
- ❌ Dragonboat, Metabase, PostHog, GA, Klaviyo, Sardine, Socure, NetXD, Lucidchart
- ❌ Phase 5 UI support
- ❌ Rich operator console
- ❌ Metrics trust stack
- ❌ Planning sync (Phase 3+)

---

## Step 1: Lock the Truth

**Objective:** Make contracts, schema, docs, and code point to the same source.

### Deliverables

1. **Source of truth document**
   - File: `docs/contracts/tier1_skill_contracts.md`
   - Canonical definitions for: meeting_summary, agent_system_prompt, support_agent

2. **Tier 1 alignment tests** — all green before moving forward
   - `tests/unit/contracts/test_tier1_alignment.py` (NEW — replacing generic test)

### Tests to Write First

```python
# tests/unit/contracts/test_tier1_alignment.py
- test_meeting_summary_eval_file_exists()
- test_meeting_summary_eval_file_has_5_criteria()
- test_schema_seed_has_meeting_summary_skill()
- test_schema_criteria_match_eval_criteria()
- test_locked_eval_checksum_matches_contract_hash()
- test_no_schema_without_eval_file()
- test_no_eval_file_without_schema_seed()
```

### Strict Acceptance Criteria

- ✅ Every Tier 1 skill has exactly one locked eval file (`evals/meeting-summary.md`, etc.)
- ✅ Schema seed data lists exact same criteria names and count as locked eval
- ✅ File paths consistent everywhere (evals/ = .md files, not .yaml)
- ✅ CI fails if any contract drifts
- ✅ Docs point to schema skill definitions

### Done When

- All alignment tests GREEN
- No human disagreement between eval files, schema, and code

---

## Step 2: Schema & Migrations Real

**Objective:** Move from theoretical schema to working DB with testable migrations.

### Deliverables

1. **Migrations**
   - `services/knowledge-hub/db/migrations/001_initial_schema.sql`
   - `services/knowledge-hub/db/migrations/002_add_canonical_fields.sql`

2. **Seed scripts**
   - `services/knowledge-hub/db/seeds/seed_tier1_skills.ts`
   - `services/knowledge-hub/db/seeds/seed_tier1_criteria.ts`
   - `services/knowledge-hub/db/seeds/seed_test_inputs.ts`

3. **Reset script**
   - `scripts/db/reset_test_db.sh` (already exists, test it)

### Tests to Write First

```python
# tests/unit/schema/test_migrations_real.py
- test_migration_001_creates_all_canonical_tables()
- test_skills_table_has_required_columns()
- test_criteria_table_joins_skills()
- test_normalized_sources_table_stores_canonical_records()

# tests/unit/schema/test_seed_data_alignment.py
- test_seed_meeting_summary_skill()
- test_seed_meeting_summary_5_criteria()
- test_seed_test_inputs_present()
- test_all_tier1_skills_seeded()
- test_no_unresolved_fk_references()

# tests/integration/schema/test_deterministic_db.py
- test_seed_twice_produces_identical_state()
- test_reset_script_works()
- test_clean_boot_matches_seeded_state()
```

### Strict Acceptance Criteria

- ✅ Clean DB boot works in CI
- ✅ Seed scripts produce identical rows every run
- ✅ All 3 Tier 1 skills seeded with correct criteria
- ✅ Test inputs available for each skill
- ✅ No manual SQL edits required

### Done When

- Anyone can `make db-reset && make db-seed` and have a working DB
- All migration and seed tests GREEN

---

## Step 3: Jira & Confluence Connectors Real

**Objective:** Get operational and document data synced into canonical schema.

### Deliverables

#### Jira Connector
- `services/knowledge-hub/src/connectors/jira_connector.ts`
  - Auth (API token)
  - Full sync (query all issues since start_date)
  - Incremental sync (watermark-based)
  - Normalization to canonical schema
  - Freshness scoring (7-day half-life)
  - Checkpointing
  - Retry/backoff

#### Confluence Connector
- `services/knowledge-hub/src/connectors/confluence_connector.ts`
  - Auth (API token)
  - Full sync (query all pages since start_date)
  - Incremental sync (watermark-based)
  - Normalization to canonical schema
  - Freshness scoring (14-day half-life)
  - Checkpointing
  - Retry/backoff

#### Canonical Schema
```sql
CREATE TABLE normalized_sources (
  id UUID PRIMARY KEY,
  source_system TEXT NOT NULL,  -- 'jira', 'confluence'
  source_object_id TEXT NOT NULL,
  source_object_type TEXT,  -- 'issue', 'page'
  title TEXT,
  body TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  last_synced_at TIMESTAMP,
  freshness_score NUMERIC,
  eligible_skill_families_json JSON,  -- ["meeting_summary", ...]
  raw_metadata_json JSON,
  connector_checksum TEXT
);
```

### Tests to Write First

#### Jira Tests
```python
# tests/unit/connectors/test_jira_connector.py
- test_auth_config_parsed_correctly()
- test_auth_validates_url_and_token()
- test_fixture_jira_issue_normalizes_to_canonical()
- test_fixture_has_all_required_fields()
- test_multiple_issues_normalize_consistently()
- test_malformed_issue_caught()

# tests/integration/connectors/test_jira_sync.py
- test_full_sync_writes_to_normalized_sources()
- test_full_sync_sets_freshness()
- test_incremental_sync_uses_watermark()
- test_unchanged_issue_skipped_by_hash()
- test_changed_issue_syncs()
- test_retry_backoff_on_rate_limit()
- test_no_duplicate_writes_on_retry()
- test_dead_letter_on_malformed_payload()
```

#### Confluence Tests
```python
# tests/unit/connectors/test_confluence_connector.py
- test_auth_config_parsed_correctly()
- test_auth_validates_url_and_token()
- test_fixture_confluence_page_normalizes_to_canonical()
- test_fixture_has_all_required_fields()
- test_multiple_pages_normalize_consistently()
- test_malformed_page_caught()

# tests/integration/connectors/test_confluence_sync.py
- test_full_sync_writes_to_normalized_sources()
- test_full_sync_sets_freshness()
- test_incremental_sync_uses_watermark()
- test_unchanged_page_skipped_by_hash()
- test_changed_page_syncs()
- test_retry_backoff_on_rate_limit()
- test_no_duplicate_writes_on_retry()
- test_dead_letter_on_malformed_payload()
```

### Strict Acceptance Criteria

**For each connector:**
- ✅ Auth config parsed correctly and validates
- ✅ Real fixture payload normalizes into canonical schema
- ✅ source_system, source_object_id, last_synced_at, freshness_score populated
- ✅ eligible_skill_families_json populated (e.g., ["meeting_summary"])
- ✅ Changed object syncs via watermark
- ✅ Unchanged object skipped via hash
- ✅ Malformed payload dead-lettered
- ✅ Retry/backoff does not duplicate writes
- ✅ Unit tests mock API, integration tests use fixtures

### Done When

- You can inspect normalized_sources table and see canonical Jira + Confluence records
- Both integration tests GREEN
- No manual API calls needed for tests

---

## Step 4: Knowledge Query Path

**Objective:** Prove query → answer with citations + confidence works.

### Deliverables

1. **Retrieval engine**
   - `services/knowledge-hub/src/retrieval/retrieve_context.ts`
   - Hybrid keyword + embedding search (or keyword-only MVP)
   - Returns canonical sources with titles, snippets, freshness
   - Deterministic for same test dataset

2. **Confidence scoring**
   - `services/knowledge-hub/src/confidence/score_confidence.ts`
   - Inputs: sources, freshness, citation count
   - Output: confidence 0-1
   - Factors: freshness penalty, citation count penalty, contradiction penalty

3. **Query API**
   - `POST /api/query`
   - Input: { query: string, skill?: string }
   - Output: { answer: string, citations: [...], confidence: float, freshness: float, next_action?: string }

4. **Phase 1 E2E Test**
   - `tests/e2e/test_phase1_query_to_answer.py` (make green)

### Tests to Write First

```python
# tests/unit/knowledge/test_retrieve_context_meeting.py
- test_retrieve_returns_canonical_sources()
- test_results_include_title_snippet_freshness()
- test_deterministic_for_same_input()
- test_irrelevant_query_returns_empty()
- test_retrieval_respects_skill_family()

# tests/unit/knowledge/test_score_confidence.py
- test_confidence_0_to_1_range()
- test_confidence_deterministic()
- test_stale_source_lowers_confidence()
- test_low_citation_count_lowers_confidence()
- test_high_freshness_increases_confidence()

# tests/api/test_query_endpoint_meeting.py
- test_query_endpoint_returns_answer()
- test_query_endpoint_returns_citations()
- test_query_endpoint_returns_confidence()
- test_query_endpoint_returns_freshness()
- test_impossible_query_declined_with_reason()

# tests/e2e/test_phase1_query_to_answer.py (make green)
- test_sync_jira_confluence()
- test_query_gets_answer_from_synced_data()
- test_answer_includes_citations()
- test_answer_includes_confidence()
```

### Strict Acceptance Criteria

- ✅ Query returns answer + citations + freshness + confidence
- ✅ Same input → deterministic confidence
- ✅ Stale sources lower confidence
- ✅ No supported answer returns with zero citations
- ✅ Impossible request gets explicit rejection + suggestion
- ✅ E2E test GREEN: sync → query → answer

### Done When

- You can demo: "Sync Jira/Confluence, ask a question, get a cited answer with confidence score"

---

## Step 5: Meeting Summary Complete Loop

**Objective:** End-to-end: generation → eval → scoring → storage → publish → gold examples.

### Deliverables

1. **meeting_summary prompt**
   - `services/generators/src/prompts/meeting_summary.md`
   - Takes synced Confluence pages + Jira issues as context
   - Generates: Decisions, Action Items (owner + deadline), Open Questions
   - Max 300 words

2. **meeting_summary generation**
   - `services/generators/src/generate/generate_meeting_summary.ts`
   - Calls LLM with prompt + context
   - Stores generation_id, version, model, temperature

3. **meeting_summary eval runner**
   - `evals/meeting-summary.md` (locked, already exists)
   - 5 criteria (hard and soft gates)
   - Test runner that scores outputs

4. **Round scoring**
   - `services/generators/src/evals/run_skill_round.ts`
   - Generates 10 outputs per test input
   - Runs eval on each
   - Stores results in DB

5. **Results analyzer**
   - `services/generators/src/results/analyze_run.ts`
   - Parses results
   - Generates results.log, analysis.md, learnings.md, changelog.md
   - Identifies patterns

6. **Prompt promotion**
   - `services/generators/src/prompts/promote_prompt.ts`
   - Compares old vs new score
   - Promotes only if new ≥ old + 2%

7. **Gold example promotion**
   - `services/generators/src/gold/promote_gold_examples.ts`
   - All-pass rounds → gold examples
   - Stored and retrieval-accessible

8. **Publish guard enforcement**
   - `services/shared/publish/guard.ts` (already scaffolded)
   - Blocks on failed hard gates
   - Blocks on low confidence
   - Blocks on missing metadata

### Tests to Write First

```python
# tests/unit/generators/test_meeting_summary.py
- test_prompt_exists_and_is_locked()
- test_prompt_version_tracked()

# tests/unit/generators/test_generation_meeting_summary.py
- test_generation_takes_context()
- test_generation_returns_structured_output()
- test_generation_stores_version_and_metadata()

# tests/integration/evals/test_round_scoring.py
- test_round_generates_10_outputs_per_input()
- test_round_scores_each_output()
- test_round_stores_results_to_db()
- test_round_creates_results_log()

# tests/integration/evals/test_prompt_promotion.py
- test_promotion_requires_2_percent_improvement()
- test_promotion_blocked_on_regression()
- test_promotion_requires_hard_gates_pass()
- test_promotion_recorded_with_actor()

# tests/integration/results/test_results_analyzer.py
- test_analyzer_parses_results_log()
- test_analyzer_generates_analysis_md()
- test_analyzer_generates_learnings_md()
- test_analyzer_generates_changelog_md()

# tests/unit/knowledge/test_gold_example_promotion.py
- test_all_pass_round_promotes_all_to_gold()
- test_gold_examples_stored_and_retrievable()
- test_gold_example_has_skill_and_scenario_tags()

# tests/unit/publish/test_publish_guards_meeting.py
- test_hard_gate_fail_blocks_publish()
- test_low_confidence_blocks_publish()
- test_missing_metadata_blocks_publish()
- test_passing_all_gates_allows_publish()

# tests/integration/publish/test_publish_meeting_to_confluence.py
- test_passing_output_publishes_to_confluence()
- test_failed_output_blocked()
- test_publish_event_logged()

# tests/e2e/test_phase2_generate_to_publish.py (make green)
- test_generation_succeeds()
- test_eval_round_completes()
- test_scoring_stored_in_db()
- test_promotion_decision_made()
- test_gold_examples_available()
- test_publish_succeeds_on_pass()
- test_publish_blocked_on_fail()
```

### Strict Acceptance Criteria

- ✅ Exactly 10 outputs per test input
- ✅ Exactly 3 test inputs
- ✅ Summary includes Decisions, Action Items (owner + deadline), Questions
- ✅ Every action item has owner + deadline
- ✅ Decisions explicitly labeled
- ✅ Questions are questions
- ✅ Output < 300 words
- ✅ Score stored in DB
- ✅ results.log, analysis.md, learnings.md, changelog.md created
- ✅ Gold examples promoted from all-pass
- ✅ Failures patterns stored
- ✅ Publish guard blocks bad, allows good
- ✅ E2E test GREEN

### Done When

- You can: generate → score → publish → inspect gold examples for next round
- One full loop: baseline → round → promotion decision complete

---

## Step 6: Operator Visibility

**Objective:** Make system inspectable without blind debugging.

### Deliverables

1. **Eval history endpoint**
   - `GET /api/admin/evals/<skill>/history`
   - Returns recent rounds with scores

2. **Connector health**
   - `GET /api/admin/connectors/health`
   - Last sync time, freshness, error count

3. **Query debug endpoint**
   - `GET /api/admin/debug/query/<query_id>`
   - Shows retrieval, confidence factors, sources used

4. **Active prompt version**
   - `GET /api/admin/prompts/<skill>/active`
   - Current active prompt with version

### Tests

```python
# tests/api/test_eval_history_endpoint.py
- test_eval_history_returns_recent_rounds()
- test_eval_history_includes_scores()

# tests/api/test_connector_health_endpoint.py
- test_connector_health_shows_freshness()
- test_connector_health_shows_last_sync()

# tests/api/test_query_debug_endpoint.py
- test_debug_shows_retrieval_results()
- test_debug_shows_confidence_factors()

# tests/api/test_active_prompt_endpoint.py
- test_active_prompt_shows_version()
- test_active_prompt_shows_criteria()
```

### Strict Acceptance Criteria

- ✅ Operator can inspect latest eval round
- ✅ Operator can inspect connector freshness
- ✅ Operator can see why output failed
- ✅ Operator can see active prompt version

### Done When

- You're not debugging blind

---

## The 5 Commits

### Commit 1: Eval Contract Truth
**Purpose:** Lock the truth so contracts, schema, docs, code never drift.

**Include:**
- `tests/unit/contracts/test_tier1_alignment.py` ← FAILING
- `docs/contracts/tier1_skill_contracts.md` (canonical definitions)
- Fixes to `services/knowledge-hub/db/schemas.ts` (seed data)
- Fix eval file paths if needed
- Lock checksums in schema

**Exit criteria:** All tests GREEN

### Commit 2: Jira Connector
**Purpose:** Get real operational data into canonical schema.

**Include:**
- `services/knowledge-hub/src/connectors/jira_connector.ts` (full impl)
- `tests/unit/connectors/test_jira_connector.py` ← FAILING, then PASSING
- `tests/integration/connectors/test_jira_sync.py` ← FAILING, then PASSING
- Migration or schema update for normalized_sources table
- Jira unit + integration tests GREEN

**Exit criteria:**
- You can inspect DB and see Jira issues in canonical format
- Both test files GREEN.

### Commit 3: Confluence Connector
**Purpose:** Get real documentation data into canonical schema.

**Include:**
- `services/knowledge-hub/src/connectors/confluence_connector.ts` (full impl)
- `tests/unit/connectors/test_confluence_connector.py` ← FAILING, then PASSING
- `tests/integration/connectors/test_confluence_sync.py` ← FAILING, then PASSING
- Confluence unit + integration tests GREEN

**Exit criteria:**
- You can inspect DB and see Confluence pages in canonical format
- Both test files GREEN.

### Commit 4: Query API + Confidence
**Purpose:** Prove knowledge hub works with real synced data.

**Include:**
- `services/knowledge-hub/src/retrieval/retrieve_context.ts` (full impl)
- `services/knowledge-hub/src/confidence/score_confidence.ts` (full impl)
- `services/knowledge-hub/src/api/query.ts` (endpoint)
- `tests/unit/knowledge/test_retrieve_context.py` ← all GREEN
- `tests/unit/knowledge/test_score_confidence.py` ← all GREEN
- `tests/api/test_query_endpoint.py` ← all GREEN
- `tests/e2e/test_phase1_query_to_answer.py` ← PASSING
- Phase 1 E2E GREEN

**Exit criteria:**
- Demo: sync Jira/Confluence → ask question → get answered with citations

### Commit 5: Meeting Summary Complete Loop
**Purpose:** One Tier 1 skill fully working: generate → eval → score → publish → learn.

**Include:**
- `services/generators/src/prompts/meeting_summary.md` (locked)
- `services/generators/src/generate/generate_meeting_summary.ts`
- `services/generators/src/evals/run_skill_round.ts`
- `services/generators/src/results/analyze_run.ts`
- `services/generators/src/prompts/promote_prompt.ts`
- `services/generators/src/gold/promote_gold_examples.ts`
- `services/shared/publish/guard.ts` (full impl)
- `tests/unit/generators/test_meeting_summary.py` ← all GREEN
- `tests/unit/generators/test_generation.py` ← all GREEN
- `tests/integration/evals/test_round_scoring.py` ← all GREEN
- `tests/integration/evals/test_prompt_promotion.py` ← all GREEN
- `tests/integration/results/test_results_analyzer.py` ← all GREEN
- `tests/unit/knowledge/test_gold_example_promotion.py` ← all GREEN
- `tests/unit/publish/test_publish_guards.py` ← all GREEN
- `tests/integration/publish/test_publish_meeting_to_confluence.py` ← all GREEN
- `tests/api/test_eval_history_endpoint.py` ← all GREEN
- `tests/api/test_connector_health_endpoint.py` ← all GREEN
- `tests/e2e/test_phase2_generate_to_publish.py` ← GREEN
- Phase 2 E2E GREEN

**Exit criteria:**
- Demo: sync → query → generate → score → publish → inspect gold examples
- DreamFi stops being "great architecture" and becomes "real product"

---

## Success Criteria for Vertical Slice

At the end, you should be able to demo:

1. ✅ `make db-reset && make db-seed` — clean schema + migrations work
2. ✅ Sync Jira + Confluence
3. ✅ Ask a question → get cited answer with confidence
4. ✅ Generate a meeting summary from synced context
5. ✅ Score it against locked evals
6. ✅ Store failures and gold examples
7. ✅ Publish only if all gates pass
8. ✅ Inspect eval history, connector health, active prompt

If you can do that:
- DreamFi proves the model works end-to-end
- The rest becomes repetition (more connectors, more skills, more UX)
- You have a foundation to scale from

---

## What NOT to Do

Do NOT expand into:
- ❌ All 11 connectors (do 2, the rest scale)
- ❌ Tier 2/3 skills (do 1, the rest copy the pattern)
- ❌ Phase 3 planning sync (prove Phase 1-2 first)
- ❌ Metric trust stack (separate vertical slice later)
- ❌ Dragonboat writeback (not needed for vertical slice)
- ❌ UI/UX polish (bare minimum internal views only)
- ❌ Mobile support (desktop first)

## Ready?

This vertical slice is achievable in ~2 weeks if focused.

Next: implement in order (Commit 1 → 2 → 3 → 4 → 5) and do not branch.


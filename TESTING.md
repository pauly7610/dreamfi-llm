# DreamFi Testing Strategy and Build Order

This document defines the strict TDD approach for building DreamFi. It serves as the source of truth for implementation priorities, test requirements, and quality gates.

**Core Principle:** No feature is done until it passes TDD gates. Documentation alone does not count.

## Build Order

Build in this exact sequence to maximize impact and unblock downstream work:

### Phase 1 Core Vertical Slice (Foundation)
1. Schema validation and seed data integrity
2. Jira connector with watermarking
3. Confluence connector with pagination
4. Knowledge Hub query API with confidence scoring
5. Gold example retrieval

### Phase 2 Tier 1 Skills (First AI Layer)
1. agent_system_prompt generator and evaluator
2. support_agent generator and evaluator
3. meeting_summary generator and evaluator

### Phase 3 Trust-Based Reporting (First Downstream)
1. Jira/Dragonboat field mapping validation
2. Report summary generation
3. Escalation detection

### Phase 4 Metrics Trust (Data Trust Layer)
1. Metabase connector (metrics source)
2. PostHog connector (product analytics)
3. Google Analytics connector (traffic)
4. Metric snapshot generation with trust scoring

### Phase 5 UI Support (Last, After Phase 1-2 Live)
1. Minimalist fintech style validation
2. Export readiness checking
3. Artifact-to-skill mapping

**Rationale:** This sequence unblocks each phase through lower phases. Do not parallelize across phases.

## Global TDD Rules

These rules apply to all features and phases.

### Mandatory Rules

1. **No implementation file without test file** - For every TS/Python implementation, create corresponding tests before or alongside implementation
2. **No connector merged without coverage** - Every connector must have unit tests + integration tests
3. **No skill promoted without eval pass** - All hard-gate criteria must pass before prompt version is activated
4. **No publish without gate tests** - Publish flows must have negative-path tests proving gates work
5. **No doc-only "done"** - Features are done when code + tests pass, not when documented

### Mandatory Quality Gates

All code must pass before merge:

- All tests pass in CI
- TypeScript strict mode passes
- ESLint passes (if used)
- Eval regression tests pass for any skill changes
- Code satisfies acceptance criteria

### Acceptance Thresholds

- **Connector write path:** Minimum 90% happy-path coverage on core mapping logic
- **Skill promotion:** Round score > previous best AND all hard-gate criteria pass
- **Publish flow:** Stale/failing inputs must block publish, with tests proving it

### ADR Enforcement Tests

Every ADR must have corresponding test(s) that verify the decision is enforced:

| ADR | Required Test |
|-----|---|
| 003 (Eval Locking) | tests/integration/evals/test_eval_runner_locking.py |
| 004 (Keep/Revert Loop) | tests/integration/evals/test_prompt_promotion.py |
| 005 (Confidence Model) | tests/unit/knowledge/test_score_confidence.py |
| 006 (Hard-Gate Publishing) | tests/unit/publish/test_publish_guards.py |
| 007 (Freshness Policy) | tests/unit/connectors/test_freshness_scoring.py |
| 008 (Skill Promotion) | tests/integration/evals/test_promotion_policy.py |

## Critical Area 1: Schema and Canonical Data Integrity

**Importance:** This is the foundation. Everything depends on correct schema.

**Files Under Test**
- services/knowledge-hub/db/schema.sql
- Migration files (when created)
- Seed data files
- Schema access layer (when created)

### Test Files to Create

```
tests/unit/schema/test_schema_tables_exist.py
tests/unit/schema/test_schema_constraints.py
tests/unit/schema/test_schema_indexes.py
tests/unit/schema/test_seed_data_integrity.py
tests/unit/schema/test_eval_contract_alignment.py
```

### Strict Acceptance Criteria

All 11 canonical tables must exist:
- core_entities
- relationships
- citations
- skill_registry
- prompt_versions
- evaluation_criteria_catalog
- test_input_registry
- evaluation_rounds
- evaluation_outputs
- gold_example_registry
- skill_failure_patterns

**Constraints:**
- All primary keys exist and are UUID type
- Required unique constraints exist (e.g., skill_name is unique)
- Foreign keys enforce referential integrity on DELETE CASCADE
- Seed skills (9 total) are inserted correctly with no duplicates

**Indexes:**
- Retrieval-critical tables have indexes (core_entities on type, status, freshness; evaluation_outputs on round_id, pass_fail)
- Uniqueness constraints have corresponding indexes
- Full-text search indexes exist on description fields

**Seed Data:**
- All 9 skills inserted successfully
- Every seeded skill has at least one evaluation_criteria_catalog row
- Evaluation criteria match locked eval file definitions
- No foreign key violations on insert

**HIGH-PRIORITY FAILING TEST:**

Create test_eval_contract_alignment.py that fails if:
- Schema references .md file path but repo truth is .yaml (or vice versa)
- Seeded evaluation_criteria_catalog entries do not match locked eval file criteria for Tier 1 skills
- Criterion count mismatch for any Tier 1 skill

This test is critical because the repo currently has inconsistencies here.

### Definition of Done for Schema

- Schema applies to clean database with zero manual edits
- Seed data loads successfully on fresh DB
- No foreign key violations
- All 11 tables verified in CI
- Every seeded skill aligned with locked eval file
- Schema test suite passes in CI

## Critical Area 2: Connector Framework

**Importance:** Without connectors, the platform is useless. Start here after schema.

**Implementation Priority Order**
1. Jira (highest priority, used by Phase 3)
2. Confluence (used by Phase 1)
3. Dragonboat (used by Phase 3)
4. Metabase (used by Phase 4)
5. PostHog (used by Phase 4)
6. Google Analytics (used by Phase 4)
7. Klaviyo, NetXD, Sardine, Socure, Lucidchart (lower priority)

**Files Under Test**
- services/knowledge-hub/src/connectors/base_connector.ts
- services/knowledge-hub/src/connectors/jira_connector.ts
- services/knowledge-hub/src/connectors/confluence_connector.ts
- (and each subsequent connector)

### Test Files

```
tests/unit/connectors/test_base_connector.py
tests/unit/connectors/test_jira_connector.py
tests/unit/connectors/test_confluence_connector.py
tests/unit/connectors/test_dragonboat_connector.py
tests/integration/connectors/test_jira_sync.py
tests/integration/connectors/test_confluence_sync.py
tests/integration/connectors/test_watermarking.py
tests/integration/connectors/test_dead_letter_handling.py
tests/unit/connectors/test_freshness_scoring.py
```

### Strict Unit Test Acceptance Criteria

Every connector must handle:

1. **Auth Configuration:**
   - Parses credentials from environment variables correctly
   - Fails gracefully on missing credentials
   - Does not log credentials

2. **Normalization:**
   - Transforms source object into NormalizedEntity with all required fields:
     - source_system (e.g., "jira")
     - source_object_id (external ID)
     - last_synced_at (ISO-8601)
     - freshness_score (0-1)
     - eligible_skill_families_json (which skills can use this)
   - Maps source-specific types to canonical entity_type

3. **Pagination:**
   - Handles paginated responses correctly
   - Processes all pages without skipping
   - Stops pagination when no more results

4. **Rate Limiting and Retry:**
   - Retries on 429 (rate limit) with exponential backoff
   - Retries on 5xx errors up to 5 times
   - Fails fast on 4xx errors with clear message
   - Does not exceed API rate limits in test

5. **Error Handling:**
   - Emits typed errors on malformed payloads
   - Includes source object ID in error message
   - Dead-letter path receives unparseable payloads
   - Does not crash on unexpected field absence

### Strict Integration Test Acceptance Criteria

1. **Watermarking:**
   - Changed object syncs when newer than last_synced_at
   - Unchanged object skipped via payload hash comparison
   - Watermark persists across restarts

2. **Data Quality:**
   - Malformed payload goes to dead-letter path (not canonical DB)
   - Stale source object freshness_score reduces correctly
   - Retries do not create duplicate records in canonical DB

3. **End-to-End:**
   - At least one real fixture from the source system works start-to-finish
   - Produces canonical entity in DB with all required fields
   - Freshness score calculated correctly
   - Can handle fixture with missing optional fields

### Definition of Done for a Connector

- Unit tests pass (auth, normalization, pagination, retry, errors)
- Integration sync test passes
- Canonical object written to DB with all required fields
- Freshness score computed and stored
- One real fixture from the source system syncs successfully
- Dead-letter handling tested for malformed payloads
- Code review passed

## Critical Area 3: Knowledge Hub Retrieval and Query API

**Importance:** This is the first thing downstream systems use. Must be reliable.

**Files Under Test**
- services/knowledge-hub/src/retrieval/retrieve_context.ts
- services/knowledge-hub/src/confidence/score_confidence.ts
- services/knowledge-hub/src/api/query.ts

### Test Files

```
tests/unit/knowledge/test_retrieve_context.py
tests/unit/knowledge/test_gold_example_retrieval.py
tests/unit/knowledge/test_failure_pattern_retrieval.py
tests/unit/knowledge/test_score_confidence.py
tests/integration/api/test_query_endpoint.py
tests/e2e/test_phase1_query_to_answer.py
```

### Strict Retrieval Acceptance Criteria

retrieve_context must:

1. **Relevance:**
   - Return canonical entities matching query
   - Return full citations for all source-backed claims
   - Include gold examples when skill/scenario match exists in DB

2. **Freshness:**
   - Rank fresher sources above stale ones when relevance is comparable
   - Include freshness_score in returned metadata

3. **Failure Insights:**
   - Return failure patterns when available for the matched skill
   - Include failure_count and last_seen_at

4. **Limits:**
   - No unlimited result loops (max 100 results)
   - Nullable results return explicit empty array, never null

### Strict Confidence Acceptance Criteria

score_confidence must:

1. **Determinism:**
   - Same input bundle always produces same confidence output (no randomness)
   - Confidence is numeric between 0 and 1

2. **Scoring Logic:**
   - Reduce confidence when freshness < 0.8
   - Reduce confidence when citation_count < 1
   - Reduce confidence when hard-gate criteria fail
   - Never return "high confidence" (>0.8) when source freshness is below threshold

3. **Traceability:**
   - Include breakdown of which factors affected score
   - Log scoring decisions for debugging

### Strict Query API Acceptance Criteria

For entity-backed queries (queries matching canonical entities):

- Response includes answer
- Response includes citations (source_system, source_object_id, source_snippet)
- Response includes freshness metadata
- Response includes confidence score with breakdown
- Response includes next_action if required by skill

For ambiguous or impossible requests:

- No hallucinated policy or process
- Clear limitation statement
- Specific redirect or next action

### Definition of Done for Query API

- All unit tests pass
- Integration test proves end-to-end query works
- E2E test proves query + downstream skill receives correct context
- No query returns without citations (when citations apply)

## Critical Area 4: Tier 1 Skill Engine

**Importance:** Skills are where value is generated. Start with top 3 only.

**In Scope (First)**
- agent_system_prompt
- support_agent
- meeting_summary

**Out of Scope (For Now)**
- cold_email, landing_page_copy, newsletter_headline, product_description, resume_bullet, short_form_script

**Files Under Test**
- services/generators/src/generate/generate_output.ts
- services/generators/src/evals/run_skill_round.ts
- evals/runners/run_{skill}_eval.py (for each skill)

### Test Files

```
tests/unit/generators/test_agent_system_prompt.py
tests/unit/generators/test_support_agent.py
tests/unit/generators/test_meeting_summary.py
tests/integration/evals/test_eval_runner_locking.py
tests/integration/evals/test_round_scoring.py
tests/integration/evals/test_prompt_promotion.py
tests/e2e/test_phase2_generate_to_publish.py
```

### Strict Acceptance Criteria: agent_system_prompt

From locked eval file (evals/agent-system-prompt.md):

- C1: Correct intent on first response
- C2: No made-up information (uses only provided context)
- C3: Includes specific next action (not vague suggestions)
- C4: Under 80 words
- C5: Clearly refuses or reroutes ambiguous/impossible requests

All 5 criteria must pass for output to be publishable.

### Strict Acceptance Criteria: support_agent

From locked eval file (evals/support-agent.md):

- C1: Resolves issue without escalation when resolution is possible
- C2: Uses ONLY knowledge base information (no invented policies)
- C3: Resolves within 3 messages
- C4: Escalates correctly when required
- C5: Under 120 words

All 5 criteria must pass for output to be publishable.

### Strict Acceptance Criteria: meeting_summary

From locked eval file (evals/meeting-summary.md):

- C1: Decisions clearly labeled as decisions
- C2: Action items include owner and deadline
- C3: Contains distinct sections (decisions, action items, open questions)
- C4: Open questions phrased as questions
- C5: Under 300 words

All 5 criteria must pass for output to be publishable.

### Round Scoring Acceptance Criteria

For every skill round:

1. **Inputs:**
   - Exactly 3 test inputs (unless skill explicitly versioned otherwise)
   - Exactly 10 outputs per input (30 total)

2. **Scoring:**
   - Round score calculation matches locked eval file definition
   - Promotion blocked if score <= previous best
   - Regression causes automatic revert to previous version

3. **Output Artifacts:**
   - results.log: Raw scorer output for all 30 outputs
   - analysis.md: Structured breakdown of passing/failing criteria
   - learnings.md: What to change for next round
   - changelog.md: Entry added with score and date

4. **Promotion Logic:**
   - New score must be at least 2% higher than previous best to promote
   - All hard gates must pass (C1-C5 for that skill)
   - Previous version reverted if new version fails

### Definition of Done for Tier 1 Skill

- Eval file locked (immutable, versioned)
- Runner locked (immutable, no changes to scoring logic)
- Baseline round recorded (Round 1 in changelog)
- At least one promoted prompt version (score > baseline)
- Failing outputs logged with failed criteria details
- Passing outputs eligible for gold example storage (>90th percentile)
- Hard-gate failures tested to prove publish is blocked

## Critical Area 5: Eval Contract Enforcement

**Importance:** High. The repo currently has eval path inconsistencies (.yaml vs .md).

**Files Under Test**
- services/knowledge-hub/db/schema.sql (seed data section)
- evals/*.md (locked files)
- evals/runners/*.py (immutable runners)

### Test Files

```
tests/unit/evals/test_eval_file_registry.py
tests/unit/evals/test_seeded_criteria_match_locked_files.py
tests/unit/evals/test_eval_path_consistency.py
```

### Strict Acceptance Criteria

1. **File Path Consistency:**
   - All references use .md (not .yaml)
   - Schema seed data references .md files
   - Runner config references .md files
   - Docs reference .md files

2. **Criteria Alignment:**
   - Seeded evaluation_criteria_catalog entries match locked eval file criteria for Tier 1 skills
   - Criterion count matches (e.g., agent_system_prompt has exactly 5 hard gates in both schema and eval file)
   - Criterion names/keys match between schema and eval file

3. **CI Enforcement:**
   - CI fails if schema references different path format than actual e files
   - CI fails if seeded criteria count differs from locked eval file count
   - CI fails if criterion names do not match

### Definition of Done

- One authoritative path format chosen (.md) and enforced
- All Tier 1 skills pass alignment tests
- CI blocks any merge that violates alignment

## Critical Area 6: Publishing Gates

**Importance:** Prevents bad outputs from escaping.

**Files Under Test**
- services/*/publish_to_confluence.ts
- services/*/publish_to_jira.ts

### Test Files

```
tests/unit/publish/test_publish_guards.py
tests/integration/publish/test_publish_to_confluence.py
tests/integration/publish/test_publish_to_jira.py
```

### Strict Acceptance Criteria

Publish MUST be blocked when:

1. Hard-gate criteria fail (any C1-C5 is fail)
2. Freshness is below threshold (< 0.6)
3. Skill/artifact type mismatch (e.g., landing_page_copy artifact tagged for agent_system_prompt skill)
4. Required fields missing (owner, dates when required by skill)
5. Confidence score below publish threshold (< 0.7)

Publish MUST include:

1. Source references (which entities were used)
2. Evaluation score (score_percent from latest round)
3. Artifact metadata (skill_name, version, generated_at)
4. Version reference (which prompt_version was used)

### Definition of Done

- At least one Confluence publish flow works end-to-end
- At least one Jira artifact publish flow works end-to-end
- All negative-path gate tests pass (prove that blocking works)

## Critical Area 7: Planning Sync and Trust-Based Reporting

**Importance:** First reporting layer worth making real.

**Files Under Test**
- services/planning-sync/src/hierarchy_rules.ts
- services/planning-sync/src/field_map.ts
- services/planning-sync/src/validate_taxonomy.ts
- services/planning-sync/src/generate_report_summary.ts
- services/planning-sync/src/escalate_reporting_gap.ts

### Test Files

```
tests/unit/planning/test_hierarchy_rules.py
tests/unit/planning/test_field_mapping.py
tests/unit/planning/test_validate_taxonomy.py
tests/unit/planning/test_generate_report_summary.py
tests/unit/planning/test_reporting_gap_escalation.py
tests/e2e/test_phase3_sync_to_report.py
```

### Strict Acceptance Criteria

1. **Hierarchy Validation:**
   - No orphaned items (every story has a parent epic)
   - Circular references detected and rejected

2. **Field Mapping:**
   - All mappings deterministic (same source status always maps to same canonical status)
   - Invalid statuses rejected with clear error

3. **Report Generation:**
   - Output follows structure: Decisions, Action Items, Open Questions
   - Every action item includes owner and deadline (or explicit TODO marker)
   - Decisions stated as decisions (not ambiguous claims)
   - Open questions phrased as questions

4. **Missing Data Handling:**
   - Missing-data gaps explicitly stated in output
   - No invented ownership, dates, or status
   - Escalation flags set when data quality is below threshold

### Definition of Done

- One trusted report generated from real synced planning data
- Missing-data flags visible in output
- Ambiguity explicitly called out (not invented)

## Critical Area 8: Metric Trust and Narrative Generation

**Importance:** Data trust foundation for Phase 4.

**In Scope (First)**
- Metabase
- PostHog
- Google Analytics

**Out of Scope (For Now)**
- Klaviyo, NetXD, Sardine, Socure

**Files Under Test**
- services/metrics/src/metric_catalog.ts
- services/metrics/src/normalization/*.ts
- services/metrics/src/create_snapshot.ts
- services/metrics/src/render_internal_summary.ts
- services/metrics/src/render_exec_subject.ts
- services/metrics/src/score_metric_trust.ts

### Test Files

```
tests/unit/metrics/test_metric_catalog.py
tests/unit/metrics/test_normalize_org_id.py
tests/unit/metrics/test_score_metric_trust.py
tests/integration/metrics/test_snapshot_generation.py
tests/integration/metrics/test_internal_summary_render.py
tests/integration/metrics/test_exec_subject_render.py
tests/e2e/test_phase4_metric_to_narrative.py
```

### Strict Acceptance Criteria

1. **Metric Catalog:**
   - Every metric has owner and source of truth defined
   - Canonical metric IDs unique and stable

2. **Normalization:**
   - Normalized identifiers used consistently in snapshots
   - org_id normalization deterministic

3. **Trust Scoring:**
   - Combines freshness, consistency, and definition completeness
   - Interpretation trust distinct from data trust
   - Never returns "trusted" when freshness < 24 hours old for that metric

4. **Narrative Generation:**
   - Internal summaries satisfy meeting_summary constraints when used
   - Exec headlines satisfy newsletter_headline constraints when used
   - Narrative blocked if mapped skill eval fails

### Definition of Done

- One weekly summary generated from real metric inputs
- Trust score visible and justified in output
- Narrative blocked on skill eval failure

## Critical Area 9: Results Analyzer and Skill Loop Observability

**Importance:** What makes optimization loops real.

**Files Under Test**
- autoresearch-toolkit/autoresearch-toolkit/results-analyzer/*.py (when integrated)
- scripts/analyze_results.py (new file)

### Test Files

```
tests/unit/results/test_parse_results_log.py
tests/unit/results/test_generate_analysis_md.py
tests/unit/results/test_generate_learnings_md.py
tests/integration/results/test_full_results_artifacts.py
```

### Strict Acceptance Criteria

1. **Parsing:**
   - Results log parsed correctly
   - Baseline vs. subsequent rounds classified correctly
   - Kept and reverted rounds identified

2. **Analysis:**
   - Criterion improvement summary accurate
   - Failure breakdown correct

3. **Learnings:**
   - Learnings file generated from valid results log
   - Identifies high-frequency failure patterns
   - Suggests concrete next changes

4. **Error Handling:**
   - Malformed log fails safely with explicit error
   - Does not crash on missing sections

### Definition of Done

- One full skill round produces valid analyzer outputs automatically
- Learnings guide next prompt iteration

## Critical Area 10: UI Support Export-Readiness

**Importance:** High-impact later, not first.

**Files Under Test**
- services/ui-support/src/style/minimalist_fintech_rules.ts
- services/ui-support/src/evals/validate_export_readiness.ts
- services/ui-support/src/mapping/map_artifact_skill.ts

### Test Files

```
tests/unit/ui/test_minimalist_fintech_rules.py
tests/unit/ui/test_export_readiness.py
tests/unit/ui/test_map_artifact_skill.py
tests/e2e/test_phase5_ui_request_to_publish.py
```

### Strict Acceptance Criteria

1. **Style Validation:**
   - Fails if hard-coded pixel positioning detected
   - Passes responsive layouts
   - Enforces 40% whitespace minimum

2. **Artifact Mapping:**
   - Every artifact maps to exactly one intended skill
   - Mapping deterministic

3. **Export Readiness:**
   - Copy fails if intended-surface skill eval fails
   - Code readiness: responsive, no hard-coded positioning, dark mode compatible
   - Artifact cannot publish unless both code AND copy pass

### Definition of Done

- One UI artifact passes export-readiness end-to-end
- Both code and copy checked before publish

## CI/CD Pipeline

### Required CI Jobs

All jobs must pass before merge:

1. **schema-tests** - All schema validation tests
2. **connector-unit-tests** - All unit tests for connectors
3. **connector-integration-tests** - All integration tests for connectors
4. **knowledge-api-tests** - Query API and retrieval tests
5. **skill-eval-tests** - All Tier 1 skill tests
6. **publish-guard-tests** - Publish blocking logic tests
7. **planning-report-tests** - Planning sync and reporting tests
8. **metrics-trust-tests** - Metric trust and narrative tests
9. **results-analyzer-tests** - Results analyzer tests
10. **e2e-critical-path** - End-to-end critical path test

### Merge Blocking Rules

PR cannot merge if ANY of these fail:

- Tier 1 skill eval alignment tests fail
- Hard-gate publish test fails (blocking gate does not work)
- Schema drift test fails (eval paths inconsistent)
- Confidence or freshness tests fail
- E2E for impacted critical path fails
- Code does not typecheck (Node.js strict mode)
- Code does not pass linting

### Post-Merge Deployment

After CI passes:

1. Schema applied to staging DB
2. Seed data verified
3. Connectors tested against staging data
4. Query API smoke test
5. Skill evaluation sanity check
6. Publish flow manual verification

## Implementation Checkpoints

### Before Phase 1 Coding Starts

- [x] Schema tests written and passing
- [x] Base connector framework tests written
- [ ] Jira connector unit test written (but failing, TDD style)

### Before Phase 2 Coding Starts

- [ ] Connectors implemented and integrated
- [ ] Query API tested and live
- [ ] Tier 1 skill tests written (but failing)

### Before Phase 3 Coding Starts

- [ ] Tier 1 skills live and promoting
- [ ] Planning sync tests written

### Before Phase 4 Coding Starts

- [ ] Planning sync live
- [ ] Metrics trust tests written

### Before Phase 5 Coding Starts

- [ ] Query API healthy with high coverage
- [ ] Skills generating trusted outputs
- [ ] UI support tests written

## Testing Philosophy

### Why TDD First

- Tests define the contract before code
- Catch design issues early (before implementation wasted)
- Regression tests prevent backsliding
- CI gates prevent broken main branch

### Test Organization

- Unit tests: `tests/unit/{area}/`
- Integration tests: `tests/integration/{area}/`
- E2E tests: `tests/e2e/`
- Critical path tests should be tagged `@critical`

### Test Naming Convention

Bad names:
- `test_thing_works`
- `test_api`
- `test_stuff`

Good names:
- `test_confidence_score_reduces_when_freshness_below_threshold`
- `test_publish_blocks_when_hard_gate_fails`
- `test_connector_retry_with_exponential_backoff`

### Acceptance Criteria Definition

Every test should have explicit assertions:

```python
# Good
def test_agent_system_prompt_fails_without_next_action(eval_runner):
    output = "We can help with account resets."  # No specific next action
    result = eval_runner.score_output(output, "test_input")
    assert result['pass_fail'] == 'fail'
    assert 'specific_next_action' in result['failed_criteria']

# Bad
def test_agent_system_prompt(eval_runner):
    output = "Some output"
    result = eval_runner.score_output(output, "test_input")
    assert result  # Doesn't test anything specific
```

## Success Metrics

### Phase 1 Is Complete When

- Schema tests: 100% pass rate
- Jira connector: Syncs 100+ real issues, no duplicates
- Confluence connector: Syncs 50+ pages with metadata
- Query API: Returns answers with citations for 95%+ of queries
- Confidence: Scores prove freshness + citation impact

### Phase 2 Is Complete When

- agent_system_prompt: 85%+ of outputs pass all hard gates
- support_agent: 90%+ of outputs pass all hard gates
- meeting_summary: 80%+ of outputs pass all hard gates
- No skill promotes without score improvement
- Regression logs prove rollback works

### Phase 3 Is Complete When

- Jira/Dragonboat sync: 100% field mapping accuracy
- No orphaned items: Validation catches all hierarchy violations
- Report summary: Reads like human-written, clear decisions/actions/questions

### Phase 4 Is Complete When

- Metric snapshots: Daily generation works reliably
- Trust scores: Correlate with data quality (fresh > stale)
- Narratives: Generated by correct skill, match constraints

### Phase 5 Is Complete When

- UI artifacts: Export-ready validation 100% accurate
- No bad copy: Skill eval failures block publish 100%
- Style rules: Whitespace/responsive/component checks all pass

---

**Last Updated:** 2026-04-18  
**Status:** Ready for implementation

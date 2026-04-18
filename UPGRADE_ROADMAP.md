# DreamFi Massive Upgrade — Complete Roadmap

**North Star:** Turn DreamFi into a production-grade product operations + evaluation + reporting platform that ingests trusted data, answers grounded questions with citations, generates high-quality artifacts through locked evals, promotes prompts only on measurable improvement, blocks low-trust outputs, produces operational and executive narratives with trust scores, and gives the team observability, reproducibility, and rollback safety.

---

## Upgrade Program Structure

### 10 Parallel Tracks (with explicit dependencies)

| Track | Focus | Priority | Depends On |
|-------|-------|----------|-----------|
| **Track A** | Core platform hardening | 🔴 CRITICAL | None (foundation) |
| **Track B** | Connector maturity | 🔴 CRITICAL | Track A |
| **Track C** | Knowledge hub intelligence | 🟠 HIGH | Track B |
| **Track D** | Skill engine and eval rigor | 🟠 HIGH | Track A |
| **Track E** | Publish and workflow controls | 🟠 HIGH | Track D |
| **Track F** | Planning and reporting trust | 🟡 MEDIUM | Track B, C |
| **Track G** | Metrics and interpretation trust | 🟡 MEDIUM | Track F |
| **Track H** | UI support and artifact quality | 🟡 MEDIUM | Track D, E |
| **Track I** | Governance, security, reproducibility | 🟡 MEDIUM | All |
| **Track J** | Developer velocity and internal UX | 🟢 ENABLING | All |

---

## Phase Timeline

### Phase 1: Foundation (Weeks 1-3)
- ✅ Track A: Core platform hardening (A1, A2, A3)
- ✅ Track B: Connector framework (B1)
- ✅ Track D: Tier 1 skill setup (D1, D3)
- ✅ Track J: DX scaffolding (J2)
- 🔗 **Gate:** E2E 1 (query → answer with citations)

### Phase 2: Generate and Evaluate (Weeks 4-6)
- ✅ Track B: Real connectors (B2, B3)
- ✅ Track C: Knowledge hub intelligence (C1-C5)
- ✅ Track D: Tier 1 complete + results analyzer (D1-D4)
- ✅ Track E: Publish guards (E1)
- 🔗 **Gate:** E2E 2 (generate → eval → publish)

### Phase 3: Planning and Sync (Weeks 7-9)
- ✅ Track F: Planning sync + reporting (F1-F3)
- ✅ Track B: Webhook support (B3)
- ✅ Track I: Data handling policy (I1)
- 🔗 **Gate:** E2E 3 (sync → trusted report)

### Phase 4: Metrics and Narrative (Weeks 10-12)
- ✅ Track G: Metrics catalog + trust scoring (G1-G4)
- ✅ Track D: Tier 2/3 skills (D2)
- ✅ Track I: RACI + governance (I2-I4)
- 🔗 **Gate:** E2E 4 (metrics → audience narrative)

### Phase 5: Publishing and UI (Weeks 13-15)
- ✅ Track H: UI support + export readiness (H1-H3)
- ✅ Track E: Artifact versioning + manual review (E2, E3)
- ✅ Track J: Internal console (J1)
- 🔗 **Gate:** E2E 5 (UI request → publishable artifact)

### Phase 6: Observability and Hardening (Weeks 16-18)
- ✅ Track J: Observability and runbooks (J3)
- ✅ Track I: Finalization (prompt governance)
- ✅ All tracks: Integration and load testing
- 🔗 **Gate:** All E2E tests green, operational thresholds met

---

## Track A — Core Platform Hardening

### A1. Fix source-of-truth drift

**Problem:** Platform risks silent schema/eval/docs/runner drift.

**Files to Create:**
- `tools/contracts/skill_contract_loader.ts`
- `tools/contracts/validate_skill_contracts.ts`
- `tools/contracts/generate_db_seed_from_evals.ts`
- `tools/contracts/generate_skill_registry_docs.ts`

**Tests:**
- `tests/unit/contracts/test_skill_contract_loader.py`
- `tests/unit/contracts/test_contract_to_schema_alignment.py`
- `tests/unit/contracts/test_contract_to_runner_alignment.py`
- `tests/integration/contracts/test_contract_drift_ci_gate.py`

**Acceptance Criteria:**
- ✅ Every Tier 1 skill maps to exactly one locked eval file
- ✅ No skill exists in schema without locked eval
- ✅ No runner exists without locked eval
- ✅ No doc entry exists without schema skill
- ✅ CI fails on any contract mismatch
- ✅ Repo can regenerate seed/docs from source-of-truth contract files

---

### A2. Migration-based schema management

**Problem:** Single big schema file insufficient long-term.

**Files to Create:**
- `services/knowledge-hub/db/migrations/001_initial_schema.sql`
- `services/knowledge-hub/db/migrations/002_add_artifact_versioning.sql`
- `services/knowledge-hub/db/seeds/seed_skills.ts`
- `services/knowledge-hub/db/seeds/seed_eval_criteria.ts`
- `services/knowledge-hub/db/seeds/seed_test_inputs.ts`
- `scripts/db/reset_test_db.sh`

**Tests:**
- `tests/unit/schema/test_migrations_apply_cleanly.py`
- `tests/unit/schema/test_migrations_are_reversible.py`
- `tests/integration/schema/test_seed_is_deterministic.py`

**Acceptance Criteria:**
- ✅ Migrations apply on empty DB
- ✅ Migrations roll back safely in test env
- ✅ Seed scripts are deterministic
- ✅ No manual SQL edits required

---

### A3. Service boot reliability

**Problem:** Services need health checks and startup validation.

**Files to Create:**
- `shared/config/env.ts`
- `shared/health/health_router.ts`
- `shared/health/readiness.ts`

**Tests:**
- `tests/unit/config/test_env_validation.py`
- `tests/api/test_health_endpoints.py`

**Acceptance Criteria:**
- ✅ Every service exposes `/health` and `/ready`
- ✅ Service fails fast on missing required env vars
- ✅ Readiness fails if required DB/connectors unavailable

---

## Track B — Connector Maturity

### B1. Connector framework standardization

**Files to Create:**
- `services/knowledge-hub/src/connectors/base_connector.ts`
- `services/knowledge-hub/src/connectors/types.ts`
- `services/knowledge-hub/src/connectors/errors.ts`
- `services/knowledge-hub/src/connectors/freshness.ts`
- `services/knowledge-hub/src/connectors/checkpoint_store.ts`

**Tests:**
- `tests/unit/connectors/test_base_connector.py`
- `tests/unit/connectors/test_freshness_scoring.py`
- `tests/unit/connectors/test_checkpointing.py`
- `tests/unit/connectors/test_connector_error_model.py`

**Acceptance Criteria:**
- ✅ Every connector implements identical lifecycle methods
- ✅ Full sync + incremental sync support
- ✅ Typed error emission
- ✅ Deterministic freshness scoring
- ✅ Watermark/checkpoint storage
- ✅ Retry/backoff without duplicate writes

---

### B2. Real implementation of top-priority connectors

**Priority Order:** Jira → Confluence → Dragonboat → Metabase → PostHog → GA → Lucidchart → Klaviyo → NetXD → Sardine → Socure

**Test Pattern per Connector:**
- `tests/unit/connectors/test_<name>_connector.py`
- `tests/integration/connectors/test_<name>_sync.py`

**Acceptance Criteria per Connector:**
- ✅ Authenticates successfully
- ✅ Fetches at least one real fixture payload
- ✅ Normalizes payload into canonical structure
- ✅ Stores required source metadata
- ✅ Computes freshness
- ✅ Handles incremental sync
- ✅ Skips unchanged records using hash
- ✅ Dead-letters malformed payloads
- ✅ Integration tests green in CI

---

### B3. Webhook support for near-real-time sync

**Files to Create:**
- `services/knowledge-hub/src/webhooks/webhook_receiver.ts`
- `services/knowledge-hub/src/webhooks/jira_webhook.ts`
- `services/knowledge-hub/src/webhooks/confluence_webhook.ts`

**Tests:**
- `tests/unit/webhooks/test_signature_validation.py`
- `tests/unit/webhooks/test_dedupe.py`
- `tests/integration/webhooks/test_event_to_sync_pipeline.py`

**Acceptance Criteria:**
- ✅ Duplicate event IDs ignored
- ✅ Invalid signatures rejected
- ✅ Valid events enqueue sync job
- ✅ Replay-safe behavior verified

---

## Track C — Knowledge Hub Intelligence

### C1. Better retrieval orchestration

**Files to Create:**
- `services/knowledge-hub/src/retrieval/retrieve_context.ts`
- `services/knowledge-hub/src/retrieval/rank_results.ts`
- `services/knowledge-hub/src/retrieval/retrieve_gold_examples.ts`
- `services/knowledge-hub/src/retrieval/retrieve_failure_patterns.ts`

**Tests:**
- `tests/unit/knowledge/test_retrieve_context.py`
- `tests/unit/knowledge/test_rank_results.py`
- `tests/unit/knowledge/test_gold_example_retrieval.py`
- `tests/unit/knowledge/test_failure_pattern_retrieval.py`

**Acceptance Criteria:**
- ✅ Matching gold examples returned for matching skill/scenario
- ✅ Fresher sources outrank stale ones when relevance is close
- ✅ Retrieved contexts always include source references
- ✅ Retrieval output is deterministic for same test dataset

---

### C2. Canonical entity linking and deduplication

**Files to Create:**
- `services/knowledge-hub/src/entity-resolution/resolve_entities.ts`
- `services/knowledge-hub/src/entity-resolution/merge_rules.ts`

**Tests:**
- `tests/unit/knowledge/test_entity_resolution.py`
- `tests/unit/knowledge/test_alias_mapping.py`
- `tests/unit/knowledge/test_duplicate_detection.py`

**Acceptance Criteria:**
- ✅ Same logical entity across sources maps to one canonical record
- ✅ Duplicate entities detected and merge candidates surfaced
- ✅ No unintended merges in test fixtures

---

### C3. Citation quality enforcement

**Files to Create:**
- `services/knowledge-hub/src/citations/validate_citations.ts`

**Tests:**
- `tests/unit/knowledge/test_citation_validation.py`

**Acceptance Criteria:**
- ✅ Supported answer claims carry citations
- ✅ Unsupported claims lower confidence or block answer
- ✅ No cited answer returned with zero citations for supported query types

---

### C4. Confidence model v2

**Files to Create:**
- `services/knowledge-hub/src/confidence/score_confidence.ts`
- `services/knowledge-hub/src/confidence/types.ts`

**Tests:**
- `tests/unit/knowledge/test_score_confidence.py`
- `tests/unit/knowledge/test_confidence_penalties.py`

**Acceptance Criteria:**
- ✅ Deterministic output for fixed inputs
- ✅ Stale source lowers confidence
- ✅ Contradiction lowers confidence
- ✅ Failed hard gate prevents high confidence state
- ✅ Low citation count reduces confidence

---

### C5. Query API and internal UI

**Files to Create:**
- `services/knowledge-hub/src/api/query.ts`
- `services/knowledge-hub/src/api/entity.ts`
- `services/knowledge-hub/src/api/evals.ts`
- `apps/internal-hub/` (full app)

**Tests:**
- `tests/api/test_query_endpoint.py`
- `tests/api/test_entity_endpoint.py`
- `tests/e2e/test_phase1_query_to_answer.py`

**Acceptance Criteria:**
- ✅ Answer returns citations, freshness, confidence
- ✅ Agent-style answers include next action
- ✅ Impossible/ambiguous requests clearly refuse or reroute
- ✅ UI displays source refs and confidence clearly

---

## Track D — Skill Engine and Eval Rigor

### D1. Tier 1 skill implementation first

**Skills:** agent_system_prompt, support_agent, meeting_summary

**Files to Create:**
- `services/generators/src/generate/generate_output.ts`
- `services/generators/src/evals/run_skill_round.ts`
- `services/generators/src/prompts/agent_system_prompt.md`
- `services/generators/src/prompts/support_agent.md`
- `services/generators/src/prompts/meeting_summary.md`
- `services/generators/src/promotion/promote_prompt.ts`

**Tests:**
- `tests/unit/generators/test_agent_system_prompt.py`
- `tests/unit/generators/test_support_agent.py`
- `tests/unit/generators/test_meeting_summary.py`
- `tests/integration/evals/test_round_scoring.py`
- `tests/integration/evals/test_prompt_promotion.py`

**Acceptance Criteria:**
- ✅ 10 outputs per test input generated
- ✅ Scores computed per locked eval
- ✅ No prompt promoted without improvement
- ✅ Passing outputs stored
- ✅ Failing outputs logged with failed criteria
- ✅ Gold-example promotion works

---

### D2. Tier 2 and Tier 3 rollout

**Skills:** cold_email, landing_page_copy, newsletter_headline, product_description, resume_bullet, short_form_script

**Tests per Skill:**
- `tests/unit/generators/test_<skill>.py` (hard gates)
- `tests/integration/evals/test_<skill>_round_scoring.py`

**Acceptance Criteria:**
- ✅ Every skill has unit tests for all hard gates
- ✅ Integration tests for full round scoring
- ✅ Publish blocking on hard-gate failure
- ✅ At least one successful promoted prompt version before general use

---

### D3. Eval runner integrity and immutability

**Files to Create:**
- `tools/evals/verify_immutability.ts`

**Tests:**
- `tests/integration/evals/test_eval_runner_locking.py`
- `tests/unit/evals/test_locked_eval_checksum.py`

**Acceptance Criteria:**
- ✅ Eval files cannot be changed without explicit contract update path
- ✅ Runner checksum mismatch fails CI
- ✅ Score logic reproducible across repeated runs

---

### D4. Results analyzer full integration

**Files to Create:**
- `services/generators/src/results/analyze_run.ts`
- `services/generators/src/results/surface_learnings.ts`

**Tests:**
- `tests/unit/results/test_parse_results_log.py`
- `tests/unit/results/test_generate_analysis_md.py`
- `tests/unit/results/test_generate_learnings_md.py`
- `tests/integration/results/test_full_results_artifacts.py`

**Acceptance Criteria:**
- ✅ Analyzer runs automatically after round completion
- ✅ analysis.md and learnings.md generated correctly
- ✅ Malformed log handled safely
- ✅ Learnings accessible from internal UI

---

### D5. Multi-version prompt lifecycle management

**Files to Create:**
- `services/generators/src/prompts/prompt_lifecycle.ts`
- `apps/internal-hub/src/pages/prompts/`

**Tests:**
- `tests/unit/prompts/test_prompt_lifecycle.py`
- `tests/unit/prompts/test_single_active_prompt_rule.py`

**Acceptance Criteria:**
- ✅ Only one active prompt per skill
- ✅ Rollback restores previous active version
- ✅ No deleted prompt history
- ✅ State transitions validated

---

## Track E — Publish and Workflow Controls

### E1. Hard-gate publishing enforcement

**Files to Create:**
- `services/shared/publish/guard.ts`
- `services/shared/publish/compatibility.ts`

**Tests:**
- `tests/unit/publish/test_publish_guards.py`
- `tests/integration/publish/test_publish_to_confluence.py`
- `tests/integration/publish/test_publish_to_jira.py`

**Acceptance Criteria:**
- ✅ Publishing blocked if hard-gate criteria fail
- ✅ Publishing blocked if freshness below threshold
- ✅ Publishing blocked if confidence below threshold
- ✅ Publishing blocked if required metadata missing
- ✅ Publishing blocked if skill does not match artifact type

---

### E2. Artifact versioning and reproducibility

**Schema Changes:**
- `artifact_versions` table
- `generation_context_snapshot` table
- `publish_events` table

**Files to Create:**
- `services/shared/artifacts/artifact_versioning.ts`
- `services/shared/artifacts/generation_snapshot.ts`

**Tests:**
- `tests/unit/artifacts/test_artifact_versioning.py`
- `tests/unit/artifacts/test_generation_snapshot.py`
- `tests/integration/artifacts/test_reproducible_regeneration.py`

**Acceptance Criteria:**
- ✅ Every published artifact references prompt version, source snapshot, eval score, publish event
- ✅ Artifact can be reproduced from stored snapshot in test environment

---

### E3. Human review workflow for borderline outputs

**Files to Create:**
- `apps/internal-hub/src/pages/review-queue/`
- `services/shared/review/review_queue.ts`

**Tests:**
- `tests/unit/review/test_review_queue.py`
- `tests/integration/review/test_manual_approval_flow.py`

**Acceptance Criteria:**
- ✅ Borderline outputs route to queue
- ✅ Reviewers can approve/reject with comment
- ✅ Rejected output cannot publish
- ✅ Approval action logged

---

## Track F — Planning and Reporting Trust

### F1. Jira/Dragonboat canonical planning model

**Files to Create:**
- `services/planning-sync/src/mapping/status_mapping.ts`
- `services/planning-sync/src/validation/validate_taxonomy.ts`

**Tests:**
- `tests/unit/planning/test_hierarchy_rules.py`
- `tests/unit/planning/test_field_mapping.py`
- `tests/unit/planning/test_validate_taxonomy.py`

**Acceptance Criteria:**
- ✅ No orphaned items
- ✅ Deterministic mappings only
- ✅ Invalid status transitions rejected
- ✅ Missing required fields flagged

---

### F2. Trust-based report generation

**Files to Create:**
- `services/planning-sync/src/reporting/generate_report_summary.ts`
- `services/planning-sync/src/reporting/escalate_reporting_gap.ts`

**Tests:**
- `tests/unit/planning/test_generate_report_summary.py`
- `tests/unit/planning/test_reporting_gap_escalation.py`
- `tests/e2e/test_phase3_sync_to_report.py`

**Acceptance Criteria:**
- ✅ Summary format includes Decisions, Action Items, Open Questions
- ✅ Missing data is explicit
- ✅ No invented owners or dates
- ✅ Trust flags visible in output

---

### F3. Leadership reporting UX

**Files to Create:**
- `apps/internal-hub/src/pages/reports/`

**Tests:**
- `tests/integration/planning/test_report_dashboard_data.py`

**Acceptance Criteria:**
- ✅ Leadership can see trusted vs untrusted reports
- ✅ Stale dashboards clearly marked
- ✅ Snapshot history preserved

---

## Track G — Metrics and Interpretation Trust

### G1. Metric catalog hardening

**Files to Create:**
- `services/metrics/src/catalog/metric_catalog.ts`

**Tests:**
- `tests/unit/metrics/test_metric_catalog.py`

**Acceptance Criteria:**
- ✅ No metric exists without owner and source-of-truth
- ✅ No dashboard metric rendered without catalog registration

---

### G2. Cross-source normalization

**Files to Create:**
- `services/metrics/src/normalize/normalize_org_id.ts`
- `services/metrics/src/normalize/normalize_funnel_stage.ts`
- `services/metrics/src/normalize/normalize_fraud_decision.ts`
- `services/metrics/src/normalize/normalize_date_grain.ts`

**Tests:**
- `tests/unit/metrics/test_normalize_org_id.py`
- `tests/unit/metrics/test_normalize_funnel_stage.py`
- `tests/unit/metrics/test_normalize_fraud_decision.py`
- `tests/unit/metrics/test_normalize_date_grain.py`

**Acceptance Criteria:**
- ✅ Same logical org maps to one normalized ID
- ✅ Funnel stages are canonical
- ✅ Fraud decisions normalized consistently
- ✅ Snapshot output uses normalized values only

---

### G3. Trust scoring for metric outputs

**Files to Create:**
- `services/metrics/src/trust/score_metric_trust.ts`
- `services/metrics/src/interpretation/render_internal_summary.ts`
- `services/metrics/src/interpretation/render_exec_subject.ts`
- `services/metrics/src/interpretation/render_product_description.ts`

**Tests:**
- `tests/unit/metrics/test_score_metric_trust.py`
- `tests/integration/metrics/test_internal_summary_render.py`
- `tests/integration/metrics/test_exec_subject_render.py`
- `tests/integration/metrics/test_product_summary_render.py`
- `tests/e2e/test_phase4_metric_to_narrative.py`

**Acceptance Criteria:**
- ✅ Internal narrative maps to meeting_summary
- ✅ Exec subject/preview maps to newsletter_headline
- ✅ External/release summary maps to product_description
- ✅ Narrative blocked if assigned skill eval fails
- ✅ Trust score visible in output

---

### G4. Metric anomaly detection and discrepancy management

**Files to Create:**
- `services/metrics/src/anomaly/detect_anomalies.ts`
- `services/metrics/src/anomaly/manage_discrepancies.ts`

**Tests:**
- `tests/unit/metrics/test_anomaly_detection.py`
- `tests/unit/metrics/test_discrepancy_penalty.py`

**Acceptance Criteria:**
- ✅ Discrepancies across sources are flagged
- ✅ Trust score decreases on unresolved mismatch
- ✅ Anomaly state visible in UI and API

---

## Track H — UI Support and Artifact Quality

### H1. Minimalist fintech rule engine

**Files to Create:**
- `services/ui-support/src/style/minimalist_fintech_rules.ts`

**Tests:**
- `tests/unit/ui/test_minimalist_fintech_rules.py`

**Acceptance Criteria:**
- ✅ Style rule engine produces deterministic pass/fail per artifact
- ✅ Spacing/layout violations explicitly listed

---

### H2. Export readiness validator

**Files to Create:**
- `services/ui-support/src/evals/validate_export_readiness.ts`

**Tests:**
- `tests/unit/ui/test_export_readiness.py`
- `tests/integration/ui/test_publish_ui_spec.py`

**Acceptance Criteria:**
- ✅ Hard-coded pixel layouts fail
- ✅ Responsive layouts pass
- ✅ Copy must pass intended-surface skill
- ✅ Artifact blocked from publish if either code or copy fails

---

### H3. Artifact-to-skill mapping rigor

**Files to Create:**
- `services/ui-support/src/copy/map_artifact_skill.ts`

**Tests:**
- `tests/unit/ui/test_map_artifact_skill.py`

**Acceptance Criteria:**
- ✅ Every artifact type resolves to exactly one skill
- ✅ Unsupported artifact types fail fast
- ✅ Copy generation cannot proceed without mapped skill

---

## Track I — Governance, Security, Reproducibility

### I1. Sensitive data handling policy enforcement

**Files to Create:**
- `docs/security/data-handling-policy.md`
- `services/shared/security/redact_for_llm.ts`

**Tests:**
- `tests/unit/security/test_redaction.py`
- `tests/unit/security/test_llm_safe_projection.py`

**Acceptance Criteria:**
- ✅ Raw sensitive payloads never sent directly to generation layer
- ✅ Restricted fields redacted before LLM context use
- ✅ Security test suite covers fraud/identity/ledger samples

---

### I2. RACI and operating model

**Files to Create:**
- `docs/governance/raci.md`
- `docs/governance/prompt-promotion-policy.md`

**Enforcement:**
- PR template requires owner assignment
- Prompt promotion command requires approver metadata

**Acceptance Criteria:**
- ✅ Each critical workflow has named owner and approver
- ✅ Prompt promotions logged with actor and justification

---

### I3. Prompt lifecycle governance

**Files to Create:**
- `services/generators/src/prompts/prompt_approval_rules.ts`

**Tests:**
- `tests/unit/prompts/test_prompt_approval_rules.py`
- `tests/integration/prompts/test_prompt_rollback.py`

**Acceptance Criteria:**
- ✅ No prompt becomes production-active without passing eval
- ✅ Rollback restores previous active version safely
- ✅ Approval and rollback events logged

---

### I4. Identity resolution strategy

**Files to Create:**
- `docs/architecture/identity-resolution.md`
- `services/shared/identity/resolve_identity.ts`

**Tests:**
- `tests/unit/identity/test_resolve_identity.py`
- `tests/unit/identity/test_conflict_resolution.py`

**Acceptance Criteria:**
- ✅ Conflicting source IDs handled predictably
- ✅ Unresolved mappings surfaced for review
- ✅ Same org across analytics systems maps consistently

---

## Track J — Developer Velocity and Internal UX

### J1. Internal operator console

**Files to Create:**
- `apps/internal-hub/src/pages/connectors/`
- `apps/internal-hub/src/pages/evals/`
- `apps/internal-hub/src/pages/prompts/`
- `apps/internal-hub/src/pages/review-queue/`
- `apps/internal-hub/src/pages/artifacts/`

**Tests:**
- Component tests
- Route tests
- Core e2e operator flows

**Acceptance Criteria:**
- ✅ Operator can inspect connector freshness
- ✅ Operator can run a skill eval
- ✅ Operator can compare prompt versions
- ✅ Operator can review failing outputs
- ✅ Operator can inspect gold examples
- ✅ Operator can approve or reject borderline artifacts

---

### J2. Better DX scaffolding

**Files to Create:**
- `Makefile`
- `scripts/bootstrap_local.sh`
- `.pre-commit-config.yaml`

**Updates:**
- `.github/workflows/ci.yml`

**Tests:**
- `tests/integration/devx/test_bootstrap_local.py`

**Acceptance Criteria:**
- ✅ New dev can bootstrap locally in under 15 minutes
- ✅ Test DB and fixtures load with one command
- ✅ CI reproduces local test steps

---

### J3. Observability and runbooks

**Files to Create:**
- `docs/ops/runbooks.md`
- `services/shared/observability/metrics.ts`
- `services/shared/observability/alerting.ts`

**Tests:**
- `tests/unit/observability/test_alert_thresholds.py`

**Acceptance Criteria:**
- ✅ Stale connector alerts emitted
- ✅ Eval regressions visible
- ✅ Publish failures counted and surfaced
- ✅ Runbooks exist for top 5 incidents

---

## End-to-End Test Gates

### E2E 1 — Knowledge hub answer path
**File:** `tests/e2e/test_phase1_query_to_answer.py`

- ✅ Source sync completed
- ✅ Query returns answer with citations
- ✅ Freshness shown
- ✅ Confidence shown
- ✅ Next action included when skill requires it
- ✅ Impossible request is declined cleanly

### E2E 2 — Tier 1 skill generate-and-score
**File:** `tests/e2e/test_phase2_generate_to_publish.py`

- ✅ Skill generates output
- ✅ Locked eval runs
- ✅ Score stored
- ✅ Passing output promoted or publishable
- ✅ Failing output blocked

### E2E 3 — Planning sync to trusted report
**File:** `tests/e2e/test_phase3_sync_to_report.py`

- ✅ Jira + Dragonboat sync normalize correctly
- ✅ Report summary structured correctly
- ✅ Missing data clearly surfaced
- ✅ Trust flags present

### E2E 4 — Metrics to audience narrative
**File:** `tests/e2e/test_phase4_metric_to_narrative.py`

- ✅ Snapshot generated
- ✅ Normalized identifiers applied
- ✅ Correct audience skill selected
- ✅ Trust score present
- ✅ Failed narrative skill blocks final output

### E2E 5 — UI request to publishable artifact
**File:** `tests/e2e/test_phase5_ui_request_to_publish.py`

- ✅ UI artifact generated
- ✅ Copy skill assigned
- ✅ Export readiness validated
- ✅ Failing artifact blocked
- ✅ Approved artifact published and ingested back to hub

---

## Ultra-Strict Acceptance Thresholds

### Platform Thresholds
- 100% Tier 1 eval contract alignment
- 0 critical publish paths allowed without gating tests
- 0 production-active prompt versions without eval pass
- 0 "trusted" outputs without explicit trust/confidence value
- 0 supported knowledge answers without citations

### Service Thresholds
- Connector happy-path mapping tests: ≥90%
- Core skill hard-gate tests: 100%
- Publish guard tests: 100%
- Critical E2E flows: all green before release
- Schema migration tests: 100%

### Operational Thresholds
- Stale data must visibly lower confidence
- Unresolved discrepancies must visibly lower trust
- Malformed connector payloads must not crash pipeline
- Rollback path must be tested before production activation

---

## Critical Path Summary

```
Week 1-3: Track A + B1 + D1 + J2 → E2E 1 ✅
    ↓
Week 4-6: B2 + B3 + C + D2-4 + E1 → E2E 2 ✅
    ↓
Week 7-9: F + I1 → E2E 3 ✅
    ↓
Week 10-12: G + I2-4 → E2E 4 ✅
    ↓
Week 13-15: H + E2-3 + J1 → E2E 5 ✅
    ↓
Week 16-18: J3 + All integration & hardening → LIVE 🚀
```

---

## Implementation Notes

- **All tests use pytest** with markers for unit/integration/e2e/critical
- **All TypeScript uses strict mode** with explicit types
- **All connectors share base interface** from B1
- **Track A must be 100% complete** before merging other tracks
- **Build strictness enforced in CI** — failures block merges
- **Schema migrations reversible** — rollback tested every phase
- **Every test is deterministic** — no flaky tests
- **All data handling follows I1 policy** — no raw sensitive payloads to LLM
- **All artifacts versioned** — reproducible, rollback-safe


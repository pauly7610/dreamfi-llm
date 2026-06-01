# Workflow Skill Mining

Workflow skill mining is DreamFi's path from repeated expert work to a
reviewable skill candidate. It supports the "put your coworker into a skill"
idea without pretending we can or should copy a person wholesale.

The system captures the repeatable parts of a workflow:

- what kind of task started the work
- which sources were consulted
- which identifiers were required
- what order the tools and sources were used in
- what evidence was accepted or rejected
- what the human changed before approval
- whether the work was approved, rejected, revised, published, or used in a
  decision

It does not auto-create production skills. It creates candidate packages for
review.

## Data Model

`workflow_traces` records individual workflow executions.

Important fields:

- `workspace_id`
- `actor_id`
- `workflow_type`
- `starter_question_hash`
- `starter_question_pattern`
- `topic_id`
- `source_ids_json`
- `required_identifiers_json`
- `steps_json`
- `accepted_evidence_json`
- `rejected_evidence_json`
- `human_edits_json`
- `outcome`
- `private`

The raw starter question is not stored. DreamFi stores a SHA-256 hash plus a
redacted pattern. Emails, UUIDs, long source identifiers, transaction-like IDs,
decision-like IDs, member-like IDs, and account-like IDs are replaced with
placeholders before the pattern is stored.

`skill_candidates` records mined candidate packages.

Important fields:

- `workflow_type`
- `source_trace_count`
- `trace_ids_json`
- `intent_summary`
- `required_inputs_json`
- `source_contract_json`
- `tool_plan_json`
- `freshness_contract_json`
- `answer_contract_json`
- `refusal_rules_json`
- `eval_seed_cases_json`
- `status`
- `reviewer_id`
- `review_notes`

## API

The Python learning API owns the current implementation:

- `POST /api/learning/workflow-traces`
- `GET /api/learning/workflow-traces`
- `POST /api/learning/skill-candidates/generate`
- `GET /api/learning/skill-candidates`
- `POST /api/learning/skill-candidates/{candidate_id}/approve`
- `POST /api/learning/skill-candidates/{candidate_id}/reject`

The implementation lives in:

- `dreamfi/learning/skill_mining.py`
- `dreamfi/api/routes/learning.py`
- `dreamfi/db/models.py`
- `dreamfi/db/migrations/versions/20260529_0013_workflow_skill_mining.py`

## Mining Rules

Candidates are grouped by `(workspace_id, workflow_type)`.

By default, DreamFi only mines non-private traces from the last configured
window. The knobs are:

- `DREAMFI_SKILL_MINING_MIN_TRACES`
- `DREAMFI_SKILL_MINING_WINDOW_DAYS`
- `DREAMFI_SKILL_MINING_EVAL_SEED_LIMIT`

The miner derives:

- required inputs from identifiers that recur across traces
- source contract from selected source systems and their observed frequency
- tool plan from repeated step order
- freshness contract from selected sources
- answer contract from the workflow type
- refusal rules from required inputs and grounding constraints
- eval seed cases from redacted trace patterns

Operational sources get stricter freshness language. If traces use NetXD,
Sardine, or Socure, the candidate's freshness contract requires exact
source-of-truth checks and blocks stale authoritative conclusions.

## Review Flow

```text
Workflow traces
    |
    v
Cluster by workspace + workflow type
    |
    v
Draft SkillCandidate
    |
    v
Human review
    |
    +--> reject
    |
    +--> approve for a future governed skill PR
```

Approval is intentionally not the same as registry mutation. Locked eval files
under `evals/` are not edited by this system. A real skill still needs a normal
PR with tests, evals, docs, and human review.

## Privacy And Safety

Design choices:

- raw starter questions are not stored
- private traces are excluded from mining
- audit events store trace IDs, workflow type, source IDs, counts, and hashes,
  not raw questions or secrets
- candidate generation is idempotent while a draft or approved candidate exists
  for the same workspace/workflow
- rejected candidates remain part of review history

## Example

A fraud decline workflow may produce a candidate like:

```json
{
  "workflow_type": "fraud_decline_review",
  "required_inputs": ["decision_id", "transaction_id"],
  "source_contract": {
    "source_ids": ["netxd", "sardine", "socure"]
  },
  "freshness_contract": {
    "mode": "operational",
    "source_ids_requiring_source_of_truth_checks": ["netxd", "sardine", "socure"]
  },
  "refusal_rules": [
    "Required before execution: decision_id, transaction_id.",
    "Refuse unsupported source-of-truth claims when citations are absent."
  ]
}
```

That is enough for Product and Engineering to review whether the workflow
deserves a governed skill. It is not enough to ship the skill automatically.

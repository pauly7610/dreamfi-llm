# DreamFi LLM Outstanding Work

DreamFi LLM is now best described as a shared context and workflow-learning
engine for product, risk, and engineering work. Generation still matters, but
it is an output of grounded context, not the center of the platform.

This document is current against the repo after PR #28.

## Current State

What exists now:

- Go service at `cmd/dreamfi` with health, auth, scoped Ask, workflow generation,
  `/api/console`, and the templ console path.
- Python FastAPI app for mature support paths: skills, evals, publish, learning,
  settings, connector activation, context ask, and ops status.
- Active Python skill registry with 3 PM-adjacent skills:
  `meeting_summary`, `agent_system_prompt`, and `support_agent`.
- Archived marketing/copy skills kept on disk under `evals/` and recorded in
  `ARCHIVED_SKILLS`, without seeding or surfacing in the active Python path.
- Custom connector sync for Dragonboat, Metabase, PostHog, GA, Klaviyo, NetXD,
  Sardine, and Socure.
- Direct context connector clients for Jira, Confluence, Metabase, PostHog, and
  Slack.
- Typed context bundle path at `POST /v1/context/ask` with grounded claims,
  open questions, topic linking, and memory.
- Workflow trace and skill candidate mining under `/api/learning`, including
  redacted starter-question patterns, source contracts, tool plans, freshness
  contracts, refusal rules, and eval seed cases.

What does not exist yet:

- Runtime live evidence reads for exact recent operational records.
- A runtime planner that chooses source systems per question before Ask.
- Go parity for every Python learning, settings, skill, and context endpoint.
- Automatic conversion from approved skill candidate into a real governed skill
  PR. This should stay human-reviewed.

## Highest Priority

### 1. Runtime Freshness For Operational Questions

Problem:

Indexed evidence can be stale even when the source system is current. A fresh
NetXD ledger record must not be used as a proxy for a stale Sardine fraud
decision.

Files likely involved:

- `dreamfi/context/`
- `dreamfi/context_connectors/`
- `dreamfi/connectors.py`
- `dreamfi/api/routes/workflows.py`
- `internal/httpapi/workflows.go`
- `dreamfi/db/models.py`

Acceptance:

- Ask can classify questions as indexed, operational, or as-of.
- Operational questions require source-specific freshness contracts.
- Recent NetXD, Sardine, and Socure questions can fetch exact records by
  transaction, decision, member, or application identifier.
- Missing identifiers cause a follow-up question instead of broad connector
  search.
- Stale authoritative sources block the conclusion and name the missing source.
- Audit metadata records selected sources, freshness state, and blockers without
  raw secrets or raw question text.

Tests:

- Unit tests for planner classification and identifier extraction.
- Unit tests for NetXD/Sardine/Socure exact-record adapters with mocked HTTP.
- API tests showing stale Sardine blocks a fraud conclusion even when NetXD is
  fresh.
- API tests showing an exact live Sardine decision can satisfy the freshness
  contract without running continuous ETL.

### 2. Source Selection Before Retrieval

Problem:

`/api/ask` is scoped when the caller provides `topic_id`, `source_id`, or
`source_ids`, but DreamFi does not yet select the authoritative source set from
the question itself.

Acceptance:

- Ask builds a small context plan before retrieval.
- The plan chooses source systems, required identifiers, and freshness mode.
- The answer response includes selected source IDs, warnings, blockers, and
  citations.
- The planner remains deterministic enough for tests and audit review.

### 3. Skill Candidate To Skill PR Workflow

Problem:

PR #28 mines workflow traces into `SkillCandidate` rows, but approval is only a
review state. It does not yet create the implementation PR for a governed skill.

Acceptance:

- Approved candidates produce a checklist or generated branch plan with:
  skill ID, prompt contract, tool contract, eval cases, refusal rules, and docs.
- The process never edits `evals/` automatically.
- A human explicitly starts the real skill PR.
- New skill work stays rare and reviewable.

### 4. Go And Python Skill Registry Alignment

Problem:

The Python registry has 3 active PM-adjacent skills. The Go `internal/skills`
registry still carries historical 9-skill metadata for migration parity.

Acceptance:

- Decide whether Go should mirror the 3-skill active registry now.
- If yes, trim Go registry metadata and update tests.
- If no, document the exact migration cutoff and make the UI label clear.

### 5. Business PRD Workflow Mapping

Problem:

The workflow catalog still exposes `business-prd`, but the Python workflow maps
it to archived `landing_page_copy`.

Acceptance:

- Remap `business-prd` to an active PM skill or remove the workflow until a
  proper skill exists.
- Add tests that generation refuses workflows backed by archived skills.
- Update connector `used_for` metadata if the workflow changes.

## Next Layer

### Context Builder Production Wiring

`get_context_builder()` currently returns an empty connector registry in
production wiring. Tests can override it with real clients, but the default path
does not yet read Jira or Confluence.

Acceptance:

- Workspace connector settings can hydrate Jira and Confluence clients.
- The builder records source freshness from raw payload metadata.
- Failed connector reads create open questions instead of partial silent
  answers.

### Skill Candidate UI

The API exists, but reviewers need a console surface.

Acceptance:

- Settings or Learning page lists traces and candidates.
- Candidate detail shows source contract, tool plan, freshness contract,
  refusal rules, and eval seed cases.
- Approve/reject actions write audit events.

### Learning Loop Hygiene

The learning loop now has feedback, outcomes, proposals, replay, workflow
traces, and skill candidates. It needs guardrails so the surface stays
understandable.

Acceptance:

- One review queue for prompt proposals and skill candidates.
- Clear status vocabulary: draft, approved, rejected, applied.
- No duplicate candidate spam for the same workspace/workflow while a draft or
  approved candidate exists.

## Migration Follow-Through

The Go/templ migration is real, but not complete for every support path.

Still needed:

- Port learning and settings endpoints that the console depends on.
- Port context Ask only after runtime freshness contracts are settled.
- Keep Python as the parity oracle until the Go path has tests for the same
  behavior.
- Remove old React/Vite console only after templ has workflow-level parity.

## Review Rule

Do not treat docs as proof that a capability exists. For each capability, verify
the code path:

- API route
- model/migration
- service logic
- tests
- README or architecture doc

If one is missing, document it as outstanding, not shipped.

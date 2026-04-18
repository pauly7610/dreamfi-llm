# ADR-006: Hard-Gate Publishing

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

DreamFi publishes generated artifacts to external systems: Confluence (wiki pages, knowledge articles), Jira (field updates, comments, descriptions), and Dragonboat (initiative updates, status syncs). Once published, these artifacts are visible to stakeholders, customers, and downstream processes.

Publishing low-quality or stale artifacts has real consequences:
- A system prompt with deprecated feature references could cause an AI agent to hallucinate.
- A product description citing stale metrics could mislead customers.
- A support response with internal-only information could create compliance issues.

The platform needs an enforceable mechanism to prevent publishing artifacts that fail quality or freshness checks. Advisory warnings are insufficient because they rely on humans noticing and acting on them.

---

## Decision

**Block publish on failed eval, stale context, or skill/artifact mismatch.** These are hard gates: any single failure prevents the artifact from being published, regardless of other quality signals.

### Hard Gates

| Gate                    | Check                                                        | Failure Effect                    |
|-------------------------|--------------------------------------------------------------|-----------------------------------|
| **Eval gate**           | The generating skill's most recent round must have outcome = KEPT | Publish blocked, confidence = 0.0 |
| **Freshness gate**      | All cited source entities must have freshness_score >= 0.3   | Publish blocked, confidence = 0.0 |
| **Skill match gate**    | Artifact type must match the generating skill's declared output_type | Publish blocked, confidence = 0.0 |

### Gate Evaluation Order

Gates are evaluated in order: eval gate, then freshness gate, then skill match gate. Evaluation stops at the first failure. The first failing gate is logged as the blocking reason.

### Failure Logging

Every gate failure is recorded in `skill_failure_patterns` with:
- `pattern_type = 'publish_gate'`
- `description` = human-readable explanation of which gate failed and why
- `affected_rounds` = the round(s) involved
- `criterion_name` = the specific gate name (eval_gate, freshness_gate, skill_match_gate)

### Override Policy

There is no manual override for hard gates. If a gate fails, the only path to publishing is to fix the underlying issue:
- **Eval gate failure:** Iterate on the prompt until a round passes (outcome = KEPT).
- **Freshness gate failure:** Re-sync the stale source entities via the connector.
- **Skill match gate failure:** Generate the artifact using the correct skill.

### Per-Skill Freshness Thresholds

While the default freshness threshold is 0.3, individual skills can specify stricter thresholds:

| Skill                  | Freshness Threshold | Rationale                                |
|------------------------|--------------------|--------------------------------------------|
| agent_system_prompt    | 0.5                | Agent prompts must reflect current product state |
| support_agent          | 0.6                | Support responses must cite current procedures |
| meeting_summary        | 0.3 (default)      | Meeting context is inherently point-in-time |
| cold_email             | 0.5                | Product claims must be current |
| landing_page_copy      | 0.5                | Public-facing copy must be accurate |
| product_description    | 0.5                | Feature descriptions must match current state |
| newsletter_headline    | 0.3 (default)      | Headlines have fewer factual claims |
| resume_bullet          | 0.3 (default)      | Resume content is personal, not product-dependent |
| short_form_script      | 0.3 (default)      | Script content is creative, loosely sourced |

---

## Alternatives Considered

### Warn-only (soft gates)

**Pros:** More permissive. Artifacts can be published with warnings attached. Humans make the final call. Avoids blocking legitimate content over marginal quality issues.

**Cons:** Warnings are routinely ignored. In practice, warn-only gates degrade to no gates. The publishing pipeline becomes a rubber stamp. The cost of publishing a bad artifact (stale agent prompt, incorrect product description) outweighs the cost of blocking a marginally good one.

**Rejected because:** The consequences of publishing bad artifacts to customer-facing systems are severe enough to justify blocking. If a gate is too strict, the correct fix is to adjust the threshold, not to make the gate advisory.

### Soft gates with escalation

**Pros:** Gate failures trigger a review workflow. A designated reviewer can approve publishing despite the failure. Provides human oversight without fully blocking.

**Cons:** Review workflows create bottlenecks. Reviewers develop "approval fatigue" and rubber-stamp after the first few reviews. The escalation path becomes a backdoor for bypassing quality checks. Adds process complexity.

**Rejected because:** The autoresearch principle is explicit: automated quality checks should be the gate, not human judgment. Human judgment is channeled into defining the criteria (eval files) and setting thresholds, not into per-artifact approval.

### Confidence threshold only (no separate gates)

**Pros:** Simpler model. A single confidence score with a publish threshold handles all cases. No need for separate gate logic.

**Cons:** A high confidence score could mask a critical failure. For example: eval_score = 0.95, freshness = 0.8, citation = 1.0 but the artifact type does not match the skill. The confidence would be high, but the artifact is fundamentally wrong. Hard gates catch categorical failures that a numeric score can miss.

**Rejected because:** Hard gates address binary failure modes (pass/fail checks) that are distinct from the continuous quality signal provided by the confidence score. Both are needed.

---

## Tradeoffs

**Accepted tradeoffs:**
- **Legitimate content may be blocked.** A well-written artifact can be blocked if one of its sources is slightly stale. This creates friction.
- **No emergency override.** If a critical update needs to be published and a gate is failing, the only path is to fix the underlying issue. There is no "break glass" mechanism.
- **Gate failures may cascade.** A connector outage makes sources stale, which blocks all artifacts citing those sources, which blocks all publishing. One failure domain can freeze publishing.

**Mitigated by:**
- Freshness thresholds are set conservatively (0.3 default). Sources must be significantly stale to trigger the gate.
- Connector retry logic and circuit breakers (ADR-007) reduce the likelihood of prolonged staleness.
- If cascade blocking becomes a problem, per-skill freshness thresholds can be relaxed for less critical skills.
- The "no override" policy can be revisited if operational experience shows it is too rigid. See rollback plan.

---

## Consequences

1. The publishing pipeline is a strict gatekeeper. No artifact reaches Confluence, Jira, or Dragonboat without passing all three hard gates.
2. Teams must maintain connector health (freshness) and eval quality to keep the publishing pipeline flowing.
3. `skill_failure_patterns` accumulates a record of every blocked publish, enabling trend analysis. Persistent gate failures indicate systemic issues (e.g., a connector is consistently failing, or a skill's eval criteria are too strict).
4. The absence of manual overrides simplifies the publishing pipeline and eliminates a class of human-error risks.
5. Dashboards should prominently display gate status so teams can proactively address failures before they block publishing.

---

## Rollback Plan

1. **Relax to soft gates.** Change the publishing pipeline to log gate failures as warnings but proceed with publishing. This is a configuration change (`HARD_GATES_ENABLED=true/false`). Gate checks still run and are logged, but they do not block.
2. **Add manual override.** Introduce a `force_publish` flag that bypasses gates for a specific artifact. Requires an audit log entry with the overriding user and justification. This is a code change to the publishing pipeline.
3. **Adjust thresholds.** Per-skill freshness thresholds can be lowered if they are blocking too aggressively. This is a configuration change per skill in the skill registry.
4. **Disable individual gates.** Each gate can be independently enabled/disabled per skill. For example, disable the freshness gate for `meeting_summary` if meeting summaries rarely cite external sources.

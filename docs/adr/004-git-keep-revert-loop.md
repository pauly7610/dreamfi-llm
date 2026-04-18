# ADR-004: Git Keep/Revert Loop

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

The DreamFi eval system needs a disciplined method for iterating on prompt versions. Prompt engineering is notoriously difficult to reason about: changes that seem minor can cause unexpected regressions, and multiple simultaneous changes make it impossible to attribute improvements or regressions to specific modifications.

The autoresearch toolkit (inspired by Karpathy's approach to systematic improvement) establishes a pattern:

1. Make exactly one change per round.
2. Evaluate the change against the locked eval criteria.
3. If the aggregate score improves: keep the change.
4. If the aggregate score stays the same or regresses: revert the change.
5. Score improvement is the only signal that determines whether a change is kept.

This creates a monotonically improving (or stable) quality trajectory for each skill's prompt.

---

## Decision

**One change per round, keep improvements, revert regressions.** This is the core iteration loop for all prompt version development in DreamFi.

### Loop mechanics:

```
1. BASELINE: Record current prompt version's aggregate score (from most recent KEPT round).

2. CHANGE: Modify exactly one aspect of the prompt:
   - Add/remove/edit one instruction
   - Change one example
   - Adjust one structural element
   - Modify one constraint

3. EVALUATE: Run a full evaluation round:
   - Generate 10 outputs per test input
   - Score all outputs against locked binary criteria
   - Compute aggregate score

4. DECIDE:
   - If aggregate_score > baseline_score: KEEP
     - Mark round outcome = KEPT
     - Promote prompt version to ACTIVE
     - Check outputs for gold example eligibility
   - If aggregate_score <= baseline_score: REVERT
     - Mark round outcome = REVERTED
     - Prompt version status = REVERTED
     - Previous ACTIVE version remains in effect

5. REPEAT from step 2 with next change.
```

### What counts as "one change":

The change must be describable in a single sentence. The `prompt_versions.change_description` field enforces this.

Examples of valid single changes:
- "Added instruction to include compliance disclaimer when regulatory tags are present"
- "Replaced the third few-shot example with a higher-scoring gold example"
- "Changed maximum output length from 2000 to 2500 tokens"
- "Removed redundant instruction about formatting headers"

Examples of invalid multi-changes:
- "Rewrote the introduction and added two new examples" (two changes)
- "Changed tone instructions and adjusted length constraints" (two changes)
- "Complete prompt rewrite" (unbounded changes)

### Enforcement:

The system does not currently enforce single-change at the code level (comparing prompt diffs is unreliable). Enforcement is procedural: the `change_description` field is required and reviewed. If a round's improvement or regression cannot be attributed to the stated change, the round should be flagged for review.

---

## Alternatives Considered

### Multi-change rounds with ablation

**Pros:** Faster iteration. Make multiple changes, evaluate, then if improved, run ablation studies to determine which changes contributed.

**Cons:** Ablation is expensive (requires N additional rounds for N changes). Interaction effects between changes are difficult to detect. In practice, teams skip ablation and assume all changes contributed, which degrades signal quality.

**Rejected because:** The simplicity and reliability of one-change-per-round outweighs the speed advantage of multi-change rounds. Ablation is rarely done in practice and does not reliably identify interaction effects.

### A/B testing between versions

**Pros:** Statistical rigor. Run both versions simultaneously and compare with confidence intervals.

**Cons:** Requires much larger sample sizes than 10 outputs per input. Adds infrastructure complexity (routing, traffic splitting). Slower feedback loop (must wait for sufficient samples). Overkill for prompt iteration where the eval criteria are deterministic binary checks.

**Rejected because:** Binary eval criteria on 10 outputs per input provide sufficient signal for keep/revert decisions. A/B testing is appropriate for production traffic but not for the prompt development loop.

### Human review of outputs (no automated scoring)

**Pros:** Captures quality dimensions that automated criteria might miss. Human judgment is the ultimate quality measure.

**Cons:** Slow, expensive, inconsistent. Different reviewers will disagree. Cannot be run for every iteration. Creates a bottleneck that slows the entire improvement loop.

**Rejected because:** The autoresearch principle explicitly removes human judgment from the keep/revert decision to enable rapid, consistent iteration. Human input is channeled into defining eval criteria (which are then locked), not into per-round scoring.

### Time-based promotion (keep changes that survive N days)

**Pros:** Avoids the need for automated scoring. Let changes "soak" and catch regressions organically.

**Cons:** No mechanism for detecting regressions except user complaints. Extremely slow feedback loop. No objective quality measurement.

**Rejected because:** Time-based promotion is a proxy for "nobody complained," which is a weak quality signal. Automated scoring provides immediate, objective feedback.

---

## Tradeoffs

**Accepted tradeoffs:**
- **Slower iteration.** One change per round means improving a prompt from mediocre to excellent takes many rounds. A prompt with 10 issues cannot be fixed in one round.
- **Attribution is imperfect.** Even with single changes, the improvement might be due to stochastic variation in the 10 outputs rather than the prompt change. With only 10 samples, small score differences may not be statistically significant.
- **Prompt rewrites are awkward.** If a prompt needs a fundamental restructuring, it must be done as a sequence of small changes, each evaluated independently. This can be tedious.

**Mitigated by:**
- The loop is automated, so "many rounds" translates to compute time, not human time.
- For borderline cases (score improvement < 2%), the system can be configured to require improvement > a minimum threshold to keep.
- Fundamental restructuring can be done by creating a new eval file version (resetting the baseline) when the prompt needs a clean start.

---

## Consequences

1. All prompt development follows the same loop. No skill is exempt.
2. The `evaluation_rounds` table creates a complete audit trail of every change attempted and its outcome.
3. Prompt quality can only improve or remain stable over time (assuming locked eval files). It never degresses and stays regressed.
4. The `change_description` field on `prompt_versions` is required. It serves as documentation for why each change was made.
5. Tooling should support rapid round execution: submit a change, wait for scoring, see keep/revert result. The human's role is deciding what to change next, not evaluating whether the change was good.
6. `skill_failure_patterns` can correlate specific change descriptions with regressions, building institutional knowledge about what types of changes tend to fail.

---

## Rollback Plan

1. The keep/revert loop is implemented in the eval engine service. Disabling it means allowing all prompt version changes to be promoted regardless of score. This is a configuration flag (`ENABLE_KEEP_REVERT_LOOP=true/false`).
2. If disabled, prompt versions are promoted based on the original alternative (human review or time-based). This is a degradation, not an improvement.
3. Re-enabling the loop does not require re-evaluating historical rounds. The system picks up from the current ACTIVE prompt version and resumes the loop.
4. If the one-change-per-round constraint is too slow, it can be relaxed to "N changes per round" with the understanding that attribution quality degrades. This is a policy change, not a code change.

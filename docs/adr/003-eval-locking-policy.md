# ADR-003: Evaluation Locking Policy

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

The DreamFi eval system follows the autoresearch toolkit principles: locked binary evals, 10 outputs per input, one change per round, keep improvements, revert regressions. A critical requirement of this approach is that evaluation criteria and scoring logic must be immutable during and after an evaluation round.

Without locking, there is a risk that eval criteria are modified between rounds, making cross-round score comparisons meaningless. If round N scores 0.85 and round N+1 scores 0.87, that comparison is only valid if both rounds used identical evaluation criteria and scoring logic.

The autoresearch principle here is explicit: the eval file is the ground truth. If you want to change what "good" means, you create a new eval file version. You never modify the one that produced existing scores.

---

## Decision

**Eval files and scoring runners are immutable after lock.** Once an evaluation round begins with a specific eval file version, that version is permanently locked.

### What is locked:
- **Eval criteria definitions:** The set of binary criteria (pass/fail checks) in the `evaluation_criteria_catalog` for a given eval file version.
- **Scoring runner logic:** The code that applies criteria to outputs and computes scores. Versioned and pinned per eval file version.
- **Criterion implementations:** The specific logic of each binary check (e.g., "contains compliance language" is locked to a specific regex or LLM prompt).

### How locking works:
1. An eval file version is created in `evaluation_criteria_catalog` with status = DRAFT.
2. When a round is started, the eval file version transitions to LOCKED. This is irreversible.
3. The locked eval file version is recorded in `evaluation_rounds.eval_file_version`.
4. Any attempt to modify a LOCKED eval file version is rejected by the application layer.
5. To change evaluation criteria, a new eval file version must be created. The first round using the new version establishes a new baseline (no comparison to rounds using the old version).

### Scoring runner versioning:
- Scoring runners are stored as versioned modules alongside eval files.
- Each eval file version references a specific scoring runner version.
- Runner code is checksummed at lock time. Runtime verification ensures the runner matches the expected checksum.

---

## Alternatives Considered

### Mutable eval files with change tracking

**Pros:** More flexible. Teams can iterate on criteria without creating new versions. Change history provides audit trail.

**Cons:** Cross-round comparisons become unreliable. A score improvement might be caused by relaxed criteria rather than better prompts. The autoresearch principle of "score improvement as only promotion signal" breaks down if the scoring itself changes. Change tracking adds complexity without solving the fundamental comparison problem.

**Rejected because:** The entire eval loop depends on score comparability across rounds. Mutable criteria undermine the keep/revert decision.

### Lock only during active rounds, unlock between rounds

**Pros:** Allows iteration on criteria between rounds while maintaining consistency within a round.

**Cons:** Still breaks cross-round comparison. If criteria change between round N and round N+1, the keep/revert decision for round N+1 is comparing against a baseline scored under different rules. Partial locking creates a false sense of consistency.

**Rejected because:** The keep/revert decision inherently compares across rounds. Locking only within rounds does not provide the guarantee needed.

### No locking, rely on discipline

**Pros:** Zero implementation cost. Trust the team to not modify active eval files.

**Cons:** In practice, this fails. Someone will "fix a typo" in a criterion, invalidating historical scores. There is no enforcement mechanism. Audit becomes impossible.

**Rejected because:** Automated enforcement is more reliable than manual discipline, especially as the number of skills and team members grows.

---

## Tradeoffs

**Accepted tradeoffs:**
- **Limits iteration speed on criteria.** Changing what "good" means requires creating a new eval file version, which resets the baseline. You cannot incrementally improve criteria and compare to historical scores.
- **Version proliferation.** Over time, many eval file versions accumulate. Storage is cheap, but navigating version history requires tooling.
- **Cold-start on new versions.** When a new eval file version is created, the first round has no baseline to compare against. It establishes the new baseline, which means one round is "wasted" on baselining.

**Mitigated by:**
- Criteria changes should be infrequent. The eval file represents the definition of quality, which should be stable.
- A UI for browsing eval file version history makes navigation manageable.
- The baseline round is not wasted -- it produces outputs that may qualify as gold examples.

---

## Consequences

1. `evaluation_criteria_catalog` gains a `status` column with values DRAFT and LOCKED. Transition from DRAFT to LOCKED is one-way.
2. `evaluation_rounds` records the `eval_file_version` used, providing full provenance.
3. Cross-round score comparisons are only valid within the same eval file version. The system enforces this: keep/revert decisions only compare rounds with matching eval file versions.
4. The scoring runner is treated as code-under-test and version-pinned. Changes to scoring logic follow the same locking protocol.
5. Teams must plan criteria changes deliberately. Quick fixes to "just tweak a criterion" are intentionally prevented.
6. Historical eval results remain interpretable indefinitely because the criteria that produced them are preserved.

---

## Rollback Plan

1. If locking proves too rigid, the LOCKED status can be extended with an ARCHIVED status that allows creating a new version pre-populated with the archived version's criteria (copy-on-write). This does not modify the locked version.
2. If the team needs to retroactively fix a criterion bug, a new eval file version is created with the fix, and affected rounds can be re-scored under the new version. Historical scores under the old version are preserved for audit.
3. The locking enforcement is in the application layer. Removing it is a code change, not a schema change. However, removing locking without migrating to an alternative consistency mechanism is strongly discouraged.

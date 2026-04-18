# Tier 1 Skill Contracts — Source of Truth

**Last Updated:** April 18, 2026  
**Scope:** Tier 1 skills only (meeting_summary, agent_system_prompt, support_agent)  
**Purpose:** Single source of truth to prevent drift between locked evals, schema seed data, and code.

---

## meeting_summary

### Contract ID

`skill_meeting-summary_v1`

### File Location

`evals/meeting-summary.md` (locked)

### Tier

Tier 1

### Overview

Takes operational context (Jira issues, Confluence pages) and generates a meeting-style summary with explicit structure.

### Sections

1. **Decisions** — Listing explicit decision points made or identified
2. **Action Items** — Each with owner (required) and deadline (required)
3. **Open Questions** — Written as actual questions, not statements

### Criteria (5 total)

| ID  | Criterion        | Hard Gate | Pass Rule                                |
| --- | ---------------- | --------- | ---------------------------------------- |
| 1   | structure        | YES       | Output has all 3 sections with labels    |
| 2   | completeness     | NO        | Each section has content (0 = soft fail) |
| 3   | action_owners    | YES       | Every action item has owner name         |
| 4   | action_deadlines | YES       | Every action item has deadline           |
| 5   | word_count       | YES       | Output < 300 words                       |

### Constraints

- Max 300 words total
- Every action item MUST have owner + deadline
- Sections must be explicit (not inferred)
- Decisions explicitly labeled as such
- Questions written as questions (not statements)

### Test Inputs

- Input 1: 3 Jira issues + 2 Confluence pages → meeting summary
- Input 2: 5 Jira issues (no confluence) → meeting summary
- Input 3: 1 Confluence page + context → meeting summary

### Eval File Hash (Immutability)

```
SHA256: [computed from evals/meeting-summary.md - will be set when file is locked]
```

### Schema Seed Mapping

| Schema Field               | Value                    |
| -------------------------- | ------------------------ |
| id                         | (UUID)                   |
| skill_name                 | meeting_summary          |
| tier                       | 1                        |
| display_name               | Meeting Summary          |
| eval_file_path             | evals/meeting-summary.md |
| criteria_count             | 5                        |
| hard_gate_criteria_ids     | [1, 3, 4, 5]             |
| eligible_source_types_json | ["jira", "confluence"]   |

---

## agent_system_prompt

### Contract ID

`skill_agent-system-prompt_v1`

### File Location

`evals/agent-system-prompt.md` (locked)

### Tier

Tier 1

### Overview

Takes user intent and generates a system prompt for an autonomous agent, explaining role, constraints, and decision-making.

### Criteria (5 total)

| ID  | Criterion        | Hard Gate | Pass Rule                                        |
| --- | ---------------- | --------- | ------------------------------------------------ |
| 1   | intent_clarity   | YES       | Prompt explicitly states intended agent behavior |
| 2   | no_hallucination | YES       | Prompt includes guardrails against invention     |
| 3   | next_action      | YES       | Prompt specifies how agent decides next action   |
| 4   | conciseness      | YES       | Prompt < 80 words                                |
| 5   | refusal_criteria | NO        | Prompt describes when to refuse (soft)           |

### Constraints

- Max 80 words
- Must include explicit guardrails
- Must specify next-action logic
- Must be usable directly as system prompt

### Test Inputs

- Input 1: Agent intent (customer support) → system prompt
- Input 2: Agent intent (research assistant) → system prompt
- Input 3: Agent intent (code reviewer) → system prompt

### Schema Seed Mapping

| Schema Field               | Value                        |
| -------------------------- | ---------------------------- |
| skill_name                 | agent_system_prompt          |
| tier                       | 1                            |
| eval_file_path             | evals/agent-system-prompt.md |
| criteria_count             | 5                            |
| hard_gate_criteria_ids     | [1, 2, 3, 4]                 |
| eligible_source_types_json | ["agent_context"]            |

---

## support_agent

### Contract ID

`skill_support-agent_v1`

### File Location

`evals/support-agent.md` (locked)

### Tier

Tier 1

### Overview

Takes customer message + KB context and generates a support response, escalating when needed.

### Criteria (5 total)

| ID  | Criterion         | Hard Gate | Pass Rule                                              |
| --- | ----------------- | --------- | ------------------------------------------------------ |
| 1   | resolve           | YES       | Response attempts resolution (not just acknowledgment) |
| 2   | kb_only           | YES       | Response uses only provided KB, no invention           |
| 3   | conversation_flow | YES       | Max 3 messages before escalation recommendation        |
| 4   | escalation        | NO        | Clear escalation path when needed (soft)               |
| 5   | conciseness       | YES       | Response < 120 words                                   |

### Constraints

- Max 120 words
- Max 3-message conversation before escalation
- Only use provided KB
- Must indicate resolution status

### Test Inputs

- Input 1: Customer question + KB → support response
- Input 2: Complex question + KB → support response
- Input 3: Escalation-worthy + KB → escalation

### Schema Seed Mapping

| Schema Field               | Value                  |
| -------------------------- | ---------------------- |
| skill_name                 | support_agent          |
| tier                       | 1                      |
| eval_file_path             | evals/support-agent.md |
| criteria_count             | 5                      |
| hard_gate_criteria_ids     | [1, 2, 3, 5]           |
| eligible_source_types_json | ["kb_article"]         |

---

## Enforcement Rules

### Rule 1: Path Consistency

- Schema skill entry must have `eval_file_path` = one of:
  - `evals/meeting-summary.md`
  - `evals/agent-system-prompt.md`
  - `evals/support-agent.md`
- Paths must use `.md`, not `.yaml`

### Rule 2: Criteria Count Consistency

- Schema `criteria_count` must match number of criteria in locked eval file

### Rule 3: Hard Gate Consistency

- Schema `hard_gate_criteria_ids` must match which criteria are hard gates in eval file

### Rule 4: Immutability

- Locked eval file has SHA256 hash
- Schema seed includes hash for validation
- Any change to eval file requires hash update + contract version bump

### Rule 5: CI Gate

- CI/CD test `test_tier1_contract_alignment` must PASS before any merge
- Test validates:
  - Every Tier 1 skill in schema has corresponding locked eval file
  - Every locked eval file in evals/ has corresponding schema entry
  - Criteria counts match
  - Hard gates match
  - File hashes match
  - No drift possible

---

## Testing Alignment

### Pre-implementation Test

```python
# tests/unit/contracts/test_tier1_alignment.py
def test_every_tier1_skill_has_locked_eval():
    # Query schema for tier=1 skills
    # For each: verify corresponding evals/*.md file exists
    # Fail if missing

def test_every_locked_eval_in_schema():
    # List all evals/*.md files
    # For each: verify it's referenced in schema
    # Fail if missing

def test_criteria_count_matches():
    # Load schema skill criteria_count
    # Load locked eval file criteria count
    # Assert equal, fail if not

def test_hard_gates_match():
    # Load schema hard_gate_criteria_ids
    # Load locked eval file criteria marked as hard_gate
    # Assert same IDs, fail if not

def test_eval_file_hashes_match():
    # Compute SHA256 of evals/*.md
    # Compare to schema seed hash
    # Fail if mismatch
```

### Acceptance Criteria for This Document

- ✅ All 3 Tier 1 contracts fully specified
- ✅ Schema mapping clear for each
- ✅ Test inputs defined
- ✅ All criteria defined with hard-gate status
- ✅ Constraints clear
- ✅ Enforcement rules explicit
- ✅ Immutability strategy documented

---

## Next Steps

1. Update schema seed data to match this document exactly
2. Verify all locked eval files match this document
3. Create tests that validate this document
4. Run CI gate — must pass before any code changes

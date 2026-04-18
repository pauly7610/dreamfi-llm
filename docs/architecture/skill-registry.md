# Skill Registry

**Status:** Living document
**Last updated:** 2026-04-17

---

## 1. Overview

The skill registry is the central catalog of all generative skills in the DreamFi platform. Each skill defines a specific document generation capability with its own prompt versions, evaluation criteria, test inputs, gold examples, and failure patterns. Skills are organized into families and tiers that determine rollout order and evaluation rigor.

All skills follow the autoresearch evaluation loop: locked binary evals, 10 outputs per input, one change per round, keep improvements, revert regressions, score improvement as the only promotion signal.

---

## 2. Skill Families and Tiers

### Tier 1 -- Core Operations (Week 1-2)

These skills support daily product and support operations. They are rolled out first because they have the most immediate business impact and the most available training data.

| Skill                  | Family              | Output Type            |
|------------------------|---------------------|------------------------|
| agent_system_prompt    | Agent Configuration | System prompt document |
| support_agent          | Agent Configuration | Support response       |
| meeting_summary        | Operations          | Meeting summary doc    |
| cold_email             | Outreach            | Email body             |

### Tier 2 -- Content Generation (Week 3)

These skills produce marketing and product content. They depend on Phase 1 knowledge being populated and Phase 2 eval infrastructure being proven on Tier 1.

| Skill                  | Family              | Output Type            |
|------------------------|---------------------|------------------------|
| landing_page_copy      | Marketing Copy      | Landing page section   |
| product_description    | Product Content     | Product description    |
| newsletter_headline    | Marketing Copy      | Headline text          |

### Tier 3 -- Specialized Content (Week 4)

These skills cover niche use cases. They are rolled out last because they have fewer test inputs and more subjective evaluation criteria.

| Skill                  | Family              | Output Type            |
|------------------------|---------------------|------------------------|
| resume_bullet          | Professional Copy   | Resume bullet point    |
| short_form_script      | Video Content       | Short-form video script|

---

## 3. Prompt Version Management

Each skill maintains a linear history of prompt versions in the `prompt_versions` table.

### Version Lifecycle

```
DRAFT -> TESTING -> ACTIVE -> SUPERSEDED
                      |
                      +-> REVERTED (if next version regresses)
```

- **DRAFT:** Prompt is being edited. Not yet evaluated.
- **TESTING:** Prompt is in an active evaluation round. 10 outputs generated per test input.
- **ACTIVE:** Prompt passed evaluation and is the current production version.
- **SUPERSEDED:** A newer version has been promoted to ACTIVE.
- **REVERTED:** The version was promoted but caused regression in a subsequent round; rolled back.

### Version Rules

1. Only one version can be ACTIVE per skill at any time.
2. A new version can only enter TESTING if the current ACTIVE version exists (bootstrap exception for first version).
3. Promotion from TESTING to ACTIVE requires score improvement over the current ACTIVE version.
4. No manual override of promotion. Score improvement is the only path.
5. Version history is append-only. No deletion of prompt versions.

### Storage Schema

```sql
prompt_versions (
  id              UUID PRIMARY KEY,
  skill_id        UUID REFERENCES skill_registry(id),
  version_number  INTEGER NOT NULL,
  prompt_text     TEXT NOT NULL,
  status          TEXT CHECK (status IN ('DRAFT','TESTING','ACTIVE','SUPERSEDED','REVERTED')),
  created_at      TIMESTAMP DEFAULT now(),
  activated_at    TIMESTAMP,
  superseded_at   TIMESTAMP,
  change_description TEXT -- what changed from previous version
)
```

---

## 4. Evaluation Round Structure

Each evaluation round tests one prompt version change against the current baseline.

### Round Flow

1. **Load locked eval file.** The eval file is immutable after lock. It defines binary criteria (pass/fail).
2. **Load test inputs.** Pull from `test_input_registry` for this skill.
3. **Generate outputs.** Produce 10 candidate outputs per test input using the candidate prompt version.
4. **Score outputs.** Each output is evaluated against every criterion in the locked eval file. Each criterion returns binary pass/fail.
5. **Compute round score.** Fraction of (output, criterion) pairs that pass.
6. **Compare to baseline.** If round score > previous round score: keep. If <=: revert.
7. **Log results.** Write to `evaluation_rounds` and `evaluation_outputs`.

### Constraints

- **One change per round.** Only one aspect of the prompt is modified between consecutive rounds. This isolates the cause of any score change.
- **10 outputs per input.** This provides statistical coverage without excessive compute cost.
- **Locked eval files.** Once an eval file is locked for a round, it cannot be modified. New criteria require a new eval file version.

### Storage Schema

```sql
evaluation_rounds (
  id                UUID PRIMARY KEY,
  skill_id          UUID REFERENCES skill_registry(id),
  prompt_version_id UUID REFERENCES prompt_versions(id),
  eval_file_version TEXT NOT NULL,
  round_number      INTEGER NOT NULL,
  aggregate_score   FLOAT NOT NULL,  -- 0.0 to 1.0
  baseline_score    FLOAT,           -- score of previous round
  outcome           TEXT CHECK (outcome IN ('KEPT','REVERTED')),
  started_at        TIMESTAMP DEFAULT now(),
  completed_at      TIMESTAMP
)

evaluation_outputs (
  id                UUID PRIMARY KEY,
  round_id          UUID REFERENCES evaluation_rounds(id),
  test_input_id     UUID REFERENCES test_input_registry(id),
  output_index      INTEGER CHECK (output_index BETWEEN 1 AND 10),
  output_text       TEXT NOT NULL,
  criteria_results  JSONB NOT NULL,  -- {"criterion_name": true/false, ...}
  all_passed        BOOLEAN NOT NULL,
  score             FLOAT NOT NULL,  -- fraction of criteria passed
  created_at        TIMESTAMP DEFAULT now()
)
```

---

## 5. Gold Example Promotion Logic

Gold examples are the highest-quality outputs produced by the system. They serve as few-shot examples in prompts and as benchmarks for future evaluation.

### Promotion Criteria

An output is promoted to gold example status only when ALL of the following are true:

1. **All criteria passed.** Every binary criterion in the locked eval file returned true for this output.
2. **Score >= 90%.** The output's score (fraction of criteria passed) is at least 0.90. In practice, since all criteria must pass, this is 1.0 -- but the threshold allows for future weighted criteria.
3. **Non-regressing round.** The round that produced this output must have outcome = KEPT (i.e., the round improved or matched the baseline, it was not reverted).

### Promotion Process

1. After a round completes with outcome = KEPT, scan all outputs from that round.
2. Filter to outputs where `all_passed = true` and `score >= 0.90`.
3. Insert qualifying outputs into `gold_example_registry` with full provenance (round_id, prompt_version_id, test_input_id).
4. Gold examples are immutable once written. They are never edited or deleted.

### Storage Schema

```sql
gold_example_registry (
  id                UUID PRIMARY KEY,
  skill_id          UUID REFERENCES skill_registry(id),
  round_id          UUID REFERENCES evaluation_rounds(id),
  prompt_version_id UUID REFERENCES prompt_versions(id),
  test_input_id     UUID REFERENCES test_input_registry(id),
  output_text       TEXT NOT NULL,
  criteria_results  JSONB NOT NULL,
  score             FLOAT NOT NULL,
  promoted_at       TIMESTAMP DEFAULT now()
)
```

---

## 6. Failure Pattern Tracking

The `skill_failure_patterns` table records systematic failure modes detected across evaluation rounds. This enables targeted prompt iteration.

### What Gets Tracked

- **Criterion failures:** When a specific criterion fails across multiple outputs in a round, a pattern is logged.
- **Input-specific failures:** When a specific test input consistently produces failing outputs across rounds.
- **Regression patterns:** When a prompt change causes regression, the change description and failing criteria are correlated.
- **Publish gate failures:** When an artifact fails a hard gate (freshness, eval, skill mismatch), the failure is logged with context.

### Storage Schema

```sql
skill_failure_patterns (
  id              UUID PRIMARY KEY,
  skill_id        UUID REFERENCES skill_registry(id),
  pattern_type    TEXT CHECK (pattern_type IN ('criterion_failure','input_failure','regression','publish_gate')),
  description     TEXT NOT NULL,
  affected_rounds JSONB,     -- array of round_ids
  affected_inputs JSONB,     -- array of test_input_ids
  criterion_name  TEXT,
  frequency       INTEGER DEFAULT 1,
  first_seen_at   TIMESTAMP DEFAULT now(),
  last_seen_at    TIMESTAMP DEFAULT now(),
  resolved        BOOLEAN DEFAULT false,
  resolved_at     TIMESTAMP
)
```

---

## 7. Per-Skill Specifications

### 7.1 agent_system_prompt

**Tier:** 1
**Family:** Agent Configuration
**Output type:** System prompt document for AI agents
**Rollout:** Week 1-2

**Description:** Generates system prompts for AI agents deployed across DreamFi products. Consumes product knowledge, feature specs, compliance rules, and tone guidelines from the knowledge hub.

**Hard-gate rules:**
- Must include compliance disclaimers if source entities are tagged with regulatory labels.
- Must not reference deprecated features (checked against entity_status = DEPRECATED).
- Must include version identifier in output metadata.
- Freshness gate: all cited product entities must have freshness_score >= 0.5.

**Eval criteria (binary):**
- Contains required compliance language (if applicable)
- Does not reference deprecated features
- Follows structural template (sections present)
- Tone matches brand guidelines
- Length within bounds (500-3000 tokens)
- No hallucinated feature names (all mentioned features exist in core_entities)

---

### 7.2 support_agent

**Tier:** 1
**Family:** Agent Configuration
**Output type:** Support response template
**Rollout:** Week 1-2

**Description:** Generates support response templates for customer-facing agents. Draws from FAQ entries, product docs, known issues, and resolution procedures in the knowledge hub.

**Hard-gate rules:**
- Must not include internal-only information (entities tagged internal_only = true).
- Must reference at least one citation from knowledge hub.
- Freshness gate: cited knowledge articles must have freshness_score >= 0.6.

**Eval criteria (binary):**
- Does not leak internal information
- Contains at least one verifiable citation
- Addresses the stated customer problem
- Uses approved tone (empathetic, professional)
- Includes next steps or resolution path
- Length within bounds (100-800 tokens)

---

### 7.3 meeting_summary

**Tier:** 1
**Family:** Operations
**Output type:** Meeting summary document
**Rollout:** Week 1-2

**Description:** Generates structured meeting summaries from transcript or notes input. Links discussed topics to canonical entities (features, initiatives, issues).

**Hard-gate rules:**
- Must link at least one discussed topic to a canonical entity if entity names are detected in input.
- Must not attribute statements to individuals not present in the input.

**Eval criteria (binary):**
- Contains action items section
- Contains decisions section
- Contains attendees list
- Links topics to canonical entities where applicable
- Does not fabricate attendee names
- Captures key decisions accurately (spot-checked against input)

---

### 7.4 cold_email

**Tier:** 1
**Family:** Outreach
**Output type:** Email body
**Rollout:** Week 1-2

**Description:** Generates cold outreach emails for sales and partnerships. Uses prospect context, product positioning, and value propositions from the knowledge hub.

**Hard-gate rules:**
- Must comply with CAN-SPAM requirements (no false headers, must identify as commercial).
- Must not make unsubstantiated claims about product capabilities.
- Freshness gate: cited product capabilities must have freshness_score >= 0.5.

**Eval criteria (binary):**
- Contains personalization element (references prospect context)
- Has clear call to action
- Under 200 words
- No unsubstantiated claims (all claims traceable to citations)
- Professional tone
- CAN-SPAM compliant structure

---

### 7.5 landing_page_copy

**Tier:** 2
**Family:** Marketing Copy
**Output type:** Landing page section
**Rollout:** Week 3

**Description:** Generates copy for landing page sections (hero, features, social proof, CTA). Follows brand style guide constraints and character limits.

**Hard-gate rules:**
- Must pass character limit checks per section type (hero headline <= 60 chars, subhead <= 120 chars, body <= 300 chars).
- Must not use competitor names.
- Style constraint: must match brand voice profile.

**Eval criteria (binary):**
- Within character limits for section type
- No competitor mentions
- Matches brand voice (checked against voice profile keywords)
- Contains value proposition
- Grammatically correct
- Has clear CTA (for CTA sections)

---

### 7.6 product_description

**Tier:** 2
**Family:** Product Content
**Output type:** Product description
**Rollout:** Week 3

**Description:** Generates product descriptions for features, modules, and integrations. Sources from technical specs, user-facing docs, and feature entity records.

**Hard-gate rules:**
- All mentioned features must exist in core_entities.
- Must not describe unreleased features unless entity_status = BETA.
- Freshness gate: source feature entities must have freshness_score >= 0.5.

**Eval criteria (binary):**
- All features mentioned exist in canonical DB
- Accurate status representation (no claiming GA for beta features)
- Follows description template structure
- Appropriate technical depth for audience
- Length within bounds (100-500 tokens)
- No hallucinated integrations or capabilities

---

### 7.7 newsletter_headline

**Tier:** 2
**Family:** Marketing Copy
**Output type:** Headline text
**Rollout:** Week 3

**Description:** Generates newsletter headlines and subject lines. Optimized for open rates while maintaining brand consistency.

**Hard-gate rules:**
- Character limit: <= 80 characters.
- Must not use spam trigger words (checked against blocklist).
- Must not make unverifiable claims.

**Eval criteria (binary):**
- Under 80 characters
- No spam trigger words
- Creates curiosity or urgency
- Relevant to newsletter content (matches input topic)
- Grammatically correct
- Brand-consistent tone

---

### 7.8 resume_bullet

**Tier:** 3
**Family:** Professional Copy
**Output type:** Resume bullet point
**Rollout:** Week 4

**Description:** Generates achievement-oriented resume bullet points. Uses the XYZ formula (accomplished X by doing Y, resulting in Z).

**Hard-gate rules:**
- Must follow XYZ structure.
- Must not fabricate metrics (quantitative claims must trace to input data).

**Eval criteria (binary):**
- Follows XYZ formula structure
- Contains quantitative result (if input provides data)
- Action verb at start
- Under 30 words
- No fabricated metrics
- Specific and concrete (not generic)

---

### 7.9 short_form_script

**Tier:** 3
**Family:** Video Content
**Output type:** Short-form video script
**Rollout:** Week 4

**Description:** Generates scripts for short-form video content (30-90 seconds). Includes hook, body, and CTA structure. Sources from product knowledge and trending topic context.

**Hard-gate rules:**
- Must be within 30-90 second spoken duration (estimated at 150 words/minute).
- Must include hook in first 3 seconds of script.
- Must not make unsubstantiated product claims.

**Eval criteria (binary):**
- Within word count for 30-90 second duration (75-225 words)
- Hook present in first sentence
- Has clear CTA
- Conversational tone appropriate for video
- No unsubstantiated claims
- Follows hook-body-CTA structure

---

## 8. Rollout Schedule

| Week    | Tier | Skills Activated                                                  | Prerequisite                    |
|---------|------|-------------------------------------------------------------------|---------------------------------|
| Week 1-2| 1    | agent_system_prompt, support_agent, meeting_summary, cold_email   | Phase 1 knowledge hub populated |
| Week 3  | 2    | landing_page_copy, product_description, newsletter_headline       | Tier 1 eval infra proven        |
| Week 4  | 3    | resume_bullet, short_form_script                                  | Tier 2 stable                   |

Each tier activation requires:
1. Test inputs populated in `test_input_registry` for all skills in the tier.
2. Eval criteria defined and locked in `evaluation_criteria_catalog`.
3. At least one successful evaluation round with outcome = KEPT.
4. No unresolved Tier N-1 failure patterns of type `regression`.

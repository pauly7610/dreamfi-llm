# DreamFi System Architecture Overview

**Status:** Living document
**Last updated:** 2026-04-17

---

## 1. Platform Summary

DreamFi's product operations platform is a five-phase system that ingests data from eleven external connectors, normalizes it into a canonical Postgres schema, generates skill-based outputs through locked evaluation loops, and publishes trusted artifacts to downstream systems. Every generated artifact carries a composite confidence score derived from evaluation results, source freshness, citation coverage, and hard-gate status.

---

## 2. Five Phases

### Phase 1 -- Product Knowledge Hub + Skill Registry

The foundation layer. Postgres stores all canonical entities, relationships, citations, and skill metadata. Connectors ingest raw data from external systems, normalize it into the canonical schema, and attach freshness metadata. The skill registry tracks prompt versions, evaluation criteria, test inputs, and gold examples. A hybrid search layer (full-text + embeddings) provides retrieval for downstream generators.

### Phase 2 -- Criteria-Driven Generators

Skill-based document generation. Each skill (e.g., agent_system_prompt, support_agent, cold_email) takes structured context from Phase 1 and produces 10 candidate outputs per input. Outputs are scored against locked binary evaluation criteria. Only rounds that improve aggregate scores are kept; regressions are reverted. Promoted outputs become gold examples.

### Phase 3 -- Dragonboat + Jira Trust-Based Reporting

Taxonomy alignment and field hygiene for project management systems. Maps Jira and Dragonboat fields to canonical schema, enforces naming conventions, detects drift, and publishes hygiene reports. Trust scores reflect how well external records match canonical state.

### Phase 4 -- Product Performance + Event-Based Reporting

Metrics aggregation from PostHog, GA, Metabase, Klaviyo, and domain-specific systems (NetXD, Sardine, Socure). Builds dashboards, periodic snapshots, and event-triggered reports. Freshness of source metrics feeds into confidence scoring for any artifact that cites them.

### Phase 5 -- UI Project Support

Copy generation under style constraints. Landing page copy, newsletter headlines, and short-form scripts are generated through the same eval loop as Phase 2 but with additional UI-specific hard gates: character limits, brand voice compliance, and export-readiness checks.

---

## 3. Architecture Diagram

```
                          EXTERNAL SYSTEMS
  +--------+----------+-----------+----------+---------+----------+
  | Jira   |Dragonboat| Lucidchart|Confluence| Metabase| PostHog  |
  +--------+----------+-----------+----------+---------+----------+
  | GA     | Klaviyo  | NetXD     | Sardine  | Socure  |
  +--------+----------+-----------+----------+---------+

           |              |              |              |
           v              v              v              v
  +-------------------------------------------------------------------+
  |                   CONNECTOR INGESTION LAYER                       |
  |  - Auth (OAuth2 / API Key / Service Account)                      |
  |  - Sync (webhook / polling / batch)                               |
  |  - Raw payload -> Object Store (S3-compatible)                    |
  |  - Normalize -> Canonical DB (Postgres)                           |
  |  - Attach freshness metadata (last_synced_at, freshness_score)    |
  +-------------------------------------------------------------------+
           |                                    |
           v                                    v
  +---------------------+         +---------------------------+
  |   RAW OBJECT STORE  |         |      CANONICAL DB         |
  |   (S3-compatible)   |         |      (Postgres)           |
  |                     |         |                           |
  |  - Full API payload |         |  - core_entities          |
  |  - Webhook bodies   |         |  - relationships          |
  |  - Attachment blobs  |         |  - citations              |
  |                     |         |  - skill_registry         |
  |                     |         |  - prompt_versions        |
  |                     |         |  - evaluation_criteria_    |
  |                     |         |    catalog                |
  |                     |         |  - test_input_registry    |
  |                     |         |  - evaluation_rounds      |
  |                     |         |  - evaluation_outputs     |
  |                     |         |  - gold_example_registry  |
  |                     |         |  - skill_failure_patterns |
  +---------------------+         +---------------------------+
                                           |
                                           v
                                 +-------------------+
                                 |   SEARCH LAYER    |
                                 | Full-text (tsvec) |
                                 | + Embeddings (pgv)|
                                 | Hybrid ranking    |
                                 +-------------------+
                                           |
                                           v
  +-------------------------------------------------------------------+
  |                     EVAL ENGINE (per skill)                       |
  |                                                                   |
  |  1. Load locked eval file + scoring runner                        |
  |  2. Pull test inputs from test_input_registry                     |
  |  3. Generate 10 outputs per input                                 |
  |  4. Score each output against binary criteria                     |
  |  5. Compare round score to previous round                        |
  |  6. KEEP if improved, REVERT if regressed                        |
  |  7. Outputs passing all criteria + >=90% -> gold_example_registry |
  +-------------------------------------------------------------------+
                                           |
                                           v
  +-------------------------------------------------------------------+
  |                    CONFIDENCE SCORING                              |
  |                                                                   |
  |  confidence = w1*eval_score + w2*freshness + w3*citation_coverage  |
  |               - hard_gate_penalty                                  |
  |                                                                   |
  |  Hard gates (any failure -> confidence = 0, publish blocked):      |
  |    - eval_pass = false                                             |
  |    - freshness < threshold                                         |
  |    - skill/artifact type mismatch                                  |
  +-------------------------------------------------------------------+
                                           |
                                           v
  +-------------------------------------------------------------------+
  |                    PUBLISHING LAYER                                |
  |                                                                   |
  |  1. Check hard gates (eval, freshness, skill match)               |
  |  2. If any gate fails -> block publish, log reason                |
  |  3. If all gates pass -> publish to target system                 |
  |     - Confluence (wiki pages, knowledge articles)                 |
  |     - Jira (field updates, comments, descriptions)                |
  |     - Dragonboat (initiative updates, status syncs)               |
  +-------------------------------------------------------------------+
```

---

## 4. Data Flow

### 4.1 Ingestion

1. Connector authenticates with external system.
2. Raw payload is stored in object store with metadata envelope (source_system, source_object_id, sync_timestamp).
3. Normalizer extracts fields, maps to canonical schema tables (core_entities, relationships, citations).
4. Freshness metadata is computed and attached: `last_synced_at`, `freshness_score` (0.0-1.0), `eligible_skill_families_json`.

### 4.2 Search and Retrieval

1. Canonical entities are indexed in Postgres full-text search (tsvector/tsquery).
2. Entity descriptions and content fields are embedded via a text embedding model and stored in pgvector.
3. Queries run hybrid: keyword match + vector similarity, combined with reciprocal rank fusion.
4. Results carry source freshness forward to any downstream generation.

### 4.3 Evaluation

1. A skill's locked eval file defines binary criteria (pass/fail per criterion).
2. The scoring runner loads test inputs from `test_input_registry`.
3. The current prompt version generates 10 outputs per test input.
4. Each output is scored against every criterion. An output passes if all criteria return true.
5. Round score = fraction of (input, criterion) pairs that pass.
6. If round score > previous round score: keep the prompt change.
7. If round score <= previous round score: revert the prompt change.
8. Only one prompt change is made per round to isolate causation.

### 4.4 Promotion

1. After a non-regressing round, outputs that pass all criteria and score >= 90% are candidates.
2. Candidates are written to `gold_example_registry` with round_id, prompt_version_id, and scores.
3. The prompt version is promoted only if aggregate score improved. No manual override path exists.

### 4.5 Publishing

1. An artifact destined for publishing is checked against hard gates:
   - Eval gate: the generating skill's latest round must not have regressed.
   - Freshness gate: all cited sources must have freshness_score above threshold.
   - Skill match gate: the artifact type must match the skill's declared output type.
2. If any gate fails, publish is blocked and the failure is logged to `skill_failure_patterns`.
3. If all gates pass, the artifact is pushed to the target system (Confluence, Jira, or Dragonboat) via the same connector layer used for ingestion.

---

## 5. Confidence Scoring

```
confidence = (0.4 * eval_score) + (0.3 * freshness_score) + (0.2 * citation_coverage) + (0.1 * recency_bonus)

Hard gate override:
  if eval_pass == false OR freshness_score < 0.3 OR skill_mismatch == true:
    confidence = 0.0
    publish_blocked = true
```

| Confidence Range | Label       | Publish Allowed |
|------------------|-------------|-----------------|
| 0.90 - 1.00     | High        | Yes             |
| 0.70 - 0.89     | Medium      | Yes             |
| 0.50 - 0.69     | Low         | Yes (with flag) |
| 0.00 - 0.49     | Untrustable | No              |

---

## 6. Technology Choices

| Component            | Technology                              | Rationale                                                  |
|----------------------|-----------------------------------------|------------------------------------------------------------|
| Application services | TypeScript (Node.js)                    | Team expertise, strong typing, shared with UI layer        |
| Primary database     | PostgreSQL 16                           | Relational integrity, tsvector search, pgvector extension  |
| Embeddings search    | pgvector (Postgres extension)           | Co-located with relational data, no separate infra         |
| Full-text search     | Postgres tsvector/tsquery               | Native, no external dependency, adequate for scale         |
| Raw payload storage  | S3-compatible object store              | Cheap, durable, decoupled from structured DB               |
| Connector runtime    | TypeScript services per connector       | Isolated failure domains, independent deploy/scale         |
| Eval engine          | TypeScript + locked eval files (JSON)   | Deterministic, auditable, version-controlled               |
| Task scheduling      | pg-boss (Postgres-backed job queue)     | No Redis dependency, transactional with main DB            |
| API layer            | Express.js or Fastify                   | Lightweight, well-supported in TS ecosystem                |
| CI/CD                | GitHub Actions                          | Standard, integrates with eval locking and git revert loop |

---

## 7. Phase Dependencies

```
Phase 1 (Knowledge Hub + Skill Registry)
  |
  +---> Phase 2 (Criteria-Driven Generators)
  |       |
  |       +---> Phase 5 (UI Project Support)
  |
  +---> Phase 3 (Dragonboat + Jira Reporting)
  |
  +---> Phase 4 (Performance Reporting)
```

Phase 1 is prerequisite for all other phases. Phase 2 is prerequisite for Phase 5. Phases 3 and 4 can proceed in parallel after Phase 1.

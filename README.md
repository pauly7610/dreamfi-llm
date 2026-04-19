# DreamFi

Product operations platform that ingests data from 11 connectors, generates skill-based content through locked binary evaluations, and publishes trusted artifacts.

## What It Does

DreamFi is a five-phase system that integrates data from external connectors into a canonical PostgreSQL schema, generates criterion-driven content through immutable evaluation loops, and publishes trusted artifacts to downstream systems. Every output is scored against hard gates and carries a composite confidence metric.

- **Phase 1:** Normalize data from Jira, Dragonboat, Confluence, Metabase, PostHog, Google Analytics, Klaviyo, NetXD, Sardine, Socure, and Lucidchart into canonical schema
- **Phase 2:** Generate 9 AI skills (agent prompts, summaries, emails, copy) through locked binary evaluation loops
- **Phase 3:** Sync Jira/Dragonboat planning data with trust scoring
- **Phase 4:** Aggregate product metrics from 7 sources with audience-specific narratives
- **Phase 5:** Generate UI artifact copy under style constraints with hard-gate validation

## Architecture

```
External Data (11 connectors)
         |
         v
Canonical PostgreSQL Schema (11 tables)
         |
         v
Hybrid Search (full-text + embeddings)
         |
         v
Domain-Specific Generators (9 locked skills)
         |
         v
Hard-Gate Evaluation (binary scoring)
         |
         v
Gold Examples + Prompt Promotion
```

## Technology Stack

- **Backend:** Python 3.9+ (all production code)
- **Database:** PostgreSQL 15+ (pgvector for embeddings)
- **LLM:** Anthropic Claude 3.5 Sonnet API
- **Testing:** pytest with savepoint-based fixtures (prevent test pollution)
- **Principles:** Autoresearch toolkit (locked evals, score-driven promotion, regression rollback)
- **Migrations:** SQL-based migration system (001_initial.sql, auto-run in conftest)

## Project Status

**Foundation Phase - Complete**

- Complete 500+ line PostgreSQL schema with 11 tables
- 9 locked evaluation templates with hard gates
- 9 immutable Python evaluation runners
- 12 connector interface stubs
- 5 service READMEs with complete architecture
- 8 Architecture Decision Records documenting critical decisions
- Comprehensive test scaffolding

**Next:** Begin Phase 1 connector implementation (Jira -> Dragonboat -> Confluence priority)

## Quick Start

### Prerequisites

```bash
node --version  # v18+
python --version  # 3.9+
psql --version  # 15+
```

### Setup Database

```bash
createdb dreamfi_knowledge_hub
psql -d dreamfi_knowledge_hub -f services/knowledge-hub/db/schema.sql
```

### Setup Environment

```bash
cp .env.example .env
# Fill in API keys for: JIRA, DRAGONBOAT, CONFLUENCE, METABASE, POSTHOG, GA, KLAVIYO, NETXD, SARDINE, SOCURE, LUCIDCHART
```

### Install and Run

```bash
npm install
npm run dev  # Starts all 5 services concurrently
```

## Key Files and Directories

| Path                                   | Purpose                                  |
| -------------------------------------- | ---------------------------------------- |
| `services/knowledge-hub/db/schema.sql` | Canonical data schema with 11 tables     |
| `docs/architecture/connector-specs.md` | Connector implementation guide           |
| `docs/architecture/skill-registry.md`  | All 9 skills with hard gates             |
| `docs/architecture/system-overview.md` | High-level architecture overview         |
| `evals/runners/`                       | Locked evaluation scorers (immutable)    |
| `evals/`                               | Evaluation templates for all 9 skills    |
| `docs/adr/`                            | Architecture decision records (001-008)  |
| `services/*/README.md`                 | Service-specific architecture (5 phases) |
| `GETTING_STARTED.md`                   | Developer onboarding guide               |
| `STATUS.md`                            | Detailed completion status by phase      |

## How Evaluation Works

### Autoresearch Principles

1. Create prompt version for a skill
2. Generate 10 outputs per test input (30 total across 3 inputs)
3. Score outputs against locked binary criteria
4. Promote on improvement: If score_new > score_previous + 2.0%, activate new prompt
5. Rollback on regression: If score_t2 < score_t1, revert to previous version

### Hard Gates

All 9 skills use hard-gate criteria that must pass for an output to be publishable:

- **agent_system_prompt:** Correct intent, no hallucination, specific next action, under 80 words, clear refusal
- **support_agent:** Empathy, accurate resolution, knowledge-base only, escalation path, under 120 words
- **meeting_summary:** Action items with owners, decisions labeled, distinct sections, open questions, under 300 words
- **cold_email:** 75-word limit, specificity, CTA as question, number in opening
- **landing_page_copy:** Headline with number, no buzzwords, outcome CTA, pain point, 80-150 words
- **newsletter_headline:** Number in subject, under 50 characters, knowledge gap, preview adds info
- **product_description:** Problem first, numeric result, no comparisons, objection addressed, 100-200 words
- **resume_bullet:** Strong verb, quantified, under 25 words, business outcome
- **short_form_script:** Curiosity in first 5 words, surprising claim, single thread, under 90 seconds, hook ending

## Documentation

- **GETTING_STARTED.md** - Developer setup and first steps
- **STATUS.md** - Detailed completion checklist by phase
- **docs/architecture/system-overview.md** - High-level architecture
- **docs/architecture/connector-specs.md** - Integration guide for all 11 connectors
- **docs/adr/** - Architecture decision records (001-008)
- **docs/architecture/skill-registry.md** - All skills with evaluation criteria
- **services/knowledge-hub/README.md** - Phase 1 Knowledge Hub service
- **services/generators/README.md** - Phase 2 Generators service
- **services/planning-sync/README.md** - Phase 3 Planning Sync service
- **services/metrics/README.md** - Phase 4 Metrics service
- **services/ui-support/README.md** - Phase 5 UI Support service

## Development Workflow

1. **Pick a phase:** Start with Phase 1 connectors (Jira is highest priority)
2. **Follow the spec:** Reference docs/architecture/connector-specs.md for implementation details
3. **Write tests:** Use tests/unit/ and tests/integration/ patterns as templates
4. **Run evaluations:** Use locked runners in evals/runners/ to validate outputs
5. **Log results:** Update skill changelogs in evals/results/{skill}/changelog.md

## Implementation Priorities

| Phase   | Status     | Priority | Description                                 |
| ------- | ---------- | -------- | ------------------------------------------- |
| Phase 1 | Scaffolded | Highest  | Connector implementations (foundation)      |
| Phase 2 | Scaffolded | High     | Generator service with locked evals         |
| Phase 3 | Scaffolded | Medium   | Planning data normalization and reporting   |
| Phase 4 | Scaffolded | Medium   | Metrics aggregation and audience narratives |
| Phase 5 | Scaffolded | Lower    | UI artifact copy generation                 |

## Project Statistics

- 124 project files (30 Python, 59 Markdown, 34 TypeScript, 1 SQL)
- 500+ line database schema with seed data for all 9 skills
- 9 locked evaluation templates with PASS/FAIL examples
- 9 immutable Python evaluation runners
- 5 comprehensive service documentation files
- 8 architecture decision records
- 3 sample test implementations showing patterns

## Key Architecture Decisions

See docs/adr/ for detailed decision records:

- 001: PostgreSQL and S3 object store for canonical and raw storage
- 002: Hybrid full-text and embeddings search architecture
- 003: Eval locking policy - immutable criteria and runners
- 004: Keep-improve and revert-regress development loop
- 005: Composite confidence scoring model
- 006: Hard-gate publishing policy
- 007: Connector freshness scoring and data trust
- 008: Skill promotion policy based on score improvement threshold

## Contributing

See GETTING_STARTED.md for development setup and testing philosophy.

---

Questions? Review docs/architecture/system-overview.md or check the detailed changelogs in evals/results/.

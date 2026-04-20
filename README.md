# DreamFi

Skill-gated generation and evaluation layer on top of [Onyx](https://github.com/onyx-dot-app/onyx).

## What it does

Onyx indexes company knowledge (Jira, Confluence, GDrive, Slack, ...) and
provides hybrid search, citations, and permissioning. DreamFi sits on top
and produces trustworthy artifacts for 9 named skills:

- `meeting_summary`, `cold_email`, `landing_page_copy`, `newsletter_headline`,
  `product_description`, `resume_bullet`, `short_form_script`,
  `agent_system_prompt`, `support_agent`

Every artifact is scored against immutable hard-gate evals. Prompts only
advance when a new round scores materially above the previous active
version; regressions revert. Outputs that fail a hard gate cannot publish.

## Architecture

See `docs/architecture/onyx-integration.md` and ADR-009 / ADR-010.

```
Onyx  ->  retrieval + citations  ->  DreamFi SkillEngine  ->  locked eval
                                          |
                                          v
                               PromotionGate + PublishGuard
```

## Quick start

```bash
make bootstrap        # brings up Onyx + DreamFi Postgres/API
# Onyx UI: http://localhost:3000
# DreamFi console: http://localhost:5001/console
```

Configure a Jira / Confluence / GDrive connector in Onyx, let it index, then:

```bash
make seed                              # create Onyx personas + doc-sets
make run-round SKILL=meeting_summary   # run one eval round
```

## Development

```bash
make test        # unit + mocked integration tests
make test-live   # requires Onyx at $ONYX_BASE_URL
make lint        # ruff
```

## Layout

- `dreamfi/` - the DreamFi Python package (thin skill layer).
- `evals/` - **locked** templates and runners. Never edit these files.
- `deployment/` - docker-compose and Dockerfile.
- `scripts/` - operator CLIs.
- `docs/adr/` - architecture decision records (see 009 + 010 for the Onyx pivot).

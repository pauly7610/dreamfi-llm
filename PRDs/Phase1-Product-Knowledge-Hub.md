# PRD: Phase 1 — Product Knowledge Hub

**Version:** 1.0 | April 2026
**Author:** Paul (with Chanel)
**Status:** Draft
**Timeline:** Weeks 1–2 (Foundation)

---

## Hypothesis

Our team lacks a single source of truth for product, tech stack, and UX knowledge. Every question today requires hunting down humans or outdated docs, slowing decisions and onboarding. A persistent, LLM-maintained wiki will compound knowledge over time so anyone can get accurate, grounded answers instantly.

---

## Problem

| Pain Point | Impact |
|---|---|
| Knowledge scattered across Confluence, Slack, Jira, Figma, meeting notes | Decisions delayed; duplicate questions |
| No connection between frontend UX and backend logic | Engineers and PMs debug blind |
| Chanel holds most tribal knowledge | Single point of failure; bottleneck |
| New team members waste hours tracking down context | Onboarding takes weeks instead of days |

---

## Goals

1. Build a searchable, always-current knowledge base that explains **what the user sees** (frontend) + **how it works** (backend logic, edge cases, data flows).
2. Enable any team member to ask a question and get a precise, cited answer without finding a human.
3. Make the hub the foundation that every future phase pulls from.

## Non-Goals

- Not a replacement for raw source docs (Jira, Figma, code, etc.).
- Not a general company wiki or HR knowledge base.
- Not a one-time dump — must be living and maintained with minimal human effort.

---

## Key Scenarios

**New PM onboards:**
> Types "How does KYC flow work end-to-end?" → gets frontend screens + backend decision tree + drop-off reasons + recent changes.

**Engineer debugging:**
> "What triggers the sponsor bank error code X?" → linked to exact frontend error message + backend code path + last fix.

**Leadership asks:**
> "Why did activation drop last week?" → hub surfaces the exact UX change + A/B test + backend config.

**Cross-functional partner:**
> "What does the user see after third-party risk assessment?" → single page with screenshots, flows, and logic.

---

## Approach: Karpathy LLM Wiki Pattern

### Architecture

```
┌─────────────────────────────────────────────────┐
│  QUERY LAYER                                     │
│  Any team member asks a question → LLM searches  │
│  index → synthesizes answer with citations        │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  WIKI LAYER (LLM-owned, structured Markdown)     │
│  • Entity pages (features, flows, components)    │
│  • Concept pages (KYC, fraud checks, activation) │
│  • Comparison tables & synthesis pages            │
│  • Index.md + log.md for navigation               │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  SCHEMA LAYER                                    │
│  CLAUDE.md / AGENTS.md defining:                 │
│  • Folder structure & naming conventions          │
│  • Cross-referencing rules                       │
│  • Maintenance workflows & linting rules          │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  RAW SOURCES (immutable)                         │
│  Confluence • Jira • Slack exports • Figma       │
│  Code comments • Meeting transcripts • PostHog   │
└─────────────────────────────────────────────────┘
```

### Operations

| Operation | What it does | Frequency |
|---|---|---|
| **Ingest** | LLM reads new source material → updates 10–15 wiki pages | On new source material |
| **Query** | LLM searches index + synthesizes answer with citations | On demand |
| **Lint** | Health checks for contradictions, orphans, stale pages | Weekly automated |

---

## Tool Connections

| Tool | Role in Phase 1 |
|---|---|
| **Confluence** | Primary raw source for existing product docs; wiki pages exported and ingested |
| **Jira** | Source for ticket context, epic descriptions, acceptance criteria, and change history |
| **Lucid Charts** | Source for existing flow diagrams; new flows created here and linked from wiki pages |
| **Slack** | Exported threads ingested as raw source for tribal knowledge capture |
| **Figma** | UI screenshots and design specs linked as visual references in entity pages |
| **PostHog** | Event definitions and funnel configs referenced in feature/flow pages |
| **Metabase** | Query definitions and dashboard links embedded in relevant wiki pages |
| **Sardine** | Transaction monitoring rules and fraud flow logic documented in wiki |
| **Socure** | Identity verification decision trees and integration points documented |
| **Ledger NetXD** | Ledger logic and reconciliation flows documented in wiki |

---

## Delivery Plan (Weeks 1–2)

| Day | Milestone | Owner |
|---|---|---|
| W1 D1–2 | Export and organize raw sources (Confluence, Jira, Slack, Figma) | Paul |
| W1 D2–3 | Define schema layer (CLAUDE.md): folder structure, naming, cross-ref rules | Paul |
| W1 D3–5 | Ingest session 1: top 15 features/flows with Chanel as validator | Paul + Chanel |
| W2 D1–2 | Ingest session 2: remaining critical flows (KYC, fraud, activation, sponsor bank) | Paul + Chanel |
| W2 D3 | Build Index.md, set up lint automation, test query layer | Paul |
| W2 D4–5 | Validation: 5 team members run real queries, iterate on gaps | Paul + Chanel |

---

## Success Criteria

- [ ] Any team member can ask a product question and receive an accurate, grounded, cited answer in **<2 minutes** without tracking down a human.
- [ ] Hub covers all critical flows: KYC, activation, fraud checks, sponsor bank, core transaction paths.
- [ ] Weekly lint runs with <5% orphan/stale page rate.
- [ ] Chanel validates initial content accuracy at >90%.

---

## Partners & Resourcing

| Person | Role |
|---|---|
| **Chanel** | Primary content owner and validator |
| **Paul** | Implementation lead, LLM agent setup |
| No additional headcount needed initially | |

---

## Dependencies

- Access to all existing sources (Confluence, Jira export, Slack, Figma).
- Obsidian (or preferred Markdown wiki tool) license/setup.
- Chanel availability for structured ingest sessions in weeks 1–2.

## Risks

| Risk | Mitigation |
|---|---|
| Initial content quality depends on Chanel's availability | Structured ingest sessions with pre-scheduled blocks in W1–W2 |
| Wiki grows stale without linting discipline | Automated weekly lint reminders + log.md tracking |
| Team doesn't adopt query habit | Seed with 10 "greatest hits" questions; demo in team meeting |

> [superseded] These PRDs predate the DreamFi-on-Onyx overhaul (commit f66be26). Architecture has shifted to a thin Skills + Evals layer on top of Onyx as the knowledge substrate. Kept for historical context only — see ADR-009 and ADR-010.

# PRD: Phase 2 — Document Generators

**Version:** 1.0 | April 2026
**Author:** Paul (with Morgan)
**Status:** Draft
**Timeline:** Week 2–3 (overlaps with Phase 1 tail)

---

## Hypothesis

Product team members waste hours writing the same document types from scratch or tweaking prompts. Form-based generators using our exact voice, structure, and templates will produce consistent, on-standard docs instantly.

---

## Problem

| Pain Point | Impact |
|---|---|
| Same doc types written from scratch repeatedly | 2+ hours per document |
| Inconsistent formatting, voice, and section coverage | Bank partners and leadership receive uneven quality |
| Prompt engineering required for each doc | Not everyone is effective at prompting; outputs vary wildly |
| No enforced standards for required sections | Critical sections (edge cases, risk tables, compliance) get skipped |

---

## Goals

1. Deliver **6 generators** that output complete documents with zero prompt writing.
2. Enforce DreamFi voice, branding, and required sections every time.
3. Make document creation **5–10x faster** and perfectly consistent.

## Non-Goals

- Not a general AI writing tool.
- Not replacing human judgment on content strategy.
- Not building custom generators outside the 6 listed.

---

## Required Generators

| # | Generator | Primary User | Key Output Sections |
|---|---|---|---|
| 1 | **Technical PRD** | PMs, Engineers | Hypothesis, architecture, edge cases, data flows, API contracts, success metrics |
| 2 | **Business PRD** | PMs, Leadership | Business case, market context, revenue impact, success metrics, stakeholder alignment |
| 3 | **Third-Party Risk Assessment BRD** | Risk/Compliance | Vendor evaluation, data flow, security controls, compliance mapping, risk matrix |
| 4 | **Sponsor Bank Requirements Doc** | Partnerships, Compliance | Regulatory requirements, integration specs, SLA definitions, compliance checklist |
| 5 | **Discovery Document** | PMs | Problem framing, user research synthesis, opportunity sizing, recommendation |
| 6 | **Epic Builder** | PMs, Engineering leads | Epic summary, story breakdown, acceptance criteria, dependencies, estimation guidance |

---

## Key Scenarios

**PM creates Technical PRD:**
> Fills 8-field form for "KYC Enhancement" → receives fully formatted doc with exact section headings, success metrics format, edge-case tables, and DreamFi voice. **10 minutes vs. 2 hours.**

**Risk team creates sponsor bank doc:**
> Fills sponsor bank form → outputs compliant document ready for bank review with all regulatory sections pre-populated.

**Engineering lead builds epic:**
> Fills epic builder form with feature description → gets structured epic with stories, acceptance criteria, and Jira-ready formatting.

---

## Functional Requirements

### Form UI

- Simple web form interface (or Confluence template + automation).
- Each generator has its own form with 6–10 required fields + optional fields.
- Field types: text, dropdown (pre-populated options), multi-select, date, rich text.
- Form validation ensures required fields are complete before generation.

### Template Engine

- Pre-loaded templates with DreamFi voice (tone, phrasing, required tables).
- Each template defines: required sections, section ordering, formatting rules, voice guidelines.
- Templates pull context from Phase 1 Knowledge Hub where applicable.
- Version-controlled templates — Morgan owns template updates.

### Output

- Generated doc outputs to **Confluence page** (primary) + exportable Word/PDF.
- Auto-links to relevant Jira epics/tickets when referenced.
- Includes metadata header: generator version, author, date, template version.

### AI Assist (Optional)

- Edge-case suggestions based on Knowledge Hub context.
- Auto-populated fields from Jira epic data when epic key is provided.
- Human must review all AI-suggested content before finalizing.

---

## Tool Connections

| Tool | Role in Phase 2 |
|---|---|
| **Confluence** | Primary output destination; generated docs published as Confluence pages |
| **Jira** | Epic/ticket data auto-pulled into forms; Epic Builder outputs Jira-ready story format |
| **Lucid Charts** | Flow diagrams auto-linked in Technical PRDs and Discovery docs |
| **Dragonboat** | Generated PRDs link to Dragonboat initiatives for roadmap traceability |
| **Phase 1 Knowledge Hub** | Generators pull context (feature descriptions, flow logic, edge cases) from wiki |
| **Sardine** | Risk assessment BRD templates include Sardine monitoring rule references |
| **Socure** | Risk assessment BRD templates include Socure verification flow references |
| **Ledger NetXD** | Sponsor bank docs reference NetXD ledger integration specs |

---

## Delivery Plan (Weeks 2–3)

| Day | Milestone | Owner |
|---|---|---|
| W2 D1–2 | Morgan finalizes templates for all 6 generators (sections, voice guide, field definitions) | Morgan |
| W2 D3–4 | Paul builds form infrastructure + template engine | Paul |
| W2 D5 | Generator 1 (Technical PRD) + Generator 6 (Epic Builder) live — test with real inputs | Paul + Morgan |
| W3 D1–2 | Generators 2–4 (Business PRD, Risk BRD, Sponsor Bank) live | Paul + Morgan |
| W3 D3 | Generator 5 (Discovery Doc) live | Paul |
| W3 D4 | Chanel validates voice/content on all 6 outputs | Chanel |
| W3 D5 | Team walkthrough + feedback incorporation | All |

---

## Success Criteria

- [ ] Any product team member can produce a complete, on-standard document by filling in a form — **no prompt writing required**.
- [ ] All 6 generators produce output that passes Morgan's voice/format review on first generation.
- [ ] Average generation time: **<15 minutes** (form fill to finished doc).
- [ ] Generated docs include all required sections with no manual additions needed.

---

## Partners & Resourcing

| Person | Role |
|---|---|
| **Morgan** | Template development lead, ongoing template owner |
| **Paul** | Form tooling build, generator implementation |
| **Chanel** | Voice/content validation on first templates |

---

## Dependencies

- Finalized templates from Morgan (blocker for build start).
- Confluence API access for page creation.
- Jira API access for epic data pull.
- Phase 1 Knowledge Hub operational (for context-aware generation).

## Risks

| Risk | Mitigation |
|---|---|
| Templates don't capture real use cases | Validate against 3 recent real docs per generator before shipping |
| Templates drift over time | Morgan designated as ongoing owner with quarterly review cadence |
| Confluence API limitations | Fallback: Google Docs output + manual Confluence paste |

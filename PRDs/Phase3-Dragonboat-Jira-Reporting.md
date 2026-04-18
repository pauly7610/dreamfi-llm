# PRD: Phase 3 — Dragonboat Configuration & Jira Reporting

**Version:** 1.0 | April 2026
**Author:** Paul (with Morgan + Chanel)
**Status:** Draft
**Timeline:** Week 2–3 (parallel with Phase 2)

---

## Hypothesis

The Dragonboat-Jira integration exists but configuration, taxonomy, and hygiene are broken. Fixing these will deliver consistent, trusted reporting and clear ownership — eliminating the "nobody trusts the data" problem.

---

## Problem

| Pain Point | Impact |
|---|---|
| No clean product taxonomy or hierarchy | Reporting pulls inconsistent data; leadership can't trust rollups |
| Field/status mappings between Jira and Dragonboat are broken or ambiguous | RAG statuses don't match reality; manual cleanup required |
| No hygiene rules or enforcement | Stale tickets, missing fields, orphaned epics pollute reports |
| No saved reports for leadership questions | Every reporting request requires ad-hoc manual work |

---

## Goals

1. Audit current state and define clean **product taxonomy + hierarchy**.
2. Fix **field/status mapping** and establish enforceable hygiene rules.
3. Build **saved reports** leadership actually needs.
4. Create **single source of truth** for roadmap and delivery data.

## Non-Goals

- Not rebuilding the Dragonboat-Jira integration.
- Not replacing Jira or Dragonboat.
- Not changing engineering workflow in Jira.

---

## Key Scenarios

**Leadership asks "What is the status of all Q2 epics by priority?"**
> One saved report pulls clean data — no manual cleanup, no caveats.

**PM creates new epic:**
> Auto-maps to correct taxonomy level, required fields enforced, status rules applied.

**Cross-team view:**
> Shows consistent RAG status without manual cleanup or "let me check with the team" delays.

**Quarterly planning:**
> Dragonboat shows accurate roadmap with delivery confidence tied to real Jira data.

---

## Functional Requirements

### 1. Taxonomy & Hierarchy Definition

```
Initiative (Dragonboat)
  └── Feature (Dragonboat)
        └── Epic (Jira ↔ Dragonboat synced)
              └── Story / Task / Bug (Jira only)
```

- Define clear rules for what lives at each level.
- Document naming conventions and required fields per level.
- Align with Dragonboat's native hierarchy model.

### 2. Field & Status Mapping

| Jira Field | Dragonboat Field | Mapping Rule |
|---|---|---|
| Status | Progress Status | To Do → Not Started, In Progress → In Progress, Done → Completed |
| Priority | Priority | Direct 1:1 map (P0–P3) |
| Fix Version | Release | Map to Dragonboat release |
| Labels | Tags | Sync selected labels only (defined list) |
| Epic Link | Parent Feature | Auto-link on sync |

- RAG status in Dragonboat derived from: % stories complete + blockers flagged + days to target date.
- No manual RAG overrides without comment explaining why.

### 3. Hygiene Rules

| Rule | Enforcement |
|---|---|
| Every epic must have: summary, owner, target date, priority, linked feature | Jira automation blocks transition without required fields |
| Epics with no activity in 14 days flagged as "Stale" | Automated Slack reminder to owner |
| Stories without acceptance criteria cannot move to "Ready for Dev" | Jira workflow validation |
| Completed epics must have actual completion date | Auto-set on final story closure |
| Orphaned epics (no parent feature) surfaced weekly | Dragonboat saved filter + Slack alert |

### 4. Saved Reports

| Report | Audience | Data Source | Refresh |
|---|---|---|---|
| **Q2 Epic Status by Priority** | Leadership | Dragonboat (synced from Jira) | Real-time |
| **Feature Delivery Confidence** | Leadership, PMs | Dragonboat rollup | Weekly |
| **Team Velocity & Throughput** | Engineering leads | Jira sprint data | Per sprint |
| **Stale/Blocked Items** | PMs, Eng leads | Jira + Dragonboat | Daily |
| **Roadmap vs. Actuals** | Leadership | Dragonboat timeline view | Monthly |
| **Cross-team Dependency View** | PMs | Jira epic links + Dragonboat | Weekly |

---

## Tool Connections

| Tool | Role in Phase 3 |
|---|---|
| **Jira** | Source of truth for execution-level data (epics, stories, sprints, velocity) |
| **Dragonboat** | Source of truth for roadmap, initiative tracking, feature-level reporting |
| **Confluence** | Taxonomy definition doc, hygiene rules doc, report catalog published here |
| **Lucid Charts** | Taxonomy hierarchy diagram; data flow diagram for Jira↔Dragonboat sync |
| **Slack** | Hygiene violation alerts and stale-item reminders delivered here |

---

## Delivery Plan (Weeks 2–3)

| Day | Milestone | Owner |
|---|---|---|
| W2 D1 | Audit current Dragonboat config + Jira field mappings; document gaps | Paul |
| W2 D2 | Taxonomy workshop with Morgan + Chanel (time-boxed 90 min) | Paul + Morgan + Chanel |
| W2 D3–4 | Implement taxonomy in Dragonboat; fix field/status mappings | Paul |
| W2 D5 | Build hygiene automation rules in Jira (required fields, stale alerts) | Paul |
| W3 D1–2 | Create all 6 saved reports in Dragonboat | Paul + Morgan |
| W3 D3 | Test sync end-to-end: create epic in Jira → verify correct mapping in Dragonboat | Paul |
| W3 D4 | Leadership walkthrough of reports; gather feedback | Paul + Morgan + Chanel |
| W3 D5 | Incorporate feedback; document hygiene rules in Confluence | Paul |

---

## Success Criteria

- [ ] All epics map cleanly to features → initiatives with no orphans.
- [ ] Field/status mappings produce accurate RAG status without manual intervention.
- [ ] 6 saved reports operational and trusted by leadership.
- [ ] Hygiene automation catches >90% of violations within 24 hours.
- [ ] Defined owner for ongoing hygiene maintenance.

---

## Partners & Resourcing

| Person | Role |
|---|---|
| **Morgan** | Taxonomy co-owner, report validation |
| **Chanel** | Taxonomy co-owner, content validation |
| **Paul** | Implementation lead, Dragonboat admin, Jira automation |

---

## Dependencies

- Dragonboat admin access for Paul.
- Leadership alignment on taxonomy (one 90-min workshop).
- Jira admin access for workflow/automation changes.

## Risks

| Risk | Mitigation |
|---|---|
| Taxonomy debates delay launch | Time-boxed 90-min workshop; Paul proposes draft taxonomy in advance for reaction |
| Teams don't follow new hygiene rules | Automated enforcement (block transitions, Slack reminders) rather than relying on habit |
| Dragonboat sync lag creates stale data | Document expected sync frequency; set expectations with leadership |

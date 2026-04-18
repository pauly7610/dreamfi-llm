# DreamFi Product Toolkit — Master Delivery Plan

**Version:** 1.0 | April 2026
**Author:** Paul
**Delivery Window:** 4 Weeks (April 21 – May 16, 2026)

---

## Program Overview

Five phases delivering a complete product operations toolkit: from knowledge management to document generation to reporting to UI support. Phase 1 is the foundation — everything else pulls from it. Phase 5 runs in parallel throughout.

---

## 4-Week Timeline

```
         Week 1           Week 2           Week 3           Week 4
     Apr 21–25         Apr 28–May 2      May 5–9          May 12–16
    ┌─────────────┬──────────────────┬─────────────────┬─────────────────┐
 P1 │████████████████████████████    │                 │                 │
    │ Knowledge Hub (Foundation)     │                 │                 │
    ├─────────────┼──────────────────┼─────────────────┼─────────────────┤
 P2 │             │   ██████████████████████████       │                 │
    │             │   Document Generators              │                 │
    ├─────────────┼──────────────────┼─────────────────┼─────────────────┤
 P3 │             │   ██████████████████████████       │                 │
    │             │   Dragonboat + Jira Reporting      │                 │
    ├─────────────┼──────────────────┼─────────────────┼─────────────────┤
 P4 │             │                  │████████████████████████████████   │
    │             │                  │ Performance & Event Reporting     │
    ├─────────────┼──────────────────┼─────────────────┼─────────────────┤
 P5 │████████████████████████████████████████████████████████████████████│
    │ UI Project Support (standing, parallel throughout)                 │
    └─────────────┴──────────────────┴─────────────────┴─────────────────┘
```

---

## Week-by-Week Breakdown

### Week 1 (Apr 21–25) — Foundation

| Day | Phase 1: Knowledge Hub | Phase 5: UI Support |
|---|---|---|
| Mon | Export raw sources (Confluence, Jira, Slack, Figma) | Initial briefing from Victor |
| Tue | Define schema layer (CLAUDE.md) | Scope alignment; first discovery doc |
| Wed | Ingest session 1 with Chanel (top 15 features/flows) | |
| Thu | Ingest session 1 continued | Build initial UI epics |
| Fri | Ingest session 1 wrap-up | Ingest UI learnings to hub |

**Key deliverable:** Knowledge Hub v1 with top 15 features/flows documented.

### Week 2 (Apr 28–May 2) — Build + Configure

| Day | Phase 1 (tail) | Phase 2: Doc Generators | Phase 3: Dragonboat/Jira | Phase 5 |
|---|---|---|---|---|
| Mon | Ingest session 2 (KYC, fraud, activation) | Morgan finalizes templates | Audit current config | Review Victor priorities |
| Tue | Ingest session 2 continued | Morgan finalizes templates | Taxonomy workshop (90 min) | |
| Wed | Build Index.md + lint automation | Paul builds form infra | Implement taxonomy + fix mappings | Weekly sync with Victor |
| Thu | Validation: team runs queries | Build generators 1+6 (Tech PRD, Epic Builder) | Implement taxonomy + fix mappings | |
| Fri | Validation continued; iterate | Test generators 1+6 | Build hygiene automation | Ingest UI learnings |

**Key deliverables:** Knowledge Hub validated. First 2 generators live. Taxonomy locked. Hygiene automation on.

### Week 3 (May 5–9) — Generators + Reports + Dashboards Start

| Day | Phase 2 (continued) | Phase 3 (continued) | Phase 4: Dashboards | Phase 5 |
|---|---|---|---|---|
| Mon | Build generators 2–4 (Biz PRD, Risk BRD, Sponsor Bank) | Create saved reports | Metric definition workshop (90 min) | Review Victor priorities |
| Tue | Build generators 2–4 continued | Create saved reports | Build dashboards 1–3 (Funnel, KYC, Activation) | |
| Wed | Build generator 5 (Discovery Doc) | Test end-to-end sync | Build dashboards 1–3 continued | Weekly sync with Victor |
| Thu | Chanel validates all 6 outputs | Leadership report walkthrough | Build dashboards 4–5 (Retention, Delivery) | |
| Fri | Team walkthrough + feedback | Feedback + Confluence docs | Build dashboards 4–5 continued | Ingest UI learnings |

**Key deliverables:** All 6 generators live. All saved reports operational. First 5 dashboards built.

### Week 4 (May 12–16) — Dashboards Complete + Polish

| Day | Phase 4 (continued) | Phase 5 | All Phases |
|---|---|---|---|
| Mon | Build dashboards 6–7 (Marketing, Fraud) | Review Victor priorities | |
| Tue | Build snapshot template + filter logic | | |
| Wed | Test snapshot with real past event | Weekly sync with Victor | |
| Thu | Leadership walkthrough of all dashboards | | Final review all deliverables |
| Fri | Feedback + publish metric dictionary | Ingest UI learnings | **Ship. Celebrate.** |

**Key deliverables:** All 7 dashboards live. Snapshot tool operational. Metric dictionary published.

---

## Tool Stack Summary

| Tool | Phases | Purpose |
|---|---|---|
| **Jira** | P1, P2, P3, P5 | Execution tracking, epic/story management, hygiene automation |
| **Dragonboat** | P3, P5 | Roadmap, initiative tracking, RAG reporting, delivery confidence |
| **Confluence** | P1, P2, P3, P4, P5 | Documentation destination, report publishing, knowledge sharing |
| **Lucid Charts** | P1, P3, P4, P5 | Flow diagrams, taxonomy visuals, data flow diagrams, UI flows |
| **Metabase** | P1, P4 | Internal data, dashboard platform, snapshot queries |
| **PostHog** | P1, P4, P5 | Event analytics, funnels, feature flag tracking |
| **Google Analytics** | P4 | Traffic, channel attribution, campaign tracking |
| **Klaviyo** | P4 | Email campaign performance, marketing attribution |
| **Ledger NetXD** | P1, P4 | Transaction/ledger data, settlement reporting |
| **Sardine** | P1, P4 | Fraud transaction monitoring, alert volumes |
| **Socure** | P1, P4 | Identity verification, risk scoring |
| **Figma** | P1, P5 | Design reference, UI screenshots |
| **Slack** | P1, P3 | Knowledge source, hygiene alerts |

---

## Key Workshops (Calendar Holds Needed)

| Workshop | When | Duration | Attendees | Purpose |
|---|---|---|---|---|
| Taxonomy Definition | W2 D2 (Apr 29) | 90 min | Paul, Morgan, Chanel | Lock product hierarchy for Dragonboat/Jira |
| Metric Definitions | W3 D1 (May 5) | 90 min | Paul, Morgan, Chanel | Lock metric definitions for dashboards |
| Leadership Report Review | W3 D4 (May 8) | 60 min | Paul, Morgan, Chanel, Leadership | Validate saved reports |
| Leadership Dashboard Review | W4 D4 (May 15) | 60 min | Paul, Morgan, Chanel, Leadership | Validate dashboards + snapshot |

---

## Resourcing

| Person | Allocation | Phases |
|---|---|---|
| **Paul** | Full-time (80% phases 1–4, 20% phase 5) | All |
| **Morgan** | Part-time (~30%) | P2 (templates), P3 (taxonomy), P4 (metrics) |
| **Chanel** | Part-time (~25%) | P1 (validation), P2 (voice), P3 (taxonomy), P4 (metrics) |
| **Victor** | Weekly syncs | P5 (scope owner) |

No additional headcount required.

---

## Critical Path

```
Phase 1 Knowledge Hub ──→ Phase 2 Generators (pulls context from hub)
                      ──→ Phase 4 Dashboards (metric definitions reference hub)

Phase 3 Taxonomy     ──→ Phase 4 Delivery Dashboard (clean Jira data required)

Phase 5 runs independently but benefits from all other phases.
```

**The single biggest risk to the timeline is Chanel's availability in Week 1 for ingest sessions.** If this slips, everything downstream shifts. Pre-schedule those blocks now.

---

## Exit Criteria (Program Complete When)

- [ ] Knowledge Hub answers product questions in <2 minutes with citations
- [ ] All 6 document generators produce on-standard output from forms
- [ ] Dragonboat/Jira reporting trusted by leadership with clean data
- [ ] 7 standing dashboards live; snapshot tool produces reports in <30 min
- [ ] Victor confirms UI project has adequate product support
- [ ] All metric and taxonomy definitions documented in Confluence

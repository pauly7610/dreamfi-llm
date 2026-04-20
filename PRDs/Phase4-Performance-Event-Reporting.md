> [superseded] These PRDs predate the DreamFi-on-Onyx overhaul (commit f66be26). Architecture has shifted to a thin Skills + Evals layer on top of Onyx as the knowledge substrate. Kept for historical context only — see ADR-009 and ADR-010.

# PRD: Phase 4 — Product Performance & Event-Based Reporting

**Version:** 1.0 | April 2026
**Author:** Paul (with Morgan + Chanel)
**Status:** Draft
**Timeline:** Weeks 3–4 (depends on Phase 3 taxonomy)

---

## Hypothesis

We have data but no single place to answer "How is the product performing this week?" or quickly produce credible point-in-time reports tied to events. Standing dashboards + snapshot capability will fix this.

---

## Problem

| Pain Point | Impact |
|---|---|
| No unified view of product performance | Monday standup starts with "let me pull some numbers" |
| Metrics scattered across PostHog, Google Analytics, Metabase, Klaviyo | Different people cite different numbers for the same question |
| No point-in-time reporting capability | Event reports take days to assemble manually |
| No consistent metric definitions | "Activation" means different things to different teams |
| No connection between product changes and metric movement | Can't answer "did the last UI change improve funnel?" |

---

## Goals

1. Build **standing dashboards** for funnel conversion, KYC drop-off, activation, retention, and delivery.
2. Enable **point-in-time snapshot reporting** (tied to specific event or org engagement over defined period).
3. One trusted place for weekly performance answers and ad-hoc event reports.

## Non-Goals

- Not building new data pipelines.
- Not replacing existing analytics tools (PostHog, GA, Metabase).
- Not real-time alerting (that's an ops concern).

---

## Key Scenarios

**Monday morning:**
> Open dashboard → see this week's activation, retention, and KYC drop-off at a glance. No querying, no waiting.

**Post-event:**
> "Pull snapshot for Bank X engagement March 1–15" → pre-built template generates credible report with all relevant metrics in <30 minutes.

**Leadership asks:**
> "Did the last UI change improve funnel?" → direct answer from standing dashboard with before/after comparison.

**Marketing review:**
> "What's our email-to-activation conversion?" → dashboard shows Klaviyo campaign performance tied to product activation.

**Fraud review:**
> "What's our fraud rate by channel this month?" → Sardine + Socure data in one view.

---

## Functional Requirements

### Part 1: Standing Dashboards

| Dashboard | Key Metrics | Primary Data Source |
|---|---|---|
| **Funnel Conversion** | Visitor → Signup → KYC Start → KYC Complete → First Transaction | PostHog + Google Analytics |
| **KYC Drop-off** | Drop-off by step, by device, by cohort; error rates by type | PostHog + Metabase |
| **Activation** | Time to first transaction, activation rate by cohort, activation by channel | PostHog + Metabase |
| **Retention** | D7/D30/D90 retention curves, churn by segment, reactivation rate | Metabase + PostHog |
| **Delivery & Quality** | Sprint velocity, bug rate, deploy frequency, incident count | Jira + Dragonboat (Phase 3) |
| **Marketing Performance** | Campaign → signup → activation flow, email open/click rates, channel attribution | Klaviyo + Google Analytics |
| **Fraud & Risk** | Transaction monitoring alerts, fraud rate by channel, false positive rate | Sardine + Socure + Metabase |

**Dashboard requirements:**
- Consistent visual language across all dashboards.
- Standard date range selector (7d, 30d, 90d, custom).
- Drill-down capability on each metric.
- Metric definitions displayed on hover (single source of truth).
- All dashboards built in **Metabase** (primary) with key views mirrored to Confluence for async consumption.

### Part 2: Point-in-Time Snapshot Tool

**Purpose:** Generate a credible, presentation-ready report tied to a specific event, org, or time period.

**Filters:**
- Date range (required)
- Organization / partner (optional)
- Event or campaign (optional)
- Segment (optional)

**Output includes:**
- All standing dashboard metrics filtered to the specified scope.
- Before/after comparison when applicable.
- Trend lines and annotations for key events.
- Export to PDF / slide-ready format.

**Snapshot template structure:**
```
1. Executive Summary (auto-generated from metrics)
2. Funnel Performance (filtered)
3. Engagement Metrics (filtered)
4. Fraud & Risk Summary (filtered)
5. Marketing Attribution (if applicable)
6. Key Observations (human-written section)
7. Appendix: Raw Data Tables
```

---

## Metric Definitions (Agreed Source of Truth)

| Metric | Definition | Source |
|---|---|---|
| **Activation** | User completes first transaction within 30 days of signup | PostHog event: `transaction_complete` + Metabase |
| **KYC Completion Rate** | Users who reach KYC "approved" status / users who started KYC | PostHog funnel |
| **Retention (D30)** | Users who perform any qualifying action 30 days after activation | Metabase cohort query |
| **Fraud Rate** | Flagged transactions / total transactions (Sardine + Socure combined) | Sardine API + Socure API → Metabase |
| **Campaign Conversion** | Klaviyo email recipients who reach activation | Klaviyo + PostHog cross-reference |

*Full metric dictionary to be finalized in W3 D1 workshop.*

---

## Tool Connections

| Tool | Role in Phase 4 |
|---|---|
| **Metabase** | Primary dashboard platform; all standing dashboards built here; snapshot queries run here |
| **PostHog** | Event-level analytics source — funnels, feature flags, session recordings referenced |
| **Google Analytics** | Top-of-funnel traffic, channel attribution, campaign UTM tracking |
| **Klaviyo** | Email campaign performance data; campaign → activation attribution |
| **Sardine** | Transaction monitoring data; fraud alert volumes; false positive rates |
| **Socure** | Identity verification pass/fail rates; risk score distributions |
| **Ledger NetXD** | Transaction volume and settlement data for delivery dashboard |
| **Jira + Dragonboat** | Delivery metrics (velocity, bug rate) from Phase 3 clean data |
| **Confluence** | Dashboard summaries and snapshot reports published for async access |
| **Lucid Charts** | Data flow diagrams showing which sources feed which dashboards |

---

## Delivery Plan (Weeks 3–4)

| Day | Milestone | Owner |
|---|---|---|
| W3 D1 | Metric definition workshop (90 min, time-boxed) — lock definitions | Paul + Morgan + Chanel |
| W3 D2–3 | Build dashboards 1–3 (Funnel, KYC, Activation) in Metabase | Paul |
| W3 D4–5 | Build dashboards 4–5 (Retention, Delivery) in Metabase | Paul |
| W4 D1 | Build dashboards 6–7 (Marketing, Fraud) in Metabase | Paul |
| W4 D2 | Build snapshot template + filter logic | Paul |
| W4 D3 | Test snapshot: generate report for a real past event | Paul + Morgan |
| W4 D4 | Leadership walkthrough of all dashboards + sample snapshot | Paul + Morgan + Chanel |
| W4 D5 | Feedback incorporation; publish metric dictionary to Confluence | Paul |

---

## Success Criteria

- [ ] One place to answer **"How is the product performing this week?"** — accessible without querying or waiting.
- [ ] Snapshot tool produces credible point-in-time report in **<30 minutes** (vs. days today).
- [ ] All 7 standing dashboards live with consistent metric definitions.
- [ ] Metric definitions documented and agreed — no more "what do you mean by activation?"
- [ ] Leadership confirms dashboards answer their top 5 recurring questions.

---

## Partners & Resourcing

| Person | Role |
|---|---|
| **Morgan** | Metric definition co-owner, report validation, leadership alignment |
| **Chanel** | Metric definition co-owner, content validation |
| **Paul** | Dashboard build, snapshot tool build, Metabase implementation |

---

## Dependencies

- Clean data from **Phase 3** taxonomy/hygiene (delivery metrics depend on this).
- Metabase admin access + connections to PostHog, GA, Klaviyo, Sardine, Socure, NetXD.
- One metric definition workshop with Morgan + Chanel.

## Risks

| Risk | Mitigation |
|---|---|
| Metric definitions vary by team | Time-boxed definition workshop in W3 D1; lock definitions in Confluence |
| Data quality issues in source systems | Dashboard includes data quality indicators; known gaps documented |
| Metabase performance with cross-source queries | Pre-aggregate key metrics; use Metabase caching for heavy dashboards |
| Sardine/Socure API access limitations | Start API access requests in W2; fallback to CSV export if needed |

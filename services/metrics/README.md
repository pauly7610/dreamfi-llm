# DreamFi Phase 4: Product Performance + Event-Based Reporting

## Goal

Support weekly and event-based product reporting with both data trust and interpretation trust. Metrics connectors feed into performance snapshots; audience-specific skills generate tailored narratives.

## Core Architecture

### Metrics Ingestion

Connectors for metrics data:

- **Metabase**: Dashboards, saved queries, metrics definitions
- **PostHog**: Product analytics, event tracking, feature flags
- **Google Analytics**: Traffic, conversion, user acquisition
- **Klaviyo**: Email metrics, list engagement
- **NetXD**: Financial metrics, revenue tracking
- **Sardine**: Fraud detection rates, decision counts
- **Socure**: Identity verification metrics

### Normalization Layer

Every metric snapshot carries:

```json
{
  "metric_id": "uuid",
  "metric_name": "daily_active_users",
  "source_system": "posthog",
  "source_object_id": "event_id",
  "value": 42500,
  "unit": "count",
  "period": "2026-04-17",
  "data_trust_score": 0.95,
  "interpretation_trust_score": 0.88,
  "owner": "product-team@dreamfi.com",
  "definition": "Unique users performing any action on the platform",
  "confidence_score": 0.92,
  "last_synced_at": "2026-04-17T14:30:00Z"
}
```

### Trust Model

**Data Trust** (0–1):

- Freshness: Is the metric recent enough? (based on last synced)
- Consistency: Do different sources agree?
- Definition completeness: Is the metric well-defined?
- Anomaly status: Are there unexplained spikes/drops?

**Interpretation Trust** (0–1):

- Passes audience-specific skill eval (e.g., `newsletter_headline` for exec summary)
- Clarity of the interpretation
- Actionability (does it lead to decisions?)
- Correct structure (headline + body + next action)

**Overall Confidence** = Data Trust × Interpretation Trust

### Audience-to-Skill Mapping

| Audience      | Narrative Skill       | Purpose                          |
| ------------- | --------------------- | -------------------------------- |
| Internal team | `meeting_summary`     | Weekly sync format               |
| Executives    | `newsletter_headline` | Subject line + 1-line preview    |
| External      | `product_description` | Launch narrative (100–200 words) |
| Investors     | Custom skill          | TBD with finance                 |

## Service Structure

```
services/metrics/
├── README.md
├── src/
│   ├── catalog/
│   │   └── metric_catalog.ts
│   ├── connectors/
│   │   ├── metabase_adapter.ts
│   │   ├── posthog_adapter.ts
│   │   ├── ga_adapter.ts
│   │   ├── klaviyo_adapter.ts
│   │   ├── netxd_adapter.ts
│   │   ├── sardine_adapter.ts
│   │   └── socure_adapter.ts
│   ├── normalize/
│   │   ├── normalize_org_id.ts
│   │   ├── normalize_funnel_stage.ts
│   │   ├── normalize_fraud_decision.ts
│   │   └── normalize_date_grain.ts
│   ├── snapshots/
│   │   └── create_snapshot.ts
│   ├── interpretation/
│   │   ├── render_internal_summary.ts
│   │   ├── render_exec_subject.ts
│   │   └── render_product_description.ts
│   ├── trust/
│   │   └── score_metric_trust.ts
│   └── index.ts
└── tests/
    ├── unit/
    │   ├── test_metric_catalog.ts
    │   ├── test_normalize_org_id.ts
    │   └── test_score_metric_trust.ts
    └── integration/
        ├── test_snapshot_generation.ts
        ├── test_internal_summary_render.ts
        ├── test_exec_subject_render.ts
        └── test_product_summary_render.ts
```

## Key Workflows

### 1. Weekly Reporting Workflow

1. Create snapshot of all active metrics for past week
2. Score data trust for each metric
3. Generate internal summary using `meeting_summary` skill
4. Generate exec subject using `newsletter_headline` skill
5. Score interpretation trust for each narrative
6. Publish narratives only if both trusts > threshold (0.7)
7. Escalate low-trust metrics to owners

### 2. Event-Based Reporting

On significant events (launch, milestone, anomaly):

1. Fetch relevant metrics
2. Generate product narrative using `product_description` skill
3. Score trust
4. Publish to Confluence, Dragonboat, external channels

## Acceptance Criteria

- [ ] Every metric has source-of-truth and owner documented
- [ ] Snapshots use normalized identifiers across connectors
- [ ] Internal summary matches `meeting_summary` constraints
- [ ] Exec subject matches `newsletter_headline` constraints
- [ ] Product summary matches `product_description` constraints
- [ ] Trust scores published alongside narratives
- [ ] Low-trust metrics escalated to owners with resolution path

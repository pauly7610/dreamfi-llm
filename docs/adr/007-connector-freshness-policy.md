# ADR-007: Connector Freshness Policy

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

DreamFi ingests data from 11 external connectors. Each connector syncs at different intervals (webhook-driven near-real-time for Jira, daily batch for GA, polling every 30-60 minutes for others). Generated artifacts depend on this ingested data as source context. If source data is stale, the generated artifact may contain outdated information.

The platform needs a consistent way to:
1. Measure how fresh each synced object is.
2. Propagate freshness signals to generated artifacts that cite those objects.
3. Use freshness as an input to confidence scoring (ADR-005).
4. Block publishing when sources are too stale (ADR-006).

Without a freshness policy, the system has no way to distinguish between an artifact backed by data synced 5 minutes ago and one backed by data synced 3 weeks ago.

---

## Decision

**All synced objects carry freshness metadata. Low freshness lowers confidence and can block publishing.**

### Required Freshness Metadata (per synced object)

Every object written to the canonical DB by a connector must include:

| Field               | Type       | Description                                          |
|---------------------|------------|------------------------------------------------------|
| `last_synced_at`    | timestamp  | When this object was last successfully synced        |
| `source_updated_at` | timestamp  | When the object was last modified in the source system |
| `freshness_score`   | float      | Computed score, 0.0 to 1.0                           |

### Freshness Scoring Formula

```
hours_since_sync = (now - last_synced_at) in hours
max_stale_hours = connector-specific constant (see table below)

base_decay = hours_since_sync / max_stale_hours

# If the source object has not changed since last sync, decay slower
if source_updated_at <= last_synced_at:
    decay_rate = 0.5
else:
    decay_rate = 1.0

freshness_score = max(0.0, 1.0 - (base_decay * decay_rate))
```

### Max Stale Hours Per Connector

| Connector    | Max Stale Hours | Rationale                                      |
|--------------|----------------|-------------------------------------------------|
| Jira         | 24             | Active project data, webhook-supplemented       |
| Dragonboat   | 48             | Strategic data, changes less frequently          |
| Lucidchart   | 72             | Diagrams change infrequently                     |
| Confluence   | 24             | Active documentation, webhook-supplemented       |
| Metabase     | 48             | Dashboard/query metadata, moderate change rate   |
| PostHog      | 12             | Event data is time-sensitive                     |
| GA           | 48             | Daily batch pull, inherent processing lag        |
| Klaviyo      | 24             | Campaign data, webhook-supplemented              |
| NetXD        | 48             | Transaction data, moderate update frequency      |
| Sardine      | 12             | Fraud signals are time-critical                  |
| Socure       | 72             | Verification results rarely change after decision|

### Freshness Propagation

When an artifact cites source entities, the artifact's effective freshness is the minimum freshness across all cited entities:

```
artifact_freshness = min(entity.freshness_score for entity in artifact.cited_entities)
```

This minimum ensures that one stale source is not hidden by many fresh sources.

### Freshness Thresholds

| Freshness Range | Label    | Effect on Confidence                  |
|-----------------|----------|---------------------------------------|
| 0.70 - 1.00    | Fresh    | Full weight in confidence formula     |
| 0.30 - 0.69    | Aging    | Reduced confidence, warning displayed |
| 0.00 - 0.29    | Stale    | Hard gate: publish blocked            |

### Freshness Refresh Triggers

Freshness scores are recomputed:
1. **On sync:** When a connector successfully syncs an object, freshness is recalculated with updated `last_synced_at`.
2. **On query:** When an object is retrieved for generator context, freshness is recomputed using current time.
3. **On publish check:** When an artifact passes through the publishing pipeline, all cited entities' freshness is recomputed.

Freshness is not statically stored and forgotten -- it is a function of time and is always evaluated relative to "now."

---

## Alternatives Considered

### No freshness tracking (trust all synced data)

**Pros:** Simplest possible approach. No freshness computation, no decay, no thresholds. All synced data is treated as current.

**Cons:** A connector could fail silently for days, and artifacts would continue to be generated and published using stale data. There is no signal that source quality has degraded.

**Rejected because:** Connector failures happen. Network issues, API rate limits, auth token expiry, and service outages all cause sync gaps. Without freshness tracking, the system has no way to detect or react to these gaps.

### Boolean fresh/stale (no continuous score)

**Pros:** Simpler than a continuous score. Each object is either fresh (synced within max_stale_hours) or stale (not synced within max_stale_hours).

**Cons:** Loses nuance. An object synced 1 hour ago and one synced 23 hours ago (with max_stale_hours = 24) are both "fresh" but have very different reliability. The continuous score allows the confidence model (ADR-005) to weight freshness proportionally.

**Rejected because:** The confidence model benefits from a continuous signal. Binary fresh/stale forces a hard threshold that may be too aggressive or too permissive depending on context.

### Source-system-reported freshness

**Pros:** Let the source system tell us how fresh its data is. No need for our own computation.

**Cons:** Most source systems do not provide freshness metadata. They report `updated_at` but not "how reliable is this data right now." Our freshness score captures a different dimension: how recently did we verify the source state, not when the source last changed.

**Rejected because:** Our freshness score measures sync recency (our view of the source), not source modification recency (which is a separate signal captured by `source_updated_at`).

---

## Tradeoffs

**Accepted tradeoffs:**
- **Freshness computation adds overhead.** Every query and publish check must recompute freshness. This is a lightweight computation (two timestamp comparisons and arithmetic) but it adds to the query path.
- **Min-freshness is conservative.** One stale source among many fresh ones drags down the entire artifact's freshness. This may block publishing for artifacts that are mostly well-sourced.
- **Max stale hours are per-connector, not per-entity-type.** A Jira epic and a Jira bug share the same max stale hours, even though epics change less frequently than bugs.

**Mitigated by:**
- Freshness computation is O(1) per entity -- trivial overhead.
- The stale threshold (0.3) is low, meaning only severely stale sources trigger the hard gate.
- Per-entity-type max stale hours can be added later as a refinement. Per-connector is a reasonable starting point.

---

## Consequences

1. Every canonical entity has `last_synced_at`, `source_updated_at`, and `freshness_score` columns.
2. Connectors must update `last_synced_at` on every successful sync, even if the source object has not changed (this proves we checked).
3. The confidence model (ADR-005) uses `freshness_score` as a weighted input and as a hard-gate check.
4. Connector health is visible through aggregate freshness dashboards: if a connector's average freshness is declining, the connector is likely failing or falling behind.
5. Freshness alerts can be set up: if average freshness for a connector drops below 0.5, trigger an ops alert.
6. Historical freshness trends (stored as time-series snapshots) enable debugging of past publishing decisions.

---

## Rollback Plan

1. **Disable freshness gating.** Set all freshness thresholds to 0.0, effectively making freshness advisory-only. The scores are still computed and displayed but never block publishing. This is a configuration change.
2. **Increase max stale hours.** If a connector is consistently triggering staleness due to slow sync, increase its max_stale_hours to match operational reality. This is a per-connector configuration change.
3. **Switch to boolean fresh/stale.** Replace the continuous formula with a simple time-window check. Entities synced within max_stale_hours are fresh (1.0), otherwise stale (0.0). This simplifies the model at the cost of nuance.
4. **Remove freshness from confidence formula.** Set w2 = 0.0 in the confidence model. Freshness is tracked but does not affect confidence scores. Other weights would need rebalancing.

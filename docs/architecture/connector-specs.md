# Connector Specifications

**Status:** Living document
**Last updated:** 2026-04-17

This document defines the auth, sync method, object model, and freshness strategy for all 11 external connectors integrated into DreamFi's Knowledge Hub.

---

## Shared Required Metadata Fields

Every connector-synced entity must carry these fields in the normalized output:

| Field                          | Type               | Required | Purpose                                                         |
| ------------------------------ | ------------------ | -------- | --------------------------------------------------------------- |
| `source_system`                | string             | Yes      | Canonical identifier ('jira', 'dragonboat', 'confluence', etc.) |
| `source_object_id`             | string             | Yes      | External system's unique ID for this object                     |
| `source_url`                   | string             | No       | Direct link to the object in the external system                |
| `last_synced_at`               | ISO-8601 timestamp | Yes      | When this object was last fetched                               |
| `freshness_score`              | 0–1 decimal        | Yes      | Confidence in data freshness (1 = fresh, 0 = stale)             |
| `eligible_skill_families_json` | JSON array         | Yes      | Which skill families can use this entity as context             |

---

## Connector Implementations

### 1. Jira (Atlassian)

| Property            | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Auth method**     | OAuth 2.0 (3LO) via Atlassian Connect               |
| **Sync method**     | Webhook (primary) + polling fallback (every 15 min) |
| **Max stale hours** | 24                                                  |

### Object Model

| Source Object | Canonical Table | Notes                             |
| ------------- | --------------- | --------------------------------- |
| Issue         | core_entities   | Epic, Story, Task, Bug, Sub-task  |
| Project       | core_entities   | Container entity                  |
| Sprint        | core_entities   | Time-boxed iteration              |
| Component     | core_entities   | Logical grouping                  |
| Issue Link    | relationships   | blocks, relates_to, duplicates    |
| Comment       | citations       | Linked to parent issue            |
| Attachment    | citations       | Stored in object store, ref in DB |

### Normalized Field Mapping

| Jira Field         | Canonical Field    |
| ------------------ | ------------------ |
| key                | source_object_id   |
| summary            | entity_name        |
| description        | entity_description |
| status.name        | entity_status      |
| priority.name      | entity_priority    |
| issuetype.name     | entity_type        |
| assignee.accountId | owner_id           |
| updated            | source_updated_at  |
| project.key        | parent_entity_id   |
| labels             | tags_json          |
| fixVersions        | version_refs_json  |

### Freshness Strategy

Webhooks provide near-real-time updates for issue changes. Polling runs every 15 minutes as fallback, querying `updated >= last_synced_at`. Full reconciliation runs nightly.

---

## 2. Dragonboat

| Property            | Value                  |
| ------------------- | ---------------------- |
| **Auth method**     | API Key (header-based) |
| **Sync method**     | Polling (every 30 min) |
| **Max stale hours** | 48                     |

### Object Model

| Source Object   | Canonical Table | Notes                 |
| --------------- | --------------- | --------------------- |
| Initiative      | core_entities   | Strategic initiative  |
| Feature         | core_entities   | Tactical feature      |
| Objective       | core_entities   | OKR objective         |
| Key Result      | core_entities   | OKR key result        |
| Initiative Link | relationships   | parent_of, depends_on |
| Note            | citations       | Attached commentary   |

### Normalized Field Mapping

| Dragonboat Field | Canonical Field    |
| ---------------- | ------------------ |
| id               | source_object_id   |
| name             | entity_name        |
| description      | entity_description |
| status           | entity_status      |
| priority         | entity_priority    |
| type             | entity_type        |
| owner.id         | owner_id           |
| updatedAt        | source_updated_at  |
| parentId         | parent_entity_id   |
| tags             | tags_json          |
| timeframe        | timeframe_json     |

### Freshness Strategy

Polling every 30 minutes using `updatedAt` filter. No webhook support. Full reconciliation runs daily.

---

## 3. Lucidchart

| Property            | Value                  |
| ------------------- | ---------------------- |
| **Auth method**     | OAuth 2.0              |
| **Sync method**     | Polling (every 60 min) |
| **Max stale hours** | 72                     |

### Object Model

| Source Object    | Canonical Table | Notes                                  |
| ---------------- | --------------- | -------------------------------------- |
| Document         | core_entities   | Diagram container                      |
| Page             | core_entities   | Individual diagram page                |
| Shape/Element    | core_entities   | Diagram elements (optional detail)     |
| Document Link    | relationships   | Cross-document references              |
| Export (PNG/SVG) | citations       | Rendered snapshots stored in obj store |

### Normalized Field Mapping

| Lucidchart Field | Canonical Field    |
| ---------------- | ------------------ |
| documentId       | source_object_id   |
| title            | entity_name        |
| description      | entity_description |
| editedDate       | source_updated_at  |
| owner.id         | owner_id           |
| folder.id        | parent_entity_id   |
| type             | entity_type        |

### Freshness Strategy

Polling every 60 minutes via document listing endpoint filtered by `editedDate`. Diagram exports are re-rendered on change detection. Diagrams change infrequently so longer max stale window is acceptable.

---

## 4. Confluence

| Property            | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Auth method**     | OAuth 2.0 (3LO) via Atlassian Connect               |
| **Sync method**     | Webhook (primary) + polling fallback (every 15 min) |
| **Max stale hours** | 24                                                  |

### Object Model

| Source Object | Canonical Table | Notes                          |
| ------------- | --------------- | ------------------------------ |
| Page          | core_entities   | Wiki page                      |
| Blog Post     | core_entities   | Blog content                   |
| Space         | core_entities   | Container                      |
| Attachment    | citations       | Files attached to pages        |
| Comment       | citations       | Inline and page-level comments |
| Page Link     | relationships   | Parent/child, cross-references |

### Normalized Field Mapping

| Confluence Field   | Canonical Field    |
| ------------------ | ------------------ |
| id                 | source_object_id   |
| title              | entity_name        |
| body.storage.value | entity_description |
| status             | entity_status      |
| type               | entity_type        |
| version.when       | source_updated_at  |
| space.key          | parent_entity_id   |
| metadata.labels    | tags_json          |

### Freshness Strategy

Webhooks for page create/update/delete events. Polling fallback every 15 minutes using CQL `lastModified` filter. Full space reconciliation runs nightly. Confluence is also a publish target -- published artifacts get written back as pages.

---

## 5. Metabase

| Property            | Value                    |
| ------------------- | ------------------------ |
| **Auth method**     | API Key or Session Token |
| **Sync method**     | Polling (every 60 min)   |
| **Max stale hours** | 48                       |

### Object Model

| Source Object    | Canonical Table | Notes                                 |
| ---------------- | --------------- | ------------------------------------- |
| Question (Query) | core_entities   | Saved question / query                |
| Dashboard        | core_entities   | Dashboard container                   |
| Card             | core_entities   | Dashboard card / visualization        |
| Collection       | core_entities   | Organizational container              |
| Query Result     | citations       | Snapshot of query output at sync time |

### Normalized Field Mapping

| Metabase Field | Canonical Field    |
| -------------- | ------------------ |
| id             | source_object_id   |
| name           | entity_name        |
| description    | entity_description |
| updated_at     | source_updated_at  |
| creator.id     | owner_id           |
| collection.id  | parent_entity_id   |
| entity_type    | entity_type        |

### Freshness Strategy

Polling every 60 minutes. Dashboard and question metadata checked for updates. Query results are re-executed and snapshot diffs stored when underlying data changes. Result snapshots feed Phase 4 metrics reporting.

---

## 6. PostHog

| Property            | Value                                        |
| ------------------- | -------------------------------------------- |
| **Auth method**     | API Key (Personal or Project)                |
| **Sync method**     | Polling (every 30 min) + webhook for actions |
| **Max stale hours** | 12                                           |

### Object Model

| Source Object    | Canonical Table | Notes                           |
| ---------------- | --------------- | ------------------------------- |
| Event Definition | core_entities   | Custom event schema             |
| Action           | core_entities   | Compound event definition       |
| Insight          | core_entities   | Saved analytics query           |
| Dashboard        | core_entities   | Dashboard container             |
| Feature Flag     | core_entities   | Flag definition and status      |
| Cohort           | core_entities   | User segment definition         |
| Event Data       | citations       | Aggregated event counts/metrics |

### Normalized Field Mapping

| PostHog Field    | Canonical Field    |
| ---------------- | ------------------ |
| id               | source_object_id   |
| name             | entity_name        |
| description      | entity_description |
| last_modified_at | source_updated_at  |
| created_by.id    | owner_id           |
| type             | entity_type        |

### Freshness Strategy

Polling every 30 minutes for insight and dashboard updates. Webhooks fire for action triggers. Event data is aggregated in 1-hour windows. Short max stale window (12h) because event data is time-sensitive for Phase 4 reporting.

---

## 7. Google Analytics (GA)

| Property            | Value                               |
| ------------------- | ----------------------------------- |
| **Auth method**     | OAuth 2.0 (Service Account or User) |
| **Sync method**     | Batch (daily pull + on-demand)      |
| **Max stale hours** | 48                                  |

### Object Model

| Source Object    | Canonical Table | Notes                       |
| ---------------- | --------------- | --------------------------- |
| Property         | core_entities   | GA4 property                |
| Data Stream      | core_entities   | Web/app stream              |
| Custom Dimension | core_entities   | Custom dimension definition |
| Report Snapshot  | citations       | Daily metric snapshots      |
| Audience         | core_entities   | Audience segment definition |

### Normalized Field Mapping

| GA Field    | Canonical Field    |
| ----------- | ------------------ |
| propertyId  | source_object_id   |
| displayName | entity_name        |
| description | entity_description |
| updateTime  | source_updated_at  |
| account     | parent_entity_id   |
| type        | entity_type        |

### Freshness Strategy

Batch pull runs daily at 06:00 UTC (GA data has 24-48h processing lag). On-demand pulls available for real-time reporting needs. Report snapshots are versioned by date.

---

## 8. Klaviyo

| Property            | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Auth method**     | API Key (Private Key)                               |
| **Sync method**     | Webhook (primary) + polling fallback (every 30 min) |
| **Max stale hours** | 24                                                  |

### Object Model

| Source Object | Canonical Table | Notes                        |
| ------------- | --------------- | ---------------------------- |
| Campaign      | core_entities   | Email/SMS campaign           |
| Flow          | core_entities   | Automated flow               |
| List          | core_entities   | Subscriber list              |
| Segment       | core_entities   | Dynamic segment              |
| Template      | core_entities   | Email template               |
| Metric        | citations       | Campaign performance metrics |
| Event         | citations       | Profile activity events      |

### Normalized Field Mapping

| Klaviyo Field | Canonical Field   |
| ------------- | ----------------- |
| id            | source_object_id  |
| name          | entity_name       |
| status        | entity_status     |
| updated       | source_updated_at |
| type          | entity_type       |
| tags          | tags_json         |

### Freshness Strategy

Webhooks for campaign sends, flow triggers, and list changes. Polling every 30 minutes for metric updates. Campaign metrics aggregate over 24h windows for final delivery stats.

---

## 9. NetXD

| Property            | Value                    |
| ------------------- | ------------------------ |
| **Auth method**     | API Key + HMAC signature |
| **Sync method**     | Polling (every 60 min)   |
| **Max stale hours** | 48                       |

### Object Model

| Source Object | Canonical Table | Notes                        |
| ------------- | --------------- | ---------------------------- |
| Transaction   | core_entities   | Financial transaction record |
| Account       | core_entities   | User account                 |
| Rule          | core_entities   | Compliance/fraud rule        |
| Alert         | core_entities   | Triggered alert              |
| Report        | citations       | Compliance report snapshot   |

### Normalized Field Mapping

| NetXD Field   | Canonical Field    |
| ------------- | ------------------ |
| transactionId | source_object_id   |
| label         | entity_name        |
| details       | entity_description |
| status        | entity_status      |
| updatedAt     | source_updated_at  |
| accountId     | parent_entity_id   |
| type          | entity_type        |

### Freshness Strategy

Polling every 60 minutes. Transaction and alert data synced with `updatedAt` filter. Compliance reports are pulled as batch snapshots. Data sensitivity requires audit logging of every sync operation.

---

## 10. Sardine

| Property            | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Auth method**     | API Key + Client Secret                             |
| **Sync method**     | Webhook (primary) + polling fallback (every 30 min) |
| **Max stale hours** | 12                                                  |

### Object Model

| Source Object | Canonical Table | Notes                          |
| ------------- | --------------- | ------------------------------ |
| Session       | core_entities   | User session with risk signals |
| Rule          | core_entities   | Fraud detection rule           |
| Case          | core_entities   | Investigation case             |
| Signal        | citations       | Individual risk signal         |
| Score         | citations       | Composite risk score snapshot  |

### Normalized Field Mapping

| Sardine Field | Canonical Field   |
| ------------- | ----------------- |
| sessionId     | source_object_id  |
| label         | entity_name       |
| riskLevel     | entity_status     |
| updatedAt     | source_updated_at |
| customerId    | parent_entity_id  |
| type          | entity_type       |
| signals       | metadata_json     |

### Freshness Strategy

Webhooks for real-time session and case updates. Polling every 30 minutes as fallback. Short max stale window (12h) because fraud signals are time-critical. Score snapshots versioned per session.

---

## 11. Socure

| Property            | Value                              |
| ------------------- | ---------------------------------- |
| **Auth method**     | API Key (header-based)             |
| **Sync method**     | Polling (every 60 min) + on-demand |
| **Max stale hours** | 72                                 |

### Object Model

| Source Object       | Canonical Table | Notes                           |
| ------------------- | --------------- | ------------------------------- |
| Verification Result | core_entities   | ID verification outcome         |
| Module Score        | core_entities   | Per-module risk score           |
| Decision            | core_entities   | Accept/review/reject decision   |
| Document            | citations       | Submitted document metadata     |
| Reason Code         | citations       | Explanation codes for decisions |

### Normalized Field Mapping

| Socure Field | Canonical Field   |
| ------------ | ----------------- |
| referenceId  | source_object_id  |
| customerName | entity_name       |
| decision     | entity_status     |
| updatedAt    | source_updated_at |
| customerId   | parent_entity_id  |
| type         | entity_type       |
| modules      | metadata_json     |

### Freshness Strategy

Polling every 60 minutes for updated verification results. On-demand sync triggered when new verifications are requested. Longer max stale window (72h) because verification results change infrequently after initial decision. Reason codes are immutable once generated.

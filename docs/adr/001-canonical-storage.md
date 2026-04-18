# ADR-001: Canonical Storage Architecture

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

DreamFi ingests data from 11 external connectors (Jira, Dragonboat, Lucidchart, Confluence, Metabase, PostHog, GA, Klaviyo, NetXD, Sardine, Socure). Each connector produces data in its own schema and format. The platform needs a canonical storage layer that:

1. Normalizes heterogeneous data into a consistent schema for cross-source queries.
2. Preserves raw payloads for auditability and reprocessing.
3. Supports the skill registry, evaluation rounds, prompt versioning, and gold example storage.
4. Provides full-text and embeddings-based search over canonical entities.
5. Handles relational integrity (entities reference other entities, citations reference entities, eval outputs reference rounds).

The canonical schema includes: `core_entities`, `relationships`, `citations`, `skill_registry`, `prompt_versions`, `evaluation_criteria_catalog`, `test_input_registry`, `evaluation_rounds`, `evaluation_outputs`, `gold_example_registry`, `skill_failure_patterns`.

---

## Decision

Use **PostgreSQL** as the primary database for all normalized/canonical state, and an **S3-compatible object store** for raw connector payloads and large binary attachments.

### PostgreSQL responsibilities:
- All canonical schema tables (core_entities through skill_failure_patterns).
- Full-text search via tsvector/tsquery.
- Embeddings search via pgvector extension.
- Transactional integrity for evaluation rounds (a round's outputs and score updates are atomic).
- Job queue via pg-boss (Postgres-backed, no separate Redis dependency).

### Object store responsibilities:
- Raw API response payloads from connectors (JSON blobs).
- Webhook request bodies.
- Binary attachments (Lucidchart exports, Confluence attachments, document uploads).
- Raw payloads are referenced by URI from canonical DB records.

---

## Alternatives Considered

### MongoDB

**Pros:** Flexible schema for heterogeneous connector data. Native JSON storage. Good for rapid prototyping.

**Cons:** Weaker relational integrity -- the canonical schema has numerous foreign key relationships (eval_outputs -> rounds -> prompt_versions -> skill_registry) that benefit from enforced constraints. No native full-text search comparable to Postgres tsvector. No native vector search (would require Atlas Vector Search or a separate service). Transactions across collections are supported but less mature. Team has stronger Postgres expertise.

**Rejected because:** The canonical schema is inherently relational. Enforced foreign keys prevent orphaned eval outputs, broken citation chains, and prompt version inconsistencies. MongoDB's flexibility is unnecessary here since the schema is well-defined.

### SQLite

**Pros:** Zero-config, embedded, fast for single-writer workloads. Good for development.

**Cons:** Single-writer limitation is a hard blocker for concurrent connector syncs and eval rounds. No pgvector equivalent for embeddings search. No built-in replication or backup tooling for production. Limited extension ecosystem.

**Rejected because:** Concurrent writes from 11 connectors plus eval engine require multi-writer support. Production operational requirements (backup, replication, monitoring) favor a client-server database.

### Pure Object Store (S3 + query layer like Athena)

**Pros:** Infinitely scalable storage. Cheap at rest. Good for append-only event streams.

**Cons:** No transactional guarantees for multi-table updates (e.g., promoting a prompt version while recording eval results). Query latency measured in seconds, not milliseconds. No foreign key enforcement. Requires a separate query engine. Operational complexity for a small team.

**Rejected because:** The eval loop requires sub-second reads and transactional multi-table writes. An object store query layer adds latency and complexity without benefit for this workload.

---

## Tradeoffs

**Accepted tradeoffs:**
- Postgres requires capacity planning and operational attention (vacuuming, connection pooling, index maintenance) that simpler stores do not.
- Dual storage (Postgres + object store) means two systems to operate and monitor.
- pgvector adds extension dependency and requires Postgres builds that include it.

**Mitigated by:**
- Managed Postgres services (RDS, Cloud SQL) handle operational burden.
- Object store is operationally simple (S3 is effectively zero-ops).
- pgvector is widely supported in managed Postgres offerings.

---

## Consequences

1. All connector normalizers write to a shared Postgres schema. Schema migrations must be coordinated.
2. Raw payloads are stored by URI reference -- the canonical DB never stores large blobs directly.
3. The eval engine can use database transactions to atomically record round results and update prompt version status.
4. Search (full-text + vector) is co-located with data, avoiding cross-service latency.
5. pg-boss provides job scheduling without introducing Redis as an additional dependency.
6. Schema changes to canonical tables require migration scripts and backwards-compatibility planning.

---

## Rollback Plan

If Postgres proves insufficient (unlikely given the workload profile):

1. The canonical schema is expressed as TypeScript interfaces. Swapping the storage backend requires implementing a new repository layer against the same interfaces.
2. Raw payloads in the object store are independent and unaffected.
3. Data can be exported from Postgres as JSON and loaded into an alternative store.
4. The pgvector dependency can be replaced with a standalone vector store (Qdrant, Pinecone) by updating the search service layer.
5. pg-boss can be replaced with a Redis-backed queue (BullMQ) if job scheduling needs change.

Estimated rollback effort: 2-3 weeks for a full storage backend swap, assuming repository interfaces are maintained.

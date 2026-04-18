# ADR-002: Search Architecture

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** DreamFi Engineering

---

## Context

The skill registry and generators need to retrieve relevant context from the canonical knowledge hub. Retrieval quality directly affects generation quality -- if a skill cannot find the right product entities, feature specs, or compliance rules, the generated output will be incomplete or inaccurate.

Retrieval must handle two distinct query types:

1. **Keyword-exact queries:** "Find all entities with status DEPRECATED in project PAYMENTS" -- requires precise field matching.
2. **Semantic queries:** "Find product descriptions related to fraud prevention for onboarding flows" -- requires understanding meaning, not just keyword overlap.

Neither pure keyword search nor pure vector search handles both cases well.

---

## Decision

Use **hybrid full-text + embeddings search**, both implemented within PostgreSQL using native extensions.

### Full-text search: Postgres tsvector/tsquery
- Index `entity_name`, `entity_description`, and `tags_json` fields as tsvector columns.
- Support exact phrase matching, boolean operators, and prefix matching.
- Handles keyword-exact queries with high precision.

### Embeddings search: pgvector
- Embed `entity_description` and `entity_name` (concatenated) using a text embedding model (e.g., text-embedding-3-small).
- Store embeddings in a vector column on `core_entities`.
- Use cosine similarity for nearest-neighbor retrieval.
- Handles semantic queries where keyword overlap is low.

### Hybrid ranking: Reciprocal Rank Fusion (RRF)

For each query, both search methods run in parallel and results are combined:

```
rrf_score(doc) = 1/(k + rank_fulltext(doc)) + 1/(k + rank_vector(doc))
```

Where `k` is a constant (default 60) that controls the influence of rank position. Documents appearing in both result sets get boosted. Documents appearing in only one set are still included but ranked lower.

### Freshness weighting

Search results are post-filtered by freshness. Documents with `freshness_score < 0.3` are excluded from generator context by default. Documents with `freshness_score >= 0.3` have their RRF score multiplied by `freshness_score` to prefer fresh sources.

---

## Alternatives Considered

### Pure keyword search (tsvector only)

**Pros:** Simple, fast, no embedding model dependency. Well-understood relevance tuning.

**Cons:** Misses semantic matches. A query for "fraud detection" will not find an entity described as "transaction risk scoring" unless keywords overlap. Generators would receive incomplete context, degrading output quality.

**Rejected because:** Semantic retrieval is essential for skills like `product_description` and `agent_system_prompt` that need to gather related context across different naming conventions.

### Pure vector search (pgvector only)

**Pros:** Strong semantic matching. Single retrieval path.

**Cons:** Poor at exact matches. A search for entity status "DEPRECATED" would not reliably filter by that exact value. Embedding models can conflate unrelated concepts with similar surface-level descriptions. No boolean operators.

**Rejected because:** Many queries require exact field matching (status filters, project filters, tag matching). Vector search alone cannot provide the precision needed for hard-gate checks.

### Elasticsearch / OpenSearch

**Pros:** Purpose-built for search. Rich query DSL. Built-in hybrid search capabilities. Mature relevance tuning.

**Cons:** Introduces a separate service to operate, scale, and keep in sync with Postgres. Data must be dual-written or change-data-captured from Postgres to Elasticsearch. Added operational burden for a small team. Consistency lag between Postgres and Elasticsearch.

**Rejected because:** The data volume (11 connectors, thousands of entities, not millions) does not justify a separate search cluster. Postgres tsvector + pgvector provide adequate capability at this scale. Co-location with the canonical DB eliminates consistency concerns.

---

## Tradeoffs

**Accepted tradeoffs:**
- Postgres-native search is less feature-rich than Elasticsearch (no fuzzy matching, no sophisticated analyzers, no per-field boosting DSL).
- Embedding model adds latency to indexing (each entity must be embedded on insert/update).
- pgvector HNSW indexes consume memory proportional to the number of embedded entities.
- Hybrid ranking adds complexity compared to a single retrieval path.

**Mitigated by:**
- At current scale (thousands of entities, not millions), Postgres search performance is more than adequate.
- Embedding is done asynchronously on connector sync, not on query path.
- HNSW memory usage is manageable for the expected entity count (< 100K entities).
- RRF is a well-understood, simple fusion method with minimal tuning parameters.

---

## Consequences

1. Every `core_entities` row has a tsvector column (auto-updated via trigger) and a vector column (updated on insert/update via async job).
2. The embedding model is a runtime dependency. Model version changes require re-embedding all entities.
3. Search quality can be evaluated using the same eval framework -- test queries with expected results, binary pass/fail on result relevance.
4. Freshness filtering is applied at the search layer, meaning stale entities are proactively excluded from generator context rather than caught downstream.
5. If search quality needs improve beyond what Postgres can provide, migrating to Elasticsearch is straightforward since the search interface is abstracted behind a service layer.

---

## Rollback Plan

1. Disable vector search and fall back to full-text only. This is a configuration change, not a code change. Generation quality will degrade for semantic queries but the system remains functional.
2. If full Elasticsearch migration is needed: implement a change-data-capture pipeline from Postgres to Elasticsearch, update the search service to query Elasticsearch instead of Postgres, and deprecate the pgvector columns.
3. Estimated rollback to full-text only: 1 hour (config change).
4. Estimated migration to Elasticsearch: 2-3 weeks (new service, CDC pipeline, relevance tuning).

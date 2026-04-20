# ADR-009: Onyx as the knowledge substrate

Status: Active
Supersedes: ADR-001 (canonical storage), ADR-002 (search architecture), ADR-007 (connector freshness)

## Context

Originally DreamFi maintained its own connector, storage, search, and freshness
pipelines. Reinventing that layer drained engineering capacity from the only
thing that makes DreamFi differentiated: the locked eval + promote/revert loop
over named skills.

## Decision

DreamFi uses [Onyx](https://github.com/onyx-dot-app/onyx) as the knowledge
substrate. Onyx owns:

- Connector ingestion (Jira, Confluence, GDrive, Slack, etc.)
- Document normalization, chunking, embedding
- Hybrid search (Vespa vector + BM25)
- Permissioning, SSO, RBAC, audit log
- LLM provider abstraction
- Chat / agent / action / MCP surface

DreamFi keeps only a thin skill-gated generation and evaluation layer. All
retrieval happens through `dreamfi.onyx.client.OnyxClient`. No direct
connector code lives in DreamFi.

## Consequences

- ADR-001 canonical storage is retired: Onyx is the source of truth.
- ADR-002 search architecture is retired: Onyx admin search + chat persona.
- ADR-007 freshness is retired: Onyx tracks `updated_at` per document; DreamFi
  derives freshness from citations returned during chat.
- Dragonboat and other unsupported connectors become either an Onyx custom
  connector or an ingestion-API push (see ADR-010 + Phase 8 of the plan).

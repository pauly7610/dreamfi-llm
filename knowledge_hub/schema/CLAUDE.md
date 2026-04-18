# DreamFi Knowledge Hub -- Wiki Schema Definition

This file is the single source of truth for the structure, conventions,
and rules that govern every page in the wiki.  All tooling (ingest, query,
lint) reads this file at runtime.  **Do not rename or relocate it.**

---

## 1. Folder Structure

All wiki pages live under `knowledge_hub/wiki/` in the following
sub-folders.  Every markdown file must be in exactly one of these
folders.

```
knowledge_hub/wiki/
  features/        # One page per product feature or capability
  flows/           # One page per end-to-end user or system flow
  concepts/        # Domain concepts (KYC, fraud, activation, ledger, etc.)
  components/      # Internal system components / services / modules
  integrations/    # One page per external system or third-party service
  comparisons/     # Side-by-side comparison tables (vendors, approaches)
```

The root of `wiki/` also contains two special files:

| File         | Purpose                                       |
|------------- |-----------------------------------------------|
| `index.md`   | Master page index -- auto-maintained by tools |
| `log.md`     | Append-only change log of all wiki mutations  |

---

## 2. Page Types

### 2.1 Entity Pages  (`features/`, `flows/`)

One page per discrete feature or flow.  Examples:
`feature-kyc-flow.md`, `flow-onboarding.md`.

### 2.2 Concept Pages  (`concepts/`)

One page per domain concept that spans multiple features.
Examples: `concept-activation.md`, `concept-fraud-scoring.md`.

### 2.3 Component Pages  (`components/`)

One page per internal service, module, or architectural building block.
Examples: `component-ledger-service.md`, `component-auth-gateway.md`.

### 2.4 Integration Pages  (`integrations/`)

One page per external system.  Examples:
`integration-socure.md`, `integration-sardine.md`.

### 2.5 Comparison Tables  (`comparisons/`)

Side-by-side comparisons.  Examples:
`comparison-kyc-vendors.md`, `comparison-fraud-engines.md`.

---

## 3. Naming Conventions

| Rule | Detail |
|------|--------|
| Case | **lowercase-kebab-case** everywhere |
| Prefix | File name starts with its type prefix: `feature-`, `flow-`, `concept-`, `component-`, `integration-`, `comparison-` |
| Extension | `.md` |
| No spaces | Use hyphens, never underscores or spaces |
| Examples | `feature-direct-deposit.md`, `concept-kyc.md`, `integration-posthog.md` |

---

## 4. Required Sections per Page Type

Every page starts with YAML frontmatter fenced by `---`.

### 4.1 Frontmatter (all page types)

```yaml
---
title: "Human-readable Title"
type: feature | flow | concept | component | integration | comparison
status: draft | active | deprecated
last_updated: "YYYY-MM-DD"
sources:
  - "confluence:PAGE_ID or jira:ISSUE_KEY or file:path or url:..."
related_pages:
  - "[[concept-kyc]]"
  - "[[integration-socure]]"
tags:
  - kyc
  - onboarding
---
```

Required fields: `title`, `type`, `status`, `last_updated`, `sources`,
`related_pages`.

### 4.2 Body Sections -- Entity Pages (features / flows)

```markdown
## Overview
Brief 2-3 sentence description.

## How It Works
Step-by-step or numbered explanation.

## Key Rules / Business Logic
Bullet list of important constraints or rules.

## Dependencies
Which components, integrations, or concepts this relies on.

## Open Questions
Anything unresolved (remove section when empty).

## Sources
Inline citations: [Source Title](link or identifier).
```

### 4.3 Body Sections -- Concept Pages

```markdown
## Definition
What this concept means in the DreamFi context.

## Where It Appears
Which features and flows reference this concept.

## Rules & Constraints
Business rules, regulatory requirements, etc.

## Sources
```

### 4.4 Body Sections -- Component Pages

```markdown
## Overview
What this component does.

## Responsibilities
Bullet list of what it owns.

## Interfaces
APIs, events, data contracts.

## Dependencies
Upstream and downstream services.

## Sources
```

### 4.5 Body Sections -- Integration Pages

```markdown
## Overview
What this external system does and why DreamFi uses it.

## Configuration
Environment variables, API keys (names only, never values).

## API Usage
Which endpoints / methods DreamFi calls and why.

## Data Flow
What data goes in and comes out.

## Sources
```

### 4.6 Body Sections -- Comparison Pages

```markdown
## Overview
What is being compared and why.

## Comparison Table
| Criterion | Option A | Option B | ... |
|-----------|----------|----------|-----|
| ...       | ...      | ...      | ... |

## Recommendation
Summary of the preferred option and rationale.

## Sources
```

---

## 5. Cross-Referencing Rules

1. Use **wiki-links**: `[[page-name]]` (without folder prefix or `.md`).
   Example: `[[concept-kyc]]`, `[[integration-socure]]`.
2. Every page **must** link to at least **2** related pages in its
   `related_pages` frontmatter and/or in the body text.
3. Links should be bidirectional when possible -- if page A links to
   page B, page B should link back to page A.
4. The `related_pages` frontmatter field is the canonical list; body
   links are supplementary.

---

## 6. Source Citations

1. Every page **must** have at least one entry in its `sources`
   frontmatter list.
2. Source format: `<system>:<identifier>`.  Examples:
   - `confluence:12345678`
   - `jira:DF-1042`
   - `file:sources/meeting-notes-2025-03.md`
   - `url:https://docs.socure.com/guide/overview`
   - `manual:paul-2025-04-10` (manually authored, with author and date)
3. Body-level citations use standard markdown links:
   `[Source Title](system:identifier)`.

---

## 7. Maintenance Rules

| Rule | Detail |
|------|--------|
| Stale threshold | A page is **stale** if `last_updated` is more than **30 days** ago |
| Review cycle | Stale pages should be reviewed and either updated or marked `deprecated` |
| Deprecation | Set `status: deprecated` and add a note pointing to the replacement page |
| Deletion | Pages are never deleted; they are deprecated |

---

## 8. Linting Rules Checklist

The `lint.py` tool checks every page against these rules.  Severity
levels: **error** (must fix), **warning** (should fix), **info**
(nice to have).

| # | Rule | Severity |
|---|------|----------|
| L1 | Frontmatter exists and contains all required fields | error |
| L2 | `type` field matches the folder the file is in | error |
| L3 | File name follows naming conventions (prefix + kebab-case) | error |
| L4 | At least 2 entries in `related_pages` | warning |
| L5 | At least 1 entry in `sources` | warning |
| L6 | All `[[wiki-links]]` resolve to existing pages | error |
| L7 | Page is not stale (last_updated within 30 days) | warning |
| L8 | All required body sections for the page type are present | warning |
| L9 | No orphan pages (at least one other page links to this one) | info |
| L10 | `index.md` contains an entry for this page | warning |

---

## 9. Index File Format

`index.md` uses this structure:

```markdown
# DreamFi Product Knowledge Hub

## How to Use This Wiki
...

## Features
- [[feature-xxx]] -- short description

## Flows
- [[flow-xxx]] -- short description

## Concepts
- [[concept-xxx]] -- short description

## Components
- [[component-xxx]] -- short description

## Integrations
- [[integration-xxx]] -- short description

## Comparisons
- [[comparison-xxx]] -- short description
```

---

## 10. Change Log Format

`log.md` uses a markdown table:

```markdown
| Date | Action | Page | Summary | Source |
|------|--------|------|---------|--------|
| 2025-04-10 | created | feature-kyc-flow | Initial page from Confluence | confluence:12345 |
```

Actions: `created`, `updated`, `deleted` (deprecated).

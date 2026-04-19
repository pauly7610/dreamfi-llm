# Knowledge Hub Service

Phase 1 foundation service for DreamFi. Stores product knowledge, skill definitions, evaluation results, gold examples, and failure patterns. Provides retrieval and query APIs backed by Postgres.

## Prerequisites

- Node.js >= 18
- PostgreSQL >= 15
- TypeScript >= 5.x

## Setup

```bash
# Install dependencies
npm install

# Create the database
createdb dreamfi_knowledge_hub

# Run the schema
psql -d dreamfi_knowledge_hub -f db/schema.sql

# Configure environment
cp .env.example .env
# Edit .env with your database URL and connector credentials

# Build
npm run build

# Start
npm start
```

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `PORT` | Server port (default: 3100) |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_EMAIL` | Jira auth email |
| `JIRA_API_TOKEN` | Jira API token |
| `DRAGONBOAT_BASE_URL` | Dragonboat API URL |
| `DRAGONBOAT_TOKEN` | Dragonboat bearer token |
| `LUCIDCHART_CLIENT_ID` | Lucidchart OAuth2 client ID |
| `LUCIDCHART_CLIENT_SECRET` | Lucidchart OAuth2 client secret |
| `CONFLUENCE_BASE_URL` | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Confluence auth email |
| `CONFLUENCE_API_TOKEN` | Confluence API token |
| `METABASE_BASE_URL` | Metabase instance URL |
| `METABASE_USERNAME` | Metabase login username |
| `METABASE_PASSWORD` | Metabase login password |
| `POSTHOG_BASE_URL` | PostHog instance URL |
| `POSTHOG_API_KEY` | PostHog personal API key |
| `GA_PROPERTY_ID` | Google Analytics property ID |
| `GA_KEY_FILE_PATH` | Path to GA service account JSON key |
| `KLAVIYO_API_KEY` | Klaviyo private API key |
| `NETXD_BASE_URL` | Ledger NetXD API URL |
| `NETXD_API_KEY` | NetXD API key |
| `NETXD_CLIENT_ID` | NetXD client ID |
| `SARDINE_BASE_URL` | Sardine API URL |
| `SARDINE_CLIENT_ID` | Sardine client ID |
| `SARDINE_SECRET_KEY` | Sardine secret key |
| `SOCURE_BASE_URL` | Socure API URL |
| `SOCURE_API_KEY` | Socure API key |
| `OPENAI_API_KEY` | LLM API key for query answering |

## API Endpoints

### Query

| Method | Path | Description |
|---|---|---|
| POST | `/api/query` | Ask a question, get answer with citations and confidence |

### Entities

| Method | Path | Description |
|---|---|---|
| GET | `/api/entities` | List entities (with `?type=` and `?search=` filters) |
| GET | `/api/entities/:id` | Get entity with relationships and citations |
| POST | `/api/entities` | Create entity |
| PUT | `/api/entities/:id` | Update entity |
| POST | `/api/entities/sync/:connector` | Trigger connector sync |

### Skills

| Method | Path | Description |
|---|---|---|
| GET | `/api/skills` | List all skills with active prompt version |
| GET | `/api/skills/:id` | Skill detail with criteria, test inputs, recent rounds |
| POST | `/api/skills/:id/prompt-versions` | Create new prompt version |
| POST | `/api/skills/:id/promote` | Promote prompt version (requires score improvement) |
| GET | `/api/skills/:id/gold-examples` | Gold examples for skill |
| GET | `/api/skills/:id/failure-patterns` | Failure patterns for skill |

### Evaluations

| Method | Path | Description |
|---|---|---|
| POST | `/api/evals/run` | Run evaluation round for a skill + prompt version |
| GET | `/api/evals/rounds/:skillId` | List eval rounds for a skill |
| GET | `/api/evals/rounds/:roundId/outputs` | Outputs for a specific round |
| GET | `/api/evals/criteria/:skillId` | Locked evaluation criteria for skill |

## Connectors (11)

1. **Jira** - Epics, stories, bugs from Atlassian Jira
2. **Dragonboat** - Initiatives, features, roadmap items
3. **Lucidchart** - Flow diagrams and document metadata
4. **Confluence** - Pages and blog posts from wiki spaces
5. **Metabase** - Saved questions, dashboards, database metadata
6. **PostHog** - Event definitions, actions, insights, feature flags
7. **Google Analytics** - Report data, dimensions, metrics
8. **Klaviyo** - Campaigns, flows, lists, metrics
9. **Ledger NetXD** - Transactions, balances, settlements
10. **Sardine** - Fraud alerts, risk scores, monitoring rules
11. **Socure** - Verification decisions, KYC risk scores

## Architecture

```
POST /api/query
  -> retrieveContext (full-text + embedding search)
  -> load active prompt version
  -> fetch gold examples + failure patterns
  -> generate answer via LLM
  -> scoreConfidence
  -> return { answer, citations, freshness, confidence }
```

Confidence scoring weights: freshness (40%), citation quality (25%), eval score (25%), hard-gate pass rate (10%).

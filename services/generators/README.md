# Generators Service

Phase 2 service for DreamFi. Provides criteria-driven document generators that use locked binary evals from the autoresearch toolkit. Each generator maps to a specific skill with hard-gate constraints that enforce quality standards on every output.

## Generator Catalog

| Skill | Tier | Hard Gates | Output Format |
|---|---|---|---|
| Agent System Prompt | 1 | 5 criteria (intent, no hallucination, next action, word limit, refusal) | Markdown |
| Support Agent | 1 | 5 criteria (resolve, KB-only, message count, escalation, word limit) | Markdown |
| Meeting Summary | 1 | 5 criteria (owner+deadline, decisions, sections, questions, word limit) | Markdown |
| Cold Email | 2 | 4 criteria (word limit, specificity, question ending, numbers) | Plaintext |
| Landing Page Copy | 2 | 5 criteria (headline number, no buzzwords, CTA, pain point, word limit) | Markdown |
| Newsletter Headline | 2 | 4 criteria (number, char limit, curiosity gap, preview info) | Plaintext |
| Product Description | 2 | 5 criteria (problem first, numeric result, no competitors, objection, word limit) | Markdown |
| Resume Bullet | 3 | 4 criteria (strong verb, quantified, word limit, business outcome) | Plaintext |
| Short-Form Script | 3 | 5 criteria (curiosity gap, surprising claim, single thread, read time, hook) | Markdown |

## Prerequisites

- Node.js >= 18
- TypeScript >= 5.x
- Access to Phase 1 Knowledge Hub API (default: `http://localhost:3100`)
- Anthropic API key for Claude

## Setup

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys and service URLs

# Build
npm run build

# Run tests
npm test
```

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `KNOWLEDGE_HUB_URL` | Phase 1 Knowledge Hub API base URL (default: `http://localhost:3100`) |
| `CONFLUENCE_BASE_URL` | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Confluence auth email |
| `CONFLUENCE_API_TOKEN` | Confluence API token |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_EMAIL` | Jira auth email |
| `JIRA_API_TOKEN` | Jira API token |
| `DRAGONBOAT_BASE_URL` | Dragonboat API URL |
| `DRAGONBOAT_TOKEN` | Dragonboat bearer token |

## Workflow

### Single Generation

1. User selects a skill (e.g., `cold_email`).
2. User fills the form fields defined by the skill template.
3. Service loads the skill template and retrieves relevant context from the Knowledge Hub.
4. Service builds a prompt from the template, form data, and context.
5. Service calls Claude to generate output.
6. Output runs through all hard-gate checks (binary pass/fail per gate).
7. Service returns the result with pass/fail status and gate-level detail.

### Eval Round (Autoresearch Pattern)

1. Load test inputs from the skill registry.
2. For each test input, generate 10 outputs.
3. Score every output against locked criteria (binary pass/fail per criterion).
4. Compute round score: `total passes / total checks`.
5. Compare to previous best round score.
6. If improved: KEEP the prompt version change.
7. If regressed: REVERT.
8. Log everything to `results.log`.

### Publishing

Generated content that passes all hard gates can be published to:

- **Confluence** -- creates or updates wiki pages
- **Jira** -- creates epics with stories
- **Dragonboat** -- creates or updates features/initiatives
- **PDF** -- exports with DreamFi branding
- **DOCX** -- exports with DreamFi template styling

## Project Structure

```
services/generators/
  src/
    templates/           # Skill template configs (9 generators)
      types.ts           # Shared SkillTemplate, HardGate, FormField interfaces
      index.ts           # Template registry
      agent_system_prompt.ts
      support_agent.ts
      meeting_summary.ts
      cold_email.ts
      landing_page_copy.ts
      newsletter_headline.ts
      product_description.ts
      resume_bullet.ts
      short_form_script.ts
    constraints/         # Constraint enforcement
      skill_constraints.ts
    forms/
      schema/            # JSON Schema definitions for form validation
        cold_email_form.json
        meeting_summary_form.json
        landing_page_copy_form.json
    generate/            # Core generation engine
      generate_output.ts
    evals/               # Eval round runner
      run_skill_round.ts
    publish/             # Output publishers and exporters
      publish_to_confluence.ts
      publish_to_jira.ts
      publish_to_dragonboat.ts
      export_pdf.ts
      export_docx.ts
```

# DreamFi Phase 3: Dragonboat + Jira Trust-Based Reporting

## Goal

Standardize roadmap and execution data across Jira and Dragonboat, then layer structured summaries and escalation logic on top. Reporting trust depends on both data quality and summary quality.

## Core Architecture

### Data Normalization Layer

Map Jira and Dragonboat fields to canonical schema to ensure consistency:

```
Jira Status                    → Canonical Status
To Do                          → backlog
In Progress                    → in_progress
In Review                      → review
Done                           → completed
Blocked / On Hold              → blocked

Dragonboat Status              → Canonical Status
Planning                       → planning
In Development                 → in_progress
Launched                       → completed
Deferred                       → deferred
```

### Validation Rules

1. No orphaned planning items (every story has a parent epic or roadmap item)
2. Required fields populated (owner, status, dates)
3. Deterministic status mappings (same Jira status always maps to same canonical)
4. Data freshness within SLA (Jira synced within 24h, Dragonboat within 7d)

### Reporting Skills

#### `report_summary` (modeled on `meeting_summary`)

- Summarizes project status, milestones, and risks
- Must follow distinct sections: Status, Risks, Milestones, Action Items
- Hard gates same as `meeting_summary` (decisions, action items with owners, no fabrication)
- Output: <500 words

#### `report_escalation` (modeled on `agent_system_prompt` + `support_agent`)

- Escalates data quality issues, missing owners, stale information
- Must clearly state the issue before proposing action
- Hard gates: Clear issue statement, specific resolution path, no guessing
- Output: <200 words

## Service Structure

```
services/planning-sync/
├── README.md
├── src/
│   ├── mapping/
│   │   ├── jira_status_map.ts
│   │   ├── dragonboat_status_map.ts
│   │   ├── field_map.ts
│   │   └── hierarchy_rules.ts
│   ├── validation/
│   │   └── validate_taxonomy.ts
│   ├── reporting/
│   │   ├── generate_report_summary.ts
│   │   └── escalate_reporting_gap.ts
│   └── index.ts
└── tests/
    ├── unit/
    │   ├── test_field_mapping.ts
    │   ├── test_hierarchy_rules.ts
    │   ├── test_generate_report_summary.ts
    │   └── test_report_gap_escalation.ts
    └── integration/
        └── test_jira_dragonboat_sync.ts
```

## Key Workflows

### 1. Planning Sync Workflow

1. Fetch Jira epics, stories, bugs (via Phase 1 Knowledge Hub connector)
2. Fetch Dragonboat roadmap items and initiatives (via Phase 1 connector)
3. Normalize both to canonical `core_entities`
4. Validate taxonomy (no orphans, all owners present)
5. Compute freshness scores
6. Generate status report summary using `report_summary` skill
7. Escalate data quality issues using `report_escalation` skill
8. Publish report to Confluence (or return via API)

### 2. Data Gap Detection

When validation fails:

- Missing owner on story → Escalate for assignment
- Stale Jira data (>24h) → Flag as low-confidence
- Orphaned item → Flag as taxonomy error
- Status undefined → Flag as data quality issue

Each gap is escalated as a `report_escalation` with:

- Clear problem statement
- Affected items (with links)
- Resolution action

## Acceptance Criteria

- [ ] No orphaned planning items pass validation
- [ ] Report summaries follow meeting-summary structure
- [ ] Missing-data situations are explicitly stated with resolution path
- [ ] Field mapping is deterministic (same input always produces same output)
- [ ] All Jira and Dragonboat items syncable to canonical schema
- [ ] Freshness scores tracked and reported
- [ ] Dashboard shows data quality flags

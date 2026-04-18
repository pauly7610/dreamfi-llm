# DreamFi Phase 5: UI Project Support

## Goal

Create a standing product support lane for the UI initiative with style constraints, export readiness enforcement, and skill-scored copy for every UI surface.

## Core Architecture

### Style Constraints Layer

All UI artifacts must conform to DreamFi fintech design principles:

**Minimalist Fintech Design:**

- Whitespace priority: minimum 40% whitespace on every screen
- Streamlined navigation: 3 levels deep max
- Standard component preference: use DreamFi design system components
- No hard-coded pixel positioning: responsive layouts only
- Type scale: 12px, 14px, 16px, 18px, 20px, 24px, 32px (only)

**Export-Readiness Checklist:**

**Code Quality:**

- [ ] Uses standard layout components (Grid, Flex, Stack)
- [ ] No hard-coded pixel positioning
- [ ] Responsive breakpoints: mobile (320px), tablet (768px), desktop (1280px)
- [ ] Dark mode compatible
- [ ] Accessibility: contrast ratio >= 4.5:1, keyboard navigation

**Copy Quality:**

- [ ] Landing surfaces → `landing_page_copy` skill eval passes
- [ ] Support surfaces → `support_agent` skill eval passes
- [ ] Internal updates → `meeting_summary` skill eval passes
- [ ] Release summaries → `product_description` skill eval passes
- [ ] Email/send surfaces → `newsletter_headline` skill eval passes

An artifact is **export-ready** only when:

1. Code passes all export checks (responsive, no hard-coded positioning)
2. All intended-surface copy passes its skill eval

## Service Structure

```
services/ui-support/
├── README.md
├── src/
│   ├── intake/
│   │   └── intake_schema.ts
│   ├── style/
│   │   └── minimalist_fintech_rules.ts
│   ├── evals/
│   │   └── validate_export_readiness.ts
│   ├── copy/
│   │   ├── map_artifact_skill.ts
│   │   └── surface_copy_mapping.ts
│   ├── publish/
│   │   ├── publish_ui_spec_to_confluence.ts
│   │   ├── publish_ui_epics_to_jira.ts
│   │   └── link_lucid_flow.ts
│   └── index.ts
└── tests/
    ├── unit/
    │   ├── test_minimalist_fintech_rules.ts
    │   ├── test_export_readiness.ts
    │   └── test_map_artifact_skill.ts
    └── integration/
        ├── test_publish_ui_spec.ts
        ├── test_publish_ui_epics.ts
        └── test_ui_to_hub_feedback_loop.ts
```

## Key Workflows

### 1. UI Intake → Eval → Publish

1. **Intake:** Designer or PM submits new UI artifact with:
   - Component/screen name
   - Design file link (Lucid or Figma)
   - Intended surfaces (landing, support, internal, email, release)
   - Associated copy (draft or blank)

2. **Evaluation:**
   - Run style constraint checks (whitespace, component, responsive, positioning)
   - For each intended surface:
     - Map to corresponding skill (`landing_page_copy`, `support_agent`, etc.)
     - Run skill eval on copy
     - Fail if skill eval fails
   - Overall: artifact is export-ready only if all evals pass

3. **Publication:**
   - If export-ready, publish UI spec to Confluence
   - Create related Jira epic for implementation
   - Link Lucidchart flow if included
   - Track approval and implementation status

4. **Feedback Loop:**
   - Once shipped, collect user feedback signals
   - Ingest back into Phase 1 Knowledge Hub as `core_entities`
   - Close feedback loop: UI → Hub → Future UX Decisions

### 2. Artifact Skill Mapping

Every artifact maps to exactly one primary skill:

```typescript
interface UIArtifact {
  artifact_id: string;
  name: string;
  intended_surface: "landing" | "support" | "internal" | "email" | "release";
  mapped_skill: string; // e.g., 'landing_page_copy'
  copy_content: string;
  design_link: string;
  export_ready: boolean;
}
```

**Mapping Rules:**

| Intended Surface | Mapped Skill        | Examples                                      |
| ---------------- | ------------------- | --------------------------------------------- |
| Landing          | landing_page_copy   | Hero section, pricing page, feature page      |
| Support          | support_agent       | Help modal, FAQ, tooltip, support page        |
| Internal         | meeting_summary     | Internal team notes, status pages, dashboards |
| Email            | newsletter_headline | Email subject, preview text, CTA text         |
| Release          | product_description | Release notes, feature announcements, blog    |

## Acceptance Criteria

- [ ] Every artifact maps to exactly one intended skill
- [ ] Export readiness checks both layout and copy quality
- [ ] Style constraints enforced (whitespace, responsive, components)
- [ ] Approved artifacts ingest back into Phase 1 Hub as feedback
- [ ] Lucidchart flows linked and tracked
- [ ] Jira epics created with export-ready checklist
- [ ] Dashboard shows pending/approved/shipped UI artifacts

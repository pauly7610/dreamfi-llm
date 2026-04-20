export type ModuleId = 'knowledge' | 'generators' | 'planning' | 'metrics' | 'ui-support'

export type ModuleDefinition = {
  id: ModuleId
  title: string
  tagline: string
  description: string
  longDescription: string
  route: string
  integrations: string[]
  actions: string[]
  primaryActionLabel: string
  primaryActionHref: string
  capabilities: string[]
  accent: string
}

export const modules: ModuleDefinition[] = [
  {
    id: 'knowledge',
    title: 'Product Knowledge Hub',
    tagline: 'Ask product questions, get cited answers.',
    description:
      'Answer product questions with citations, freshness, reusable context, and confidence that can be inspected later.',
    longDescription:
      'Retrieve the right context from your planning, analytics, and doc systems. Every answer is grounded, cited, and reusable across PRDs, briefs, and reviews.',
    route: '/console/knowledge',
    integrations: ['confluence', 'jira', 'dragonboat', 'metabase', 'posthog'],
    actions: ['weekly-brief'],
    primaryActionLabel: 'Ask a question',
    primaryActionHref: '/console/knowledge/ask',
    capabilities: [
      'Grounded answers with source citations',
      'Freshness and confidence on every response',
      'Reusable context bundles for downstream generators',
    ],
    accent: 'sky',
  },
  {
    id: 'generators',
    title: 'Document Generators',
    tagline: 'PRDs, briefs, and risk docs with governed contracts.',
    description:
      'Generate governed discovery docs, PRDs, risk docs, and adjacent product artifacts against explicit contracts and eval criteria.',
    longDescription:
      'Produce PRDs, business briefs, risk docs, and discovery artifacts that pass explicit contracts, evaluation criteria, and publish guards before they ever hit Confluence.',
    route: '/console/generators',
    integrations: ['confluence', 'jira', 'dragonboat', 'netxd', 'sardine', 'socure'],
    actions: ['technical-prd', 'business-prd', 'risk-brd', 'weekly-brief'],
    primaryActionLabel: 'Create a Technical PRD',
    primaryActionHref: '/console/generate/technical-prd',
    capabilities: [
      'Technical PRDs, Business PRDs, Risk BRDs',
      'Explicit contracts and hard-gate criteria per artifact',
      'Publish to Confluence only after policy review',
    ],
    accent: 'violet',
  },
  {
    id: 'planning',
    title: 'Planning Trust',
    tagline: 'Trusted briefs with ambiguity and hygiene flags.',
    description:
      'Turn planning inputs into trusted briefs with explicit ambiguity, missing-data, and hygiene flags.',
    longDescription:
      'Pull from Jira and Dragonboat to build briefs that flag ambiguity, missing owners, stale tickets, and unclear acceptance criteria before they become product risk.',
    route: '/console/planning',
    integrations: ['jira', 'dragonboat', 'confluence'],
    actions: ['weekly-brief', 'business-prd'],
    primaryActionLabel: 'Run weekly PM brief',
    primaryActionHref: '/console/generate/weekly-brief',
    capabilities: [
      'Ambiguity and missing-data flags on every brief',
      'Sprint and roadmap hygiene signals',
      'Stakeholder-ready summaries with lineage',
    ],
    accent: 'emerald',
  },
  {
    id: 'metrics',
    title: 'Metric Trust',
    tagline: 'Discrepancy-aware analytics narratives.',
    description:
      'Turn analytics inputs into discrepancy-aware narratives and trusted performance reporting.',
    longDescription:
      'Reconcile Metabase, PostHog, GA, and Klaviyo into performance narratives that flag discrepancies, broken funnels, and untrustworthy series before they reach leadership.',
    route: '/console/metrics',
    integrations: ['metabase', 'posthog', 'ga', 'klaviyo'],
    actions: ['business-prd'],
    primaryActionLabel: 'Compose metric narrative',
    primaryActionHref: '/console/metrics/new-narrative',
    capabilities: [
      'Cross-source discrepancy detection',
      'Trusted KPI and funnel summaries',
      'Reconstructible lineage from raw events',
    ],
    accent: 'amber',
  },
  {
    id: 'ui-support',
    title: 'UI Project Support',
    tagline: 'Structured intake, validation, and publishable UI work.',
    description:
      'Support UI and product work with structured intake, validation, export readiness, and governed publishability.',
    longDescription:
      'Capture structured intake for UI work, validate scope and acceptance criteria, and gate export and publish against governed checks so design and engineering stay in sync.',
    route: '/console/ui-support',
    integrations: ['confluence', 'jira', 'posthog'],
    actions: ['technical-prd'],
    primaryActionLabel: 'Start a UI intake',
    primaryActionHref: '/console/ui-support/intake',
    capabilities: [
      'Structured intake forms for UI and product work',
      'Validation, export readiness, and publish gates',
      'Lineage from intake through published artifact',
    ],
    accent: 'rose',
  },
]

export const moduleById: Record<ModuleId, ModuleDefinition> = modules.reduce(
  (acc, module) => {
    acc[module.id] = module
    return acc
  },
  {} as Record<ModuleId, ModuleDefinition>,
)

export const coreModules = modules.map((module) => ({
  title: module.title,
  description: module.description,
}))

export const methodologyPoints = [
  'Ground outputs in real source data and retrieval evidence.',
  'Evaluate outputs against explicit hard-gate criteria.',
  'Score trust with decomposed, inspectable signals.',
  'Reconstruct artifacts later from prompts, traces, and sources.',
  'Gate publish behind policy and operator review when needed.',
]

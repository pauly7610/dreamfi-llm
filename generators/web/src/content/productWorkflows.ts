export type ProductWorkflowTone = 'ready' | 'watch' | 'blocked'

export type ProductWorkflowState = {
  phase: string
  step: string
  jiraState: string
  readiness: string
  tone: ProductWorkflowTone
}

export type ProductWorkflowGateStatus = 'ready' | 'watch' | 'blocked' | 'not-needed'

export type ProductWorkflowGate = {
  label: string
  status: ProductWorkflowGateStatus
  summary: string
  detail: string
  sourceIds: string[]
}

export type ProductWorkflowOwner = {
  role: string
  owner: string
  nextAction: string
}

export type ProductWorkflowRisk = {
  label: string
  level: 'low' | 'medium' | 'high'
  detail: string
  owner: string
  sourceIds: string[]
}

export type ProductWorkflowConnectorCoverage = {
  sourceId: string
  role: string
  bestFor: string
  detail: string
  driftNote: string
}

export type ProductWorkflowQuestionGroup = {
  title: string
  questions: string[]
}

export type ProductWorkflowModel = {
  topicId: string
  currentState: ProductWorkflowState
  nextDecision: string
  recommendation: string
  missing: string[]
  owners: ProductWorkflowOwner[]
  gates: ProductWorkflowGate[]
  risks: ProductWorkflowRisk[]
  connectorCoverage: ProductWorkflowConnectorCoverage[]
  questionGroups: ProductWorkflowQuestionGroup[]
}

export const productWorkflows: ProductWorkflowModel[] = [
  {
    topicId: 'kyc-conversion',
    currentState: {
      phase: 'Definition',
      step: 'Step 7 readiness',
      jiraState: 'Blocked before Ready for Dev',
      readiness: 'Hold for sponsor alignment',
      tone: 'blocked',
    },
    nextDecision: 'Should KYC retry improvements move to Ready for Dev or stay blocked until sponsor-bank controls are confirmed?',
    recommendation:
      'Keep this in readiness review until sponsor guidance, accepted risk ownership, and live Socure retry evidence all line up.',
    missing: [
      'Sponsor-bank review outcome needs to be linked in Confluence before Product marks this ready.',
      'Accepted-risk owner for the manual-review fallback is still missing from the readiness note.',
      'Live Socure retry logs are degraded, so the risk recommendation is not yet publish-safe.',
    ],
    owners: [
      {
        role: 'Product',
        owner: 'Growth PM',
        nextAction: 'Close the decision note with compliance and attach it to the Jira epic.',
      },
      {
        role: 'Compliance',
        owner: 'Risk partner',
        nextAction: 'Confirm sponsor-required controls for stepped-up identity checks.',
      },
      {
        role: 'Engineering',
        owner: 'Identity squad lead',
        nextAction: 'Hold the Ready for Dev transition until Step 7 signoff is visible in Jira.',
      },
    ],
    gates: [
      {
        label: 'Gate 1 · Leadership concept approval',
        status: 'ready',
        summary: 'Approved for discovery',
        detail: 'The problem statement and expected conversion lift are already captured in the current PRD set.',
        sourceIds: ['confluence', 'jira'],
      },
      {
        label: 'Gate 2 · Sponsor-bank alignment',
        status: 'blocked',
        summary: 'Pending explicit control confirmation',
        detail: 'The current readiness packet references sponsor review, but the required control language is not attached yet.',
        sourceIds: ['confluence', 'jira'],
      },
      {
        label: 'Gate 3 · Cross-functional Step 7',
        status: 'watch',
        summary: 'Engineering is close, Ops and Compliance still need closure',
        detail: 'The build path is feasible, but operational fallback and risk ownership are still open.',
        sourceIds: ['jira', 'confluence', 'socure'],
      },
    ],
    risks: [
      {
        label: 'Sponsor policy drift',
        level: 'high',
        detail: 'If sponsor expectations changed since the last review, moving forward would create avoidable rework.',
        owner: 'Compliance',
        sourceIds: ['confluence', 'jira'],
      },
      {
        label: 'Manual review backlog',
        level: 'medium',
        detail: 'Questionable and stepped-up cases are rising faster than the proposed retry experience reduces them.',
        owner: 'Operations',
        sourceIds: ['socure', 'sardine'],
      },
    ],
    connectorCoverage: [
      {
        sourceId: 'jira',
        role: 'System of record',
        bestFor: 'Current state, readiness labels, assignee, and sprint timing.',
        detail: 'Use Jira for the canonical workflow state and for checking whether work moved into delivery too early.',
        driftNote: 'Status mappings can drift when teams rename workflow columns or skip Step 7 labels.',
      },
      {
        sourceId: 'confluence',
        role: 'Decision log',
        bestFor: 'PRD scope, sponsor notes, accepted risk, and compliance rationale.',
        detail: 'Use Confluence to anchor why the work exists and which constraints or non-starters were accepted.',
        driftNote: 'Decision notes drift when they are not linked back to the shipping Jira epic or kept current after review.',
      },
      {
        sourceId: 'socure',
        role: 'Risk evidence',
        bestFor: 'Fraud tiers, identity reason codes, stepped-up review, and explainability.',
        detail: 'Use Socure to understand what risk is rising and whether manual review is justified.',
        driftNote: 'Operational health matters: degraded retry logs can make a strong-sounding answer unsafe to publish.',
      },
      {
        sourceId: 'sardine',
        role: 'Supporting risk evidence',
        bestFor: 'Behavioral or AML-style signals that support a broader risk posture.',
        detail: 'Use Sardine as secondary corroboration when fraud posture needs another lens beyond identity checks.',
        driftNote: 'Coverage varies by integration scope, so absence of a signal should not be treated as proof of no risk.',
      },
      {
        sourceId: 'posthog',
        role: 'Behavior evidence',
        bestFor: 'Where users stall, retry, or abandon the flow in product.',
        detail: 'Use PostHog to connect process decisions back to real friction in the funnel.',
        driftNote: 'Event names and flag exposure can drift if instrumentation changes before the workflow model updates.',
      },
      {
        sourceId: 'metabase',
        role: 'Outcome evidence',
        bestFor: 'Warehouse conversion, manual-review rate, and downstream funnel impact.',
        detail: 'Use Metabase for topline outcome truth when deciding whether the concept is worth more investment.',
        driftNote: 'Saved questions can change shape over time, so verified KPI definitions should be monitored.',
      },
    ],
    questionGroups: [
      {
        title: 'Meta questions',
        questions: [
          'What step are we in right now?',
          'What is missing before we can move forward?',
          'Should we move forward or stop?',
        ],
      },
      {
        title: 'Gate checks',
        questions: [
          'Has sponsor bank consultation occurred?',
          'Is Compliance satisfied with the current risk posture?',
          'Should this move to Ready for Dev or stay blocked?',
        ],
      },
      {
        title: 'Risk questions',
        questions: [
          'What risk are we taking if we proceed?',
          'Who owns unresolved risk for this feature?',
        ],
      },
    ],
  },
  {
    topicId: 'onboarding',
    currentState: {
      phase: 'Discovery',
      step: 'Requirements intake',
      jiraState: 'Discovery in progress',
      readiness: 'Discovery still open',
      tone: 'watch',
    },
    nextDecision: 'Are we ready to move this onboarding simplification into a PRD, or do we still need more discovery evidence?',
    recommendation:
      'Stay in discovery until roadmap ownership, funding dependencies, and operational constraints are all explicit.',
    missing: [
      'Dragonboat still needs a clear portfolio owner for the onboarding initiative.',
      'Operational support constraints for first-funding retries are not yet written into the requirements intake.',
      'Dependencies between identity, funding, and support tooling need one shared definition of done.',
    ],
    owners: [
      {
        role: 'Product',
        owner: 'Onboarding PM',
        nextAction: 'Turn the current discovery notes into a requirements intake packet.',
      },
      {
        role: 'Operations',
        owner: 'Customer Ops lead',
        nextAction: 'Document what support handoff and fallback processes would change.',
      },
      {
        role: 'Engineering',
        owner: 'Core product squad lead',
        nextAction: 'Confirm the dependency chain before the scope moves into definition.',
      },
    ],
    gates: [
      {
        label: 'Gate 1 · Leadership concept approval',
        status: 'ready',
        summary: 'Approved for discovery and roadmap discussion',
        detail: 'The initiative is already recognized as worthwhile, but still needs a tighter definition of scope.',
        sourceIds: ['dragonboat', 'confluence'],
      },
      {
        label: 'Gate 2 · Sponsor-bank alignment',
        status: 'watch',
        summary: 'Likely needed if disclosures or funding timing change',
        detail: 'No hard blocker yet, but sponsor review should be planned before any user-visible policy changes ship.',
        sourceIds: ['confluence', 'jira'],
      },
      {
        label: 'Gate 3 · Cross-functional Step 7',
        status: 'watch',
        summary: 'Too early for readiness, but dependencies are visible now',
        detail: 'This should not be marked Ready for Dev until the discovery packet closes the main unknowns.',
        sourceIds: ['jira', 'confluence', 'posthog'],
      },
    ],
    risks: [
      {
        label: 'Unowned roadmap priority',
        level: 'medium',
        detail: 'Without a portfolio owner, the work can bounce between teams or be treated as side work.',
        owner: 'Product leadership',
        sourceIds: ['dragonboat'],
      },
      {
        label: 'Dependency ambiguity',
        level: 'medium',
        detail: 'Identity, funding, and support changes are coupled, so a narrow PRD could understate delivery complexity.',
        owner: 'Engineering',
        sourceIds: ['jira', 'confluence'],
      },
    ],
    connectorCoverage: [
      {
        sourceId: 'dragonboat',
        role: 'Strategy alignment',
        bestFor: 'Product Queue, Approved for Discovery state, and OKR alignment.',
        detail: 'Use Dragonboat to understand why this work is prioritized and whether leadership has already advanced it.',
        driftNote: 'Portfolio truth drifts when roadmap state is updated in Jira but not reflected back into the planning system.',
      },
      {
        sourceId: 'jira',
        role: 'System of record',
        bestFor: 'Current delivery state, dependencies, and whether work entered delivery too early.',
        detail: 'Use Jira to anchor the current phase, active owner, and whether discovery is being respected.',
        driftNote: 'A board can look ready even when the process gate is incomplete if custom fields are not enforced.',
      },
      {
        sourceId: 'confluence',
        role: 'Requirements log',
        bestFor: 'Problem framing, constraints, assumptions, and definition-of-done notes.',
        detail: 'Use Confluence for intake details, assumptions, and which teams need to be involved next.',
        driftNote: 'Scope drifts when meeting notes move faster than the formal PRD or requirements document.',
      },
      {
        sourceId: 'posthog',
        role: 'Behavior evidence',
        bestFor: 'Replay watchlists, abandonment, and real friction inside the onboarding flow.',
        detail: 'Use PostHog to prove whether the problem is real enough to justify more discovery investment.',
        driftNote: 'Event and replay slices can drift if the tracked steps in onboarding are renamed.',
      },
      {
        sourceId: 'metabase',
        role: 'Outcome evidence',
        bestFor: 'Stage conversion and first-funding performance across cohorts.',
        detail: 'Use Metabase to anchor volume, opportunity size, and success metrics for the eventual PRD.',
        driftNote: 'Metric definitions should stay verified so shifts in warehouse logic do not masquerade as product change.',
      },
    ],
    questionGroups: [
      {
        title: 'Phase questions',
        questions: [
          'What problem are we actually solving?',
          'What hypotheses are we testing?',
          'Are we ready to move to requirements intake?',
        ],
      },
      {
        title: 'Ownership questions',
        questions: [
          'Who owns this feature right now?',
          'Which teams must be involved next?',
          'Should Engineering be engaged yet?',
        ],
      },
      {
        title: 'Meta questions',
        questions: [
          'What step are we in right now?',
          'What decision is required next?',
        ],
      },
    ],
  },
  {
    topicId: 'funding',
    currentState: {
      phase: 'Design & readiness',
      step: 'Step 6 solution design',
      jiraState: 'In design review',
      readiness: 'Watch payment dependencies',
      tone: 'watch',
    },
    nextDecision: 'Can the first-funding recovery work move into readiness without adding more payment controls or support burden?',
    recommendation:
      'Keep this in design review until payment-failure detail, support readiness, and compliance wording all converge.',
    missing: [
      'NetXD decline-code detail is still too coarse to explain the main recovery paths.',
      'Operations runbook updates for failed first-funding attempts are not attached to the feature packet yet.',
      'Compliance fallback wording for sensitive payment states still needs review.',
    ],
    owners: [
      {
        role: 'Product',
        owner: 'Funding PM',
        nextAction: 'Decide whether the scope stays focused on recovery or broadens into payments reliability.',
      },
      {
        role: 'Operations',
        owner: 'Payments ops lead',
        nextAction: 'Confirm how failed transfers will be triaged and communicated after launch.',
      },
      {
        role: 'Compliance',
        owner: 'Payments compliance partner',
        nextAction: 'Review customer-facing language for sensitive funding failures.',
      },
    ],
    gates: [
      {
        label: 'Gate 1 · Leadership concept approval',
        status: 'ready',
        summary: 'Investment case is understood',
        detail: 'The opportunity to improve first-funding recovery is already accepted as a worthwhile product problem.',
        sourceIds: ['confluence', 'jira'],
      },
      {
        label: 'Gate 2 · Sponsor-bank alignment',
        status: 'watch',
        summary: 'Needed if payment messaging or controls materially change',
        detail: 'The team can keep designing, but sponsor alignment should happen before customer-visible payment-policy changes.',
        sourceIds: ['confluence', 'netxd'],
      },
      {
        label: 'Gate 3 · Cross-functional Step 7',
        status: 'blocked',
        summary: 'Not ready for delivery signoff yet',
        detail: 'The solution path is promising, but support and payment risk handling are not yet complete.',
        sourceIds: ['jira', 'netxd', 'confluence'],
      },
    ],
    risks: [
      {
        label: 'Opaque payment failure reasons',
        level: 'high',
        detail: 'If failure detail stays too generic, Product may optimize the wrong recovery step.',
        owner: 'Payments ops',
        sourceIds: ['netxd'],
      },
      {
        label: 'Support burden creep',
        level: 'medium',
        detail: 'A better in-product recovery path can still increase support load if fallback cases are not documented.',
        owner: 'Operations',
        sourceIds: ['jira', 'confluence'],
      },
    ],
    connectorCoverage: [
      {
        sourceId: 'netxd',
        role: 'Money truth',
        bestFor: 'Transfer status, payment rail outcomes, and ledger-linked failure context.',
        detail: 'Use NetXD when the question is about what happened in the payment system, not just what the UI showed.',
        driftNote: 'Payment APIs can surface rail-specific detail differently, so normalized failure states need careful mapping.',
      },
      {
        sourceId: 'jira',
        role: 'System of record',
        bestFor: 'Who owns the work, what state it is in, and whether Step 7 has happened yet.',
        detail: 'Use Jira to prevent design work from quietly becoming delivery work before cross-functional review clears.',
        driftNote: 'Delivery boards drift when issues move forward without the readiness custom fields being enforced.',
      },
      {
        sourceId: 'confluence',
        role: 'Decision log',
        bestFor: 'Funding constraints, support process changes, and launch communication prep.',
        detail: 'Use Confluence to record operational and compliance constraints that do not naturally live in a metric tool.',
        driftNote: 'Runbooks and PRDs often diverge late in the cycle unless they are reviewed together.',
      },
      {
        sourceId: 'posthog',
        role: 'Behavior evidence',
        bestFor: 'Funding-page revisits, loopbacks, and friction after initial failure.',
        detail: 'Use PostHog to see whether recovery friction is a UI problem, a timing problem, or a payment-state problem.',
        driftNote: 'Behavioral slices can drift if the funding flow changes but tracked event names do not.',
      },
      {
        sourceId: 'metabase',
        role: 'Outcome evidence',
        bestFor: 'First-funding volume, downstream activation, and cohort-level impact.',
        detail: 'Use Metabase to measure whether the recovery work moves real business outcomes after launch.',
        driftNote: 'Warehouse questions can drift when definitions of funding-ready accounts change over time.',
      },
    ],
    questionGroups: [
      {
        title: 'Solution questions',
        questions: [
          'How are we building this?',
          'What tradeoffs were made?',
          'Is the solution within defined constraints?',
        ],
      },
      {
        title: 'Readiness questions',
        questions: [
          'Is operational support ready?',
          'What is blocking readiness?',
          'Should we proceed, adjust scope, or escalate?',
        ],
      },
      {
        title: 'Meta questions',
        questions: [
          'What risk are we taking if we proceed?',
          'What decision is required next?',
        ],
      },
    ],
  },
  {
    topicId: 'lifecycle-messaging',
    currentState: {
      phase: 'Delivery & learning',
      step: 'Step 10 execution and post-launch',
      jiraState: 'Live and evaluating',
      readiness: 'Learning loop active',
      tone: 'ready',
    },
    nextDecision: 'Should the current onboarding reminders continue as-is, be iterated, or be deprecated?',
    recommendation:
      'Keep the program live while attribution is reconciled, then decide whether to double down on the winning nudge path.',
    missing: [
      'GA and Klaviyo attribution still need one reconciled read before the brief is shared broadly.',
      'The launch notes should capture what changed from the original messaging plan.',
    ],
    owners: [
      {
        role: 'Product',
        owner: 'Lifecycle PM',
        nextAction: 'Decide whether the next experiment is about timing, channel mix, or audience targeting.',
      },
      {
        role: 'Marketing',
        owner: 'CRM lead',
        nextAction: 'Review open and click performance against the current holdout logic.',
      },
      {
        role: 'Analytics',
        owner: 'Growth analyst',
        nextAction: 'Reconcile acquisition and downstream activation before the next recommendation is published.',
      },
    ],
    gates: [
      {
        label: 'Gate 1 · Leadership concept approval',
        status: 'ready',
        summary: 'Approved and already in market',
        detail: 'This lifecycle work is beyond concept approval and is now in learn-and-iterate mode.',
        sourceIds: ['confluence', 'klaviyo'],
      },
      {
        label: 'Gate 2 · Sponsor-bank alignment',
        status: 'not-needed',
        summary: 'Not currently a sponsor-sensitive change',
        detail: 'The active messaging adjustments do not change a regulated control in the current slice.',
        sourceIds: ['confluence'],
      },
      {
        label: 'Gate 3 · Cross-functional Step 7',
        status: 'ready',
        summary: 'Already cleared for the current release',
        detail: 'The important question now is whether the current launch behavior should continue or change.',
        sourceIds: ['jira', 'confluence'],
      },
    ],
    risks: [
      {
        label: 'Attribution mismatch',
        level: 'medium',
        detail: 'Klaviyo can show strong flow performance while GA still needs to confirm the broader acquisition picture.',
        owner: 'Analytics',
        sourceIds: ['klaviyo', 'ga'],
      },
      {
        label: 'Message fatigue',
        level: 'low',
        detail: 'The current reminders are working, but repeat sends could create diminishing returns if timing is not tuned.',
        owner: 'Marketing',
        sourceIds: ['klaviyo', 'posthog'],
      },
    ],
    connectorCoverage: [
      {
        sourceId: 'klaviyo',
        role: 'Lifecycle truth',
        bestFor: 'Flows, campaigns, audience overlap, and direct message performance.',
        detail: 'Use Klaviyo to understand which nudges are actually firing and how each lifecycle path is performing.',
        driftNote: 'Flow structure and audience definitions change often, so performance needs the current campaign context.',
      },
      {
        sourceId: 'ga',
        role: 'Acquisition evidence',
        bestFor: 'Traffic quality, source mix, and broader session context around onboarding.',
        detail: 'Use GA to check whether the traffic feeding lifecycle programs changed underneath the messaging results.',
        driftNote: 'Report dimensions can shift across properties, so acquisition comparisons should stay standardized.',
      },
      {
        sourceId: 'posthog',
        role: 'Behavior evidence',
        bestFor: 'Whether reminded users actually come back and complete the product journey.',
        detail: 'Use PostHog to separate strong message engagement from real product completion behavior.',
        driftNote: 'Instrumentation drift can make a message look more successful than the downstream product behavior supports.',
      },
      {
        sourceId: 'metabase',
        role: 'Outcome evidence',
        bestFor: 'Activation, conversion lift, and cohort-level business impact.',
        detail: 'Use Metabase to verify whether the marketing activity improves the business outcome that matters.',
        driftNote: 'Saved-question logic can drift away from the experiment design unless KPI definitions are kept verified.',
      },
      {
        sourceId: 'confluence',
        role: 'Decision log',
        bestFor: 'Experiment intent, launch notes, and what changed from the original plan.',
        detail: 'Use Confluence to preserve why the program exists and what the team agreed to test or communicate.',
        driftNote: 'Post-launch learnings drift when they stay in chat or decks instead of being written back to the source doc.',
      },
    ],
    questionGroups: [
      {
        title: 'Learning questions',
        questions: [
          'Did we meet success metrics?',
          'What is adoption versus expectation?',
          'What feedback did we get?',
        ],
      },
      {
        title: 'Decision questions',
        questions: [
          'Should we continue as-is, iterate, or deprecate?',
          'What changed from the original plan?',
          'What do operations and support need to know?',
        ],
      },
      {
        title: 'Meta questions',
        questions: [
          'What decision is required next?',
          'Are we over-applying process unnecessarily?',
        ],
      },
    ],
  },
]

export function workflowByTopicId(topicId: string | null): ProductWorkflowModel | null {
  if (!topicId) {
    return null
  }

  return productWorkflows.find((workflow) => workflow.topicId === topicId) ?? null
}

export function workflowQuestionsForTopic(topicId: string | null): string[] {
  const workflow = workflowByTopicId(topicId)
  if (!workflow) {
    return []
  }

  return workflow.questionGroups.flatMap((group) => group.questions)
}

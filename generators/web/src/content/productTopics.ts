export type ProductTopicSignal = {
  label: string
  value: string
  detail: string
  sourceId?: string
}

export type ProductTopicMetric = {
  label: string
  value: string
  detail: string
  sourceId?: string
}

export type ProductTopic = {
  id: string
  title: string
  summary: string
  question: string
  sources: string[]
  artifacts: string[]
  toplineMetrics: ProductTopicMetric[]
  signals: ProductTopicSignal[]
  gaps: string[]
}

const STARTER_TOPIC_IDS = ['kyc-conversion', 'funding', 'lifecycle-messaging'] as const

export const productTopics: ProductTopic[] = [
  {
    id: 'kyc-conversion',
    title: 'KYC conversion',
    summary: 'Understand movement across identity verification, retries, fraud checks, and onboarding completion.',
    question: 'Why did KYC conversion move this week?',
    sources: ['metabase', 'posthog', 'socure', 'sardine', 'jira', 'confluence'],
    artifacts: ['Weekly PM Brief', 'Technical PRD', 'Risk BRD'],
    toplineMetrics: [
      {
        label: 'Approved KYC',
        value: '73.2%',
        detail: 'Warehouse conversion across the last 7 days.',
        sourceId: 'metabase',
      },
      {
        label: 'Event completion',
        value: '68.4%',
        detail: 'Behavioral funnel with retry friction still present.',
        sourceId: 'posthog',
      },
      {
        label: 'Manual review load',
        value: '11%',
        detail: 'Applicants currently landing in the medium-risk queue.',
        sourceId: 'socure',
      },
    ],
    signals: [
      {
        label: 'Metabase funnel',
        value: '73.2%',
        detail: 'Started KYC to approved KYC over the last 7 days.',
        sourceId: 'metabase',
      },
      {
        label: 'PostHog completion',
        value: '68.4%',
        detail: 'Event-level funnel shows retry friction after document upload.',
        sourceId: 'posthog',
      },
      {
        label: 'Socure health',
        value: 'Needs attention',
        detail: 'Identity source is degraded, so generated answers should cite this limitation.',
        sourceId: 'socure',
      },
    ],
    gaps: ['Live Socure retry logs need confirmation before publishing a risk recommendation.'],
  },
  {
    id: 'onboarding',
    title: 'Onboarding',
    summary: 'Trace the product journey from account creation through first funding and first meaningful action.',
    question: 'What changed in onboarding since the last roadmap review?',
    sources: ['posthog', 'metabase', 'jira', 'confluence', 'dragonboat'],
    artifacts: ['Technical PRD', 'Weekly PM Brief'],
    toplineMetrics: [
      {
        label: 'Replay watchlist',
        value: '83 sessions',
        detail: 'Users revisiting funding after a failed attempt.',
        sourceId: 'posthog',
      },
      {
        label: 'Open delivery items',
        value: '14',
        detail: 'Jira work currently tied to onboarding and first funding.',
        sourceId: 'jira',
      },
      {
        label: 'Spec-linked delivery',
        value: '76%',
        detail: 'Work carrying Confluence or roadmap context.',
        sourceId: 'confluence',
      },
    ],
    signals: [
      {
        label: 'High-intent replay cohort',
        value: '83 sessions',
        detail: 'Sessions with funding-page revisits and failed retry events.',
        sourceId: 'posthog',
      },
      {
        label: 'Open onboarding issues',
        value: '14',
        detail: 'Active Jira tickets linked to onboarding, KYC, and first funding.',
        sourceId: 'jira',
      },
      {
        label: 'Spec-linked tickets',
        value: '76%',
        detail: 'Delivery tickets with a Confluence or Dragonboat source attached.',
        sourceId: 'confluence',
      },
    ],
    gaps: ['Roadmap priority needs a Dragonboat owner before the generated PRD is publish-ready.'],
  },
  {
    id: 'funding',
    title: 'Funding',
    summary: 'Connect activation, payment readiness, transaction health, and ledger context for funding decisions.',
    question: 'Where are users getting stuck before first funding?',
    sources: ['metabase', 'posthog', 'netxd', 'jira', 'confluence'],
    artifacts: ['Business PRD', 'Technical PRD'],
    toplineMetrics: [
      {
        label: 'Funding-ready accounts',
        value: '1,248',
        detail: 'Users who reached the first-funding step this week.',
        sourceId: 'metabase',
      },
      {
        label: 'Return visits',
        value: '83 sessions',
        detail: 'Users looping back into funding after an initial failure.',
        sourceId: 'posthog',
      },
      {
        label: 'Payments health',
        value: 'Live',
        detail: 'Ledger and transfer context is connected for review.',
        sourceId: 'netxd',
      },
    ],
    signals: [
      {
        label: 'Funding-ready accounts',
        value: '1,248',
        detail: 'Users who cleared identity checks and reached the first-funding step.',
        sourceId: 'metabase',
      },
      {
        label: 'Funding-page revisits',
        value: '83 sessions',
        detail: 'PostHog cohort indicates users returning after a failed attempt.',
        sourceId: 'posthog',
      },
      {
        label: 'Payment context',
        value: 'Live',
        detail: 'NetXD is connected for payment and ledger investigation.',
        sourceId: 'netxd',
      },
    ],
    gaps: ['Ledger anomaly details are not included in the development slice yet.'],
  },
  {
    id: 'lifecycle-messaging',
    title: 'Lifecycle messaging',
    summary: 'See how email, SMS, audiences, and acquisition signals support onboarding and activation.',
    question: 'Which lifecycle messages are helping users finish onboarding?',
    sources: ['klaviyo', 'ga', 'posthog', 'metabase', 'confluence'],
    artifacts: ['Business PRD', 'Weekly PM Brief'],
    toplineMetrics: [
      {
        label: 'Nudge open rate',
        value: '42.7%',
        detail: 'Top onboarding reminder flow in the current slice.',
        sourceId: 'klaviyo',
      },
      {
        label: 'Reminder lift',
        value: '6.8%',
        detail: 'Observed conversion gain versus the holdout cohort.',
        sourceId: 'klaviyo',
      },
      {
        label: 'Qualified traffic',
        value: '+12.4%',
        detail: 'Week-over-week growth into onboarding and education pages.',
        sourceId: 'ga',
      },
    ],
    signals: [
      {
        label: 'Onboarding nudge flow',
        value: '42.7% open',
        detail: 'Email flow sent to users who started but did not finish verification.',
        sourceId: 'klaviyo',
      },
      {
        label: 'KYC reminder SMS',
        value: '6.8% lift',
        detail: 'Observed conversion lift in the reminder cohort versus silent holdout.',
        sourceId: 'klaviyo',
      },
      {
        label: 'Organic product traffic',
        value: '+12.4%',
        detail: 'Week-over-week sessions landing on education and onboarding pages.',
        sourceId: 'ga',
      },
    ],
    gaps: ['Campaign attribution should be checked against GA before external sharing.'],
  },
]

export const starterTopics: ProductTopic[] = STARTER_TOPIC_IDS
  .map((topicId) => productTopics.find((topic) => topic.id === topicId))
  .filter((topic): topic is ProductTopic => Boolean(topic))

export function topicById(topicId: string | null): ProductTopic | null {
  if (!topicId) {
    return null
  }
  return productTopics.find((topic) => topic.id === topicId) ?? null
}

export function topicsForSource(sourceId: string): ProductTopic[] {
  return productTopics.filter((topic) => topic.sources.includes(sourceId))
}

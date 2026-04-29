import type { SourceDataPreview } from './sourcePreviewTypes'

export const analyticsSourcePreviews: Record<string, SourceDataPreview> = {
  metabase: {
    headline: 'KPI dashboards, funnels, and SQL-backed source tables',
    description:
      'Metabase is where Product can inspect governed metric definitions before asking DreamFi to summarize or generate a brief.',
    freshness: 'Refreshed 14 minutes ago in the development slice',
    primaryDataset: 'Product KPI warehouse',
    rows: [
      {
        label: 'KYC conversion funnel',
        value: '73.2%',
        detail: 'Started KYC to approved KYC over the last 7 days.',
      },
      {
        label: 'Funding-ready accounts',
        value: '1,248',
        detail: 'Users who cleared identity checks and reached the first-funding step.',
      },
      {
        label: 'Onboarding drop-off dashboard',
        value: '5 watched cards',
        detail: 'SQL cards covering account creation, KYC, funding, and first transaction.',
      },
    ],
    inspect: [
      {
        title: 'Metric definitions',
        detail: 'DreamFi should show how KPIs are defined before quoting them in a brief or PRD.',
      },
      {
        title: 'Cross-source discrepancies',
        detail: 'Look for places where warehouse numbers disagree with event analytics or marketing systems.',
      },
      {
        title: 'Dashboard lineage',
        detail: 'Surface which cards and SQL queries back the narrative so Product can inspect the source.',
      },
    ],
    workflows: [
      {
        title: 'Weekly KPI brief',
        detail: 'Turn the latest trusted dashboard state into a calm weekly update.',
        href: '/console/generate/weekly-brief?source=metabase',
      },
      {
        title: 'Metric discrepancy check',
        detail: 'Ask where Metabase and PostHog disagree before making a product call.',
        href: '/console/knowledge/ask?source=metabase&q=Where%20does%20Metabase%20disagree%20with%20PostHog%20this%20week%3F',
      },
    ],
    views: ['KYC funnel dashboard', 'Activation by funding status', 'Weekly PM KPI snapshot'],
    questions: [
      'Which funnel step moved the most this week?',
      'Where does the KPI definition differ from PostHog events?',
      'What Metabase chart should be cited in the weekly brief?',
    ],
  },
  posthog: {
    headline: 'Events, cohorts, funnels, and session replay context',
    description:
      'PostHog gives Product the behavioral layer: what users clicked, where they stalled, and which sessions need a closer look.',
    freshness: 'Streaming events through the development slice',
    primaryDataset: 'Product analytics events',
    rows: [
      {
        label: 'started_kyc to completed_kyc',
        value: '68.4%',
        detail: 'Seven-day funnel for users who entered the verification path.',
      },
      {
        label: 'High-intent replay cohort',
        value: '83 sessions',
        detail: 'Sessions with funding-page revisits and failed retry events.',
      },
      {
        label: 'Feature flag exposure',
        value: '42% rollout',
        detail: 'New KYC copy experiment exposure across eligible traffic.',
      },
    ],
    inspect: [
      {
        title: 'User journey friction',
        detail: 'DreamFi should look for exact events and screens where users stall, retry, or abandon.',
      },
      {
        title: 'Replay-backed evidence',
        detail: 'Use cohorts and replay context to explain what metrics alone cannot.',
      },
      {
        title: 'Experiment exposure',
        detail: 'Flag which feature flags or experiments were active when the behavior changed.',
      },
    ],
    workflows: [
      {
        title: 'Funnel drop investigation',
        detail: 'Ask which events changed before completion moved.',
        href: '/console/knowledge/ask?source=posthog&q=Which%20event%20changed%20before%20KYC%20completion%20moved%3F',
      },
      {
        title: 'Behavior-to-PRD trace',
        detail: 'Turn replay and funnel evidence into product requirements or follow-up work.',
        href: '/console/generate/technical-prd?source=posthog',
      },
    ],
    views: ['KYC completion funnel', 'Retry friction cohort', 'Activation experiment events'],
    questions: [
      'Which event changed before the KYC conversion dip?',
      'Show sessions where users retried identity verification twice.',
      'What should engineering know from the latest funnel?',
    ],
  },
  klaviyo: {
    headline: 'Marketing + lifecycle campaigns, audiences, and message performance',
    description:
      'Klaviyo should help Product connect marketing and lifecycle messaging to activation, onboarding completion, and reactivation.',
    freshness: 'Synced as a development preview',
    primaryDataset: 'Lifecycle messaging workspace',
    rows: [
      {
        label: 'Onboarding nudge flow',
        value: '42.7% open',
        detail: 'Email flow sent to users who started but did not finish verification.',
      },
      {
        label: 'KYC reminder SMS',
        value: '6.8% lift',
        detail: 'Observed conversion lift in the reminder cohort versus silent holdout.',
      },
      {
        label: 'High-intent lifecycle segment',
        value: '18,420 contacts',
        detail: 'Audience available for reactivation, onboarding nudges, and revenue-focused lifecycle planning.',
      },
    ],
    inspect: [
      {
        title: 'Flow performance by lifecycle step',
        detail: 'Show which email and SMS flows help users finish onboarding, fund, or reactivate.',
      },
      {
        title: 'Audience overlap and fatigue',
        detail: 'Flag when the same users sit in too many campaigns or receive too many sends.',
      },
      {
        title: 'Campaign-to-conversion lift',
        detail: 'Tie messaging back to actual product outcomes, not just opens and clicks.',
      },
    ],
    workflows: [
      {
        title: 'Marketing impact brief',
        detail: 'Generate a brief that connects lifecycle messaging to product outcomes.',
        href: '/console/generate/business-prd?source=klaviyo',
      },
      {
        title: 'Flow effectiveness check',
        detail: 'Ask which lifecycle messages are actually helping users finish onboarding.',
        href: '/console/knowledge/ask?source=klaviyo&q=Which%20lifecycle%20messages%20are%20helping%20users%20finish%20onboarding%3F',
      },
    ],
    views: ['Onboarding nudge flow', 'High-intent audience', 'KYC reminder performance'],
    questions: [
      'Which lifecycle flow should Product review before changing onboarding?',
      'How did KYC reminder messaging affect conversion?',
      'What audience should be cited in the business PRD?',
    ],
  },
  ga: {
    headline: 'Acquisition, traffic quality, and conversion source context',
    description:
      'Google Analytics connects campaign and channel performance to the product questions being asked in DreamFi.',
    freshness: 'Available as a development preview',
    primaryDataset: 'Acquisition analytics',
    rows: [
      {
        label: 'Organic product traffic',
        value: '+12.4%',
        detail: 'Week-over-week sessions landing on education and onboarding pages.',
      },
      {
        label: 'Paid search conversion',
        value: '3.9%',
        detail: 'Traffic-to-started-KYC conversion for funded-account campaigns.',
      },
      {
        label: 'Top assisted channel',
        value: 'Email',
        detail: 'Highest assisted conversion contribution for returning users.',
      },
    ],
    inspect: [
      {
        title: 'Channel quality',
        detail: 'DreamFi should separate high-intent traffic from vanity traffic before summarizing performance.',
      },
      {
        title: 'Landing-page conversion',
        detail: 'Look at where acquisition traffic turns into actual product movement or dies.',
      },
      {
        title: 'Assist behavior',
        detail: 'Show which channels support conversion even when they are not the final touch.',
      },
    ],
    workflows: [
      {
        title: 'Acquisition narrative',
        detail: 'Build a product-facing explanation of which channels are driving qualified traffic.',
        href: '/console/knowledge/ask?source=ga&q=Which%20channels%20are%20sending%20the%20highest-intent%20onboarding%20traffic%3F',
      },
    ],
    views: ['Acquisition overview', 'Campaign assisted conversion', 'Landing page quality'],
    questions: [
      'Which channel is sending the highest-intent onboarding traffic?',
      'Where do acquisition signals disagree with product analytics?',
      'What channel data belongs in the business PRD?',
    ],
  },
}

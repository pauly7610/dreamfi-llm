import type { ConsoleIntegration } from '../types/console'

export type SourceDataRow = {
  label: string
  value: string
  detail: string
}

export type SourceInspectItem = {
  title: string
  detail: string
}

export type SourceWorkflow = {
  title: string
  detail: string
  href: string
}

export type SourceReviewCase = {
  id: string
  label: string
  status: 'questionable' | 'stepped_up' | 'cleared'
  stage: string
  signal: string
  detail: string
  nextStep: string
  updatedAt: string
}

export type SourceDataPreview = {
  headline: string
  description: string
  freshness: string
  primaryDataset: string
  rows: SourceDataRow[]
  inspect: SourceInspectItem[]
  workflows: SourceWorkflow[]
  views: string[]
  questions: string[]
  reviewCases?: SourceReviewCase[]
}

const sourceDataPreviews: Record<string, SourceDataPreview> = {
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
  jira: {
    headline: 'Delivery state, sprint risk, and shipped-vs-planned reality',
    description:
      'Jira should not just show ticket status. It should help DreamFi compare what Product thinks is done versus what is actually implemented in the codebase.',
    freshness: 'Synced from the development source room',
    primaryDataset: 'Product delivery board',
    rows: [
      {
        label: 'Done tickets missing repo evidence',
        value: '4',
        detail: 'Tickets marked complete in Jira but missing matching code, pull request, or feature-flag evidence.',
      },
      {
        label: 'Done but still behind a flag',
        value: '3',
        detail: 'Tickets marked shipped even though the implementation is still gated or partially rolled out.',
      },
      {
        label: 'Spec/code drift alerts',
        value: '6',
        detail: 'Stories where the PRD, Jira ticket, and current repo behavior appear out of sync.',
      },
    ],
    inspect: [
      {
        title: 'Done vs implemented',
        detail: 'DreamFi should compare completed Jira tasks against commits, PRs, flags, and live behavior.',
      },
      {
        title: 'Completion without docs',
        detail: 'Catch tickets marked done without updated Confluence, PRD, or release evidence.',
      },
      {
        title: 'Roadmap drift',
        detail: 'Flag when Jira delivery state no longer matches Dragonboat priorities or product docs.',
      },
    ],
    workflows: [
      {
        title: 'Done vs codebase audit',
        detail: 'Ask which Jira tickets are complete in planning but not clearly implemented in the repo.',
        href: '/console/knowledge/ask?source=jira&q=Which%20Jira%20tickets%20are%20marked%20done%20but%20not%20implemented%20in%20the%20codebase%3F',
      },
      {
        title: 'Implementation drift brief',
        detail: 'Generate a summary of shipped-vs-planned mismatches for Product and Engineering.',
        href: '/console/generate/technical-prd?source=jira',
      },
    ],
    views: ['Done vs repo evidence', 'Flagged-but-complete work', 'Spec-linked delivery drift'],
    questions: [
      'Which tickets conflict with the current PRD?',
      'What blockers should go into the weekly brief?',
      'Which Jira tickets are marked complete but not implemented in the codebase?',
    ],
  },
  confluence: {
    headline: 'Specs, decisions, product docs, and publish destinations',
    description:
      'Confluence is the durable context layer for decisions DreamFi needs to cite or publish back to the team.',
    freshness: 'Synced from the development source room',
    primaryDataset: 'Product documentation space',
    rows: [
      {
        label: 'Active PRDs',
        value: '9',
        detail: 'Current product requirements docs available for citation.',
      },
      {
        label: 'Decision records',
        value: '23',
        detail: 'Architecture and product decision notes connected to source-room answers.',
      },
      {
        label: 'Recently published brief',
        value: 'Weekly PM Brief',
        detail: 'Latest DreamFi output published back into Confluence.',
      },
    ],
    inspect: [
      {
        title: 'Decision lineage',
        detail: 'Show which product and architecture decisions still govern the current work.',
      },
      {
        title: 'Doc freshness',
        detail: 'Flag when a spec is being cited but has not been updated alongside delivery or metric changes.',
      },
      {
        title: 'Publish destinations',
        detail: 'Make it obvious where DreamFi should write back the generated artifact.',
      },
    ],
    workflows: [
      {
        title: 'Spec recap',
        detail: 'Ask what changed across PRDs and decision docs since the last review.',
        href: '/console/knowledge/ask?source=confluence&q=What%20changed%20in%20the%20product%20docs%20since%20the%20last%20review%3F',
      },
    ],
    views: ['Active PRD shelf', 'Decision records', 'Published DreamFi briefs'],
    questions: [
      'Which docs should be cited for this PRD?',
      'What changed since the last weekly brief?',
      'Where should this generated artifact be published?',
    ],
  },
  socure: {
    headline: 'Identity confidence, fraud risk tiers, and decision reasons',
    description:
      'Socure should help DreamFi explain fraud and identity risk in a way Product can actually use: which users are low, medium, or high risk, and why.',
    freshness: 'Needs attention in the development slice',
    primaryDataset: 'Identity risk decisions',
    rows: [
      {
        label: 'Low-risk approvals',
        value: '82%',
        detail: 'Applicants cleared with strong identity confidence and no meaningful fraud indicators.',
      },
      {
        label: 'Medium-risk review queue',
        value: '11%',
        detail: 'Users likely needing manual review because of partial mismatch, document uncertainty, or thin-file signals.',
      },
      {
        label: 'High-risk fraud tier',
        value: '7%',
        detail: 'Applications with strong synthetic identity, velocity, or repeated device mismatch indicators.',
      },
    ],
    inspect: [
      {
        title: 'Fraud risk by tier',
        detail: 'DreamFi should show how many applicants land in low, medium, and high-risk buckets and what the movement means.',
      },
      {
        title: 'Decision reason codes',
        detail: 'Surface which reasons are driving denials or review holds: velocity, device mismatch, synthetic identity, or document concerns.',
      },
      {
        title: 'Identity confidence vs conversion',
        detail: 'Connect Socure risk signals to funnel drop-off so Product can see where caution is hurting completion.',
      },
    ],
    workflows: [
      {
        title: 'Fraud cluster review',
        detail: 'Ask which risk reasons are driving the newest high-risk cluster.',
        href: '/console/knowledge/ask?source=socure&q=Which%20Socure%20fraud%20signals%20are%20driving%20the%20highest-risk%20cluster%3F',
      },
      {
        title: 'Risk BRD draft',
        detail: 'Turn identity and fraud evidence into a review-ready risk document.',
        href: '/console/generate/risk-brd?source=socure',
      },
    ],
    views: ['Fraud risk tier distribution', 'Top denial reasons', 'Identity confidence trend'],
    questions: [
      'Which Socure signals are driving manual review?',
      'How many users are falling into high-risk fraud buckets?',
      'Where does Socure caution appear to hurt KYC conversion?',
    ],
    reviewCases: [
      {
        id: 'KYC-10421',
        label: 'Questionable device cluster',
        status: 'questionable',
        stage: 'Manual review queue',
        signal: 'Device mismatch across 3 attempts',
        detail: 'Same applicant reused two devices and changed IP region between retries, pushing the case into manual review.',
        nextStep: 'Confirm whether device ownership should trigger a hard step-up.',
        updatedAt: '2 min ago',
      },
      {
        id: 'KYC-10488',
        label: 'Stepped-up document check',
        status: 'stepped_up',
        stage: 'Document + selfie step-up',
        signal: 'Identity confidence dropped after thin-file match',
        detail: 'The applicant matched core PII but landed below the identity-confidence threshold, so Socure requested an extra document check.',
        nextStep: 'Review whether the step-up helped conversion or created avoidable friction.',
        updatedAt: '7 min ago',
      },
      {
        id: 'KYC-10409',
        label: 'Questionable synthetic indicators',
        status: 'questionable',
        stage: 'Fraud analyst review',
        signal: 'Velocity and synthetic identity reasons',
        detail: 'The identity hit multiple consortium signals linked to recent synthetic activity, but the doc score remained borderline.',
        nextStep: 'Decide whether to escalate to fraud ops or lower the manual-review threshold.',
        updatedAt: '13 min ago',
      },
      {
        id: 'KYC-10377',
        label: 'Stepped-up address verification',
        status: 'stepped_up',
        stage: 'Address verification hold',
        signal: 'Address risk + residency mismatch',
        detail: 'The applicant passed name and DOB checks but failed residency confidence, triggering a secondary address step-up.',
        nextStep: 'Check whether this step-up is blocking good users in the current funnel.',
        updatedAt: '19 min ago',
      },
    ],
  },
}

export function getSourceDataPreview(source: ConsoleIntegration): SourceDataPreview {
  const sourcePreview = sourceDataPreviews[source.id]
  if (sourcePreview) {
    return sourcePreview
  }

  return {
    headline: `${source.name} source data preview`,
    description: source.purpose,
    freshness: 'Available in the development source room',
    primaryDataset: `${source.name} workspace`,
    rows: [
      {
        label: 'Connected context',
        value: source.status === 'connected' ? 'Live' : 'Ready',
        detail: 'DreamFi can use this source when gathering evidence for product work.',
      },
      {
        label: 'Artifact coverage',
        value: String(source.used_for.length),
        detail: 'Number of generator workflows that can cite this connector.',
      },
      {
        label: 'Review path',
        value: 'Cited answers',
        detail: 'Answers should show where this source was used before publishing.',
      },
    ],
    inspect: [
      {
        title: 'What this source is good for',
        detail: source.purpose,
      },
      {
        title: 'What DreamFi should verify',
        detail: 'Connector-specific answers should stay grounded in receipts, freshness, and explicit caveats.',
      },
      {
        title: 'How Product should use it',
        detail: 'Use this source to support product questions, then promote the best answers into generated artifacts.',
      },
    ],
    workflows: [
      {
        title: `Ask about ${source.name}`,
        detail: 'Start with a grounded question using this connector as the primary scope.',
        href: `/console/knowledge/ask?source=${source.id}&q=${encodeURIComponent(`What should Product know from ${source.name}?`)}`,
      },
    ],
    views: ['Connector overview', 'Evidence coverage', 'Generator usage'],
    questions: [
      `What should Product know from ${source.name}?`,
      `Which generated artifacts use ${source.name}?`,
      `Where should ${source.name} evidence appear in a brief?`,
    ],
  }
}

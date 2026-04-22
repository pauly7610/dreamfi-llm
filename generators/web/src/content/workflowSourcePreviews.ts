import type { SourceDataPreview } from './sourcePreviewTypes'

export const workflowSourcePreviews: Record<string, SourceDataPreview> = {
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

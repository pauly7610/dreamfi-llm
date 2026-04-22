import type { ConsoleIntegration } from '../types/console'
import type {
  ConnectorWorkspaceSection,
  WorkspaceBoardColumn,
  WorkspaceChartSeries,
  WorkspaceKeyValue,
  WorkspaceMetric,
  WorkspaceRoadmapItem,
  WorkspaceTableRow,
} from '../types/connectorWorkspace'

function jiraColumns(): WorkspaceBoardColumn[] {
  return [
    {
      name: 'To do',
      items: [
        { assignee: 'PM', id: 'KYC-231', title: 'Update retry guidance for identity review' },
        { assignee: 'ENG', id: 'FUND-84', title: 'Instrument missing funding retry event' },
      ],
    },
    {
      name: 'In progress',
      items: [
        { assignee: 'ENG', id: 'KYC-244', title: 'Audit done tickets with missing repo evidence' },
        { assignee: 'DES', id: 'ONB-73', title: 'Revise onboarding empty states for verification' },
      ],
    },
    {
      name: 'Done',
      items: [
        { assignee: 'ENG', id: 'KYC-219', title: 'Reduce false positives in risk retry path' },
        { assignee: 'PM', id: 'OPS-18', title: 'Publish weekly rollout note for KYC fallback' },
      ],
    },
  ]
}

const jiraBurndownSeries: WorkspaceChartSeries[] = [
  {
    name: 'Story points',
    color: 'rgba(12, 102, 228, 0.88)',
    points: [
      { label: 'Mon', value: 34 },
      { label: 'Tue', value: 29 },
      { label: 'Wed', value: 27 },
      { label: 'Thu', value: 20 },
      { label: 'Fri', value: 17 },
      { label: 'Mon', value: 12 },
      { label: 'Today', value: 9 },
    ],
  },
]

const jiraHealthValues: WorkspaceKeyValue[] = [
  { label: 'Scope added', value: '+3 issues' },
  { label: 'WIP limit', value: '6 in progress' },
  { label: 'Review risk', value: '2 done without evidence' },
]

function confluenceTableRows(): WorkspaceTableRow[] {
  return [
    { cells: ['KYC Retry Policy', 'PRD', 'Updated 2h ago'] },
    { cells: ['Identity Decision Notes', 'Decision record', 'Updated yesterday'] },
    { cells: ['Weekly PM Brief', 'Published brief', 'Updated 3 days ago'] },
  ]
}

function dragonboatRows(): WorkspaceTableRow[] {
  return [
    { cells: ['KYC conversion', 'On track', 'Identity flow hardening'] },
    { cells: ['Funding experience', 'Watch', 'Retry handling'] },
    { cells: ['Lifecycle messaging', 'At risk', 'Cross-team dependency'] },
  ]
}

function sardineRows(): WorkspaceTableRow[] {
  return [
    { cells: ['ATO review', 'High risk', 'Escalated'] },
    { cells: ['Behavioral anomaly', 'Medium risk', '2FA suggested'] },
    { cells: ['Connection graph cluster', 'High risk', 'Fraud ring review'] },
  ]
}

function netxdRows(): WorkspaceTableRow[] {
  return [
    { cells: ['ACH deposit', 'Queued', '$14,200'] },
    { cells: ['Debit return', 'Watch', '$980'] },
    { cells: ['Funding transfer', 'Settled', '$6,420'] },
  ]
}

function dragonboatTimeline(): WorkspaceRoadmapItem[] {
  return [
    { title: 'KYC conversion', tone: 'discovery', timeframe: 'Now to Q2' },
    { title: 'Funding experience', tone: 'delivery', timeframe: 'Q2 to Q3' },
    { title: 'Lifecycle messaging', tone: 'risk', timeframe: 'Q3 planning' },
  ]
}

export function operationsSectionsForSource(
  source: ConsoleIntegration,
  highlights: WorkspaceMetric[],
): ConnectorWorkspaceSection[] | null {
  switch (source.id) {
    case 'jira':
      return [
        {
          id: 'source-board',
          label: 'Board',
          eyebrow: 'Board',
          title: 'Current sprint board',
          surface: 'board',
          badges: [
            { label: 'Board' },
            { label: 'Sprint 14' },
            { label: '2 blockers', tone: 'warning' },
          ],
          chart: { ariaLabel: 'Jira sprint burndown', series: jiraBurndownSeries },
          keyValues: jiraHealthValues,
          board: jiraColumns(),
        },
        {
          id: 'source-delivery',
          label: 'Delivery',
          eyebrow: 'Delivery audit',
          title: 'Done vs code reality',
          surface: 'table',
          metrics: highlights,
        },
      ]
    case 'confluence':
      return [
        {
          id: 'source-pages',
          label: 'Pages',
          eyebrow: 'Pages',
          title: 'Space pages and trusted docs',
          surface: 'table',
          table: {
            columns: ['Page', 'Type', 'Freshness'],
            rows: confluenceTableRows(),
          },
        },
        {
          id: 'source-recent',
          label: 'Recent',
          eyebrow: 'Recent updates',
          title: 'Single source of truth',
          surface: 'doc',
          metrics: highlights,
        },
      ]
    case 'dragonboat':
      return [
        {
          id: 'source-roadmap',
          label: 'Roadmap',
          eyebrow: 'Roadmap',
          title: 'Portfolio allocation and initiative health',
          surface: 'table',
          timeline: dragonboatTimeline(),
          table: {
            columns: ['Initiative', 'Health', 'Focus'],
            rows: dragonboatRows(),
          },
        },
        {
          id: 'source-portfolio',
          label: 'Portfolio',
          eyebrow: 'Portfolio intelligence',
          title: 'Demand, resource, and scenario view',
          surface: 'chart',
          metrics: highlights,
        },
      ]
    case 'sardine':
      return [
        {
          id: 'source-cases',
          label: 'Cases',
          eyebrow: 'Cases',
          title: 'Case management queue',
          surface: 'table',
          table: {
            columns: ['Case', 'Risk', 'Disposition'],
            rows: sardineRows(),
          },
        },
        {
          id: 'source-rules',
          label: 'Rules',
          eyebrow: 'Rules and signals',
          title: 'Behavior, connections, and disposition signals',
          surface: 'chart',
          metrics: highlights,
        },
      ]
    case 'netxd':
      return [
        {
          id: 'source-ledger',
          label: 'Ledger',
          eyebrow: 'Ledger',
          title: 'Transaction health and monitor view',
          surface: 'chart',
          metrics: highlights,
        },
        {
          id: 'source-transactions',
          label: 'Transactions',
          eyebrow: 'Transactions',
          title: 'Recent movement',
          surface: 'table',
          table: {
            columns: ['Type', 'Status', 'Amount'],
            rows: netxdRows(),
          },
        },
      ]
    default:
      return null
  }
}

import type { ConsoleIntegration } from '../types/console'
import type {
  ConnectorWorkspaceSection,
  WorkspaceChartPoint,
  WorkspaceChartSeries,
  WorkspaceKeyValue,
  WorkspaceMetric,
  WorkspaceSummaryCard,
  WorkspaceTableRow,
  WorkspaceTextItem,
} from '../types/connectorWorkspace'

function summaryCard(label: string, value: string, detail: string): WorkspaceSummaryCard {
  return { label, value, detail }
}

const posthogTrendSeries: WorkspaceChartSeries[] = [
  {
    name: 'Started KYC',
    color: 'rgba(255, 178, 138, 0.95)',
    points: [
      { label: 'Apr 15', value: 92 },
      { label: 'Apr 16', value: 88 },
      { label: 'Apr 17', value: 95 },
      { label: 'Apr 18', value: 91 },
      { label: 'Apr 19', value: 97 },
      { label: 'Apr 20', value: 93 },
      { label: 'Apr 21', value: 90 },
    ],
  },
  {
    name: 'Completed KYC',
    color: 'rgba(245, 78, 0, 0.95)',
    points: [
      { label: 'Apr 15', value: 74 },
      { label: 'Apr 16', value: 73 },
      { label: 'Apr 17', value: 78 },
      { label: 'Apr 18', value: 70 },
      { label: 'Apr 19', value: 76 },
      { label: 'Apr 20', value: 72 },
      { label: 'Apr 21', value: 68 },
    ],
  },
]

const posthogReplayItems: WorkspaceTextItem[] = [
  { title: '02:14', detail: 'Users retry document upload after copy experiment exposure.' },
  { title: '01:31', detail: 'Funding CTA seen before identity state resolves in the sidebar.' },
  { title: '00:48', detail: 'Second retry correlates with feature-flagged inline helper text.' },
]

const metabaseTrendSeries: WorkspaceChartSeries[] = [
  {
    name: 'KYC conversion',
    color: 'rgba(93, 125, 39, 0.88)',
    points: [
      { label: 'Mon', value: 71 },
      { label: 'Tue', value: 72 },
      { label: 'Wed', value: 74 },
      { label: 'Thu', value: 73 },
      { label: 'Fri', value: 75 },
      { label: 'Sat', value: 74 },
      { label: 'Sun', value: 73 },
    ],
  },
]

const metabaseBars: WorkspaceChartPoint[] = [
  { label: 'Doc', value: 73 },
  { label: 'Plaid', value: 68 },
  { label: 'Retry', value: 54 },
  { label: 'Funding', value: 61 },
]

const klaviyoTrendSeries: WorkspaceChartSeries[] = [
  {
    name: 'Attributed conversions',
    color: 'rgba(20, 122, 98, 0.92)',
    points: [
      { label: 'Week 1', value: 52 },
      { label: 'Week 2', value: 56 },
      { label: 'Week 3', value: 58 },
      { label: 'Week 4', value: 63 },
      { label: 'Week 5', value: 61 },
      { label: 'Week 6', value: 66 },
    ],
  },
]

const klaviyoBars: WorkspaceChartPoint[] = [
  { label: 'Email', value: 62 },
  { label: 'SMS', value: 24 },
  { label: 'Push', value: 14 },
]

const klaviyoSummaryCards: WorkspaceSummaryCard[] = [
  summaryCard('Business performance summary', '$182k', 'Attributed revenue in the last 30 days'),
  summaryCard('Top performing flows', 'Welcome + KYC reminder', 'Highest conversion contribution across onboarding'),
  summaryCard('Recent campaigns', '2 shipped this week', 'Lifecycle nudge and funding education sends'),
]

const gaTrendSeries: WorkspaceChartSeries[] = [
  {
    name: 'Sessions',
    color: 'rgba(26, 115, 232, 0.92)',
    points: [
      { label: 'Apr 15', value: 61 },
      { label: 'Apr 16', value: 64 },
      { label: 'Apr 17', value: 68 },
      { label: 'Apr 18', value: 66 },
      { label: 'Apr 19', value: 71 },
      { label: 'Apr 20', value: 74 },
      { label: 'Apr 21', value: 76 },
    ],
  },
]

const gaRealtimeBars: WorkspaceChartPoint[] = [
  { label: '5m', value: 18 },
  { label: '10m', value: 23 },
  { label: '15m', value: 27 },
  { label: '20m', value: 29 },
  { label: '25m', value: 25 },
  { label: '30m', value: 31 },
]

const gaSummaryCards: WorkspaceSummaryCard[] = [
  summaryCard('New users', '14.2k', '+8.7% vs previous period'),
  summaryCard('Engaged sessions', '6.1k', '53.4% engagement rate'),
  summaryCard('Key events', '1,184', 'KYC start and funding intent combined'),
  summaryCard('Top channel', 'Organic Search', 'Most qualified first-touch source'),
]

const gaRealtimeValues: WorkspaceKeyValue[] = [
  { label: 'Top page', value: '/onboarding/verify' },
  { label: 'Top event', value: 'document_retry' },
  { label: 'Audience', value: 'Returning users' },
]

function metabaseQuestionRows(): WorkspaceTableRow[] {
  return [
    { cells: ['KYC conversion by source', 'Verified', 'Dashboard card'] },
    { cells: ['Funding-ready accounts by cohort', 'Official', 'Saved question'] },
    { cells: ['Retry friction by day', 'Draft', 'SQL question'] },
  ]
}

function klaviyoTableRows(): WorkspaceTableRow[] {
  return [
    { cells: ['Welcome series', 'Email + SMS', 'Live', '9.4% conversion'] },
    { cells: ['KYC reminder', 'Email', 'Live', '6.8% lift'] },
    { cells: ['Browse abandon', 'Email', 'Draft', '3.2% click'] },
  ]
}

function posthogEventRows(): WorkspaceTableRow[] {
  return [
    { cells: ['started_kyc', '12,481', '+4.1%', 'Primary entry'] },
    { cells: ['document_retry', '2,038', '+18.7%', 'Friction spike'] },
    { cells: ['completed_kyc', '8,532', '-2.9%', 'Outcome'] },
    { cells: ['funding_page_view', '3,184', '+6.0%', 'Downstream'] },
  ]
}

function gaRows(): WorkspaceTableRow[] {
  return [
    { cells: ['Paid Search', '3.9%', 'High-intent'] },
    { cells: ['Email', 'Top assist', 'Returning users'] },
    { cells: ['Organic', '+12.4%', 'Education pages'] },
  ]
}

export function analyticsSectionsForSource(
  source: ConsoleIntegration,
  highlights: WorkspaceMetric[],
): ConnectorWorkspaceSection[] | null {
  switch (source.id) {
    case 'posthog':
      return [
        {
          id: 'source-insights',
          label: 'Insights',
          eyebrow: 'Insights',
          title: 'Graphs, trends, and replay context',
          surface: 'dark',
          badges: [
            { label: 'Trends' },
            { label: '7D' },
            { label: 'Breakdown by source' },
          ],
          chart: { ariaLabel: 'PostHog KYC trend', series: posthogTrendSeries },
          darkChart: true,
          textItems: posthogReplayItems,
          metrics: highlights,
        },
        {
          id: 'source-funnel',
          label: 'Funnels',
          eyebrow: 'Funnels',
          title: 'KYC path breakdown',
          surface: 'chart',
          badges: [
            { label: '4-step funnel' },
            { label: '18.7% retry spike', tone: 'warning' },
            { label: 'Flag exposure 42%' },
          ],
          funnelRows: highlights,
        },
        {
          id: 'source-events',
          label: 'Events',
          eyebrow: 'Events',
          title: 'Latest event stream',
          surface: 'table',
          table: {
            columns: ['Event', 'Count', 'Trend', 'Read'],
            rows: posthogEventRows(),
          },
        },
      ]
    case 'metabase':
      return [
        {
          id: 'source-dashboards',
          label: 'Dashboards',
          eyebrow: 'Dashboards',
          title: 'Official KPI boards',
          surface: 'dashboard',
          collection: {
            title: 'Product KPIs',
            subtitle: 'Official collection · 3 verified dashboards · 9 saved questions',
            badges: [
              { label: 'Official' },
              { label: 'Verified items', tone: 'success' },
            ],
          },
          metrics: highlights,
          chart: { ariaLabel: 'Metabase KYC conversion trend', series: metabaseTrendSeries },
          barChart: {
            ariaLabel: 'Metabase stage completion bars',
            bars: metabaseBars,
            color: 'linear-gradient(180deg, rgba(252, 211, 77, 0.85), rgba(93, 125, 39, 0.92))',
          },
        },
        {
          id: 'source-questions',
          label: 'Questions',
          eyebrow: 'Questions',
          title: 'Verified questions in this collection',
          surface: 'table',
          table: {
            columns: ['Question', 'Status', 'Type'],
            rows: metabaseQuestionRows(),
          },
        },
      ]
    case 'klaviyo':
      return [
        {
          id: 'source-flows',
          label: 'Flows',
          eyebrow: 'Flows',
          title: 'Flow library and current performance',
          surface: 'table',
          rows: klaviyoSummaryCards,
          table: {
            columns: ['Flow', 'Channel', 'Status', 'Outcome'],
            rows: klaviyoTableRows(),
          },
        },
        {
          id: 'source-performance',
          label: 'Performance',
          eyebrow: 'Analytics snapshot',
          title: 'Flow performance and audience lift',
          surface: 'chart',
          chart: { ariaLabel: 'Klaviyo attributed conversions trend', series: klaviyoTrendSeries },
          barChart: {
            ariaLabel: 'Klaviyo channel contribution',
            bars: klaviyoBars,
            color: 'linear-gradient(180deg, rgba(92, 221, 170, 0.88), rgba(20, 122, 98, 0.94))',
          },
          metrics: highlights,
        },
      ]
    case 'ga':
      return [
        {
          id: 'source-snapshot',
          label: 'Snapshot',
          eyebrow: 'Reports snapshot',
          title: 'Acquisition overview',
          surface: 'chart',
          rows: gaSummaryCards,
          chart: { ariaLabel: 'Google Analytics sessions overview trend', series: gaTrendSeries },
          metrics: highlights,
        },
        {
          id: 'source-realtime',
          label: 'Realtime',
          eyebrow: 'Realtime',
          title: 'Channels and active sessions',
          surface: 'table',
          barChart: {
            ariaLabel: 'Google Analytics active users last 30 minutes',
            bars: gaRealtimeBars,
            color: 'linear-gradient(180deg, rgba(141, 182, 255, 0.9), rgba(26, 115, 232, 0.95))',
          },
          keyValues: gaRealtimeValues,
          table: {
            columns: ['Channel', 'Signal', 'Read'],
            rows: gaRows(),
          },
        },
      ]
    default:
      return null
  }
}

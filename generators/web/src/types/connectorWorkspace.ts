import type { IntegrationStatus } from './console'

export type WorkspaceBadge = {
  label: string
  tone?: 'default' | 'success' | 'warning'
}

export type WorkspaceMetric = {
  label: string
  value: string
  detail: string
}

export type WorkspaceChartPoint = {
  label: string
  value: number
}

export type WorkspaceChartSeries = {
  color: string
  name: string
  points: WorkspaceChartPoint[]
}

export type WorkspaceKeyValue = {
  label: string
  value: string
}

export type WorkspaceSummaryCard = {
  label: string
  value: string
  detail: string
}

export type WorkspaceTextItem = {
  detail: string
  title: string
}

export type WorkspaceBoardItem = {
  assignee: string
  id: string
  title: string
}

export type WorkspaceBoardColumn = {
  items: WorkspaceBoardItem[]
  name: string
}

export type WorkspaceTableRow = {
  cells: string[]
}

export type WorkspaceRoadmapItem = {
  timeframe: string
  title: string
  tone: 'discovery' | 'delivery' | 'risk'
}

export type WorkspaceCollection = {
  badges: WorkspaceBadge[]
  subtitle: string
  title: string
}

export type WorkspaceInspectItem = {
  detail: string
  title: string
}

export type WorkspaceWorkflow = {
  detail: string
  href: string
  title: string
}

export type WorkspaceReviewCase = {
  detail: string
  id: string
  label: string
  nextStep: string
  signal: string
  stage: string
  status: 'questionable' | 'stepped_up' | 'cleared'
  updatedAt: string
}

export type ConnectorWorkspaceSection = {
  badges?: WorkspaceBadge[]
  board?: WorkspaceBoardColumn[]
  collection?: WorkspaceCollection
  darkChart?: boolean
  funnelRows?: WorkspaceMetric[]
  id: string
  keyValues?: WorkspaceKeyValue[]
  label: string
  metrics?: WorkspaceMetric[]
  rows?: WorkspaceSummaryCard[]
  surface: 'board' | 'chart' | 'dark' | 'dashboard' | 'doc' | 'table'
  table?: {
    columns: string[]
    rows: WorkspaceTableRow[]
  }
  textItems?: WorkspaceTextItem[]
  timeline?: WorkspaceRoadmapItem[]
  title: string
  chart?: {
    ariaLabel: string
    series: WorkspaceChartSeries[]
  }
  barChart?: {
    ariaLabel: string
    bars: WorkspaceChartPoint[]
    color: string
  }
  eyebrow: string
}

export type ConnectorWorkspacePayload = {
  connector: {
    description: string
    freshness: string
    headline: string
    id: string
    name: string
    primaryDataset: string
    purpose: string
    status: IntegrationStatus
    workspaceDescription: string
    workspaceTitle: string
  }
  highlights: WorkspaceMetric[]
  inspect: WorkspaceInspectItem[]
  questions: string[]
  reviewCases?: WorkspaceReviewCase[]
  sections: ConnectorWorkspaceSection[]
  views: string[]
  workflows: WorkspaceWorkflow[]
}

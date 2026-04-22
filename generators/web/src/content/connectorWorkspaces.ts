import { analyticsSectionsForSource } from './connectorWorkspaceAnalyticsSections'
import { workspaceDescriptionForSource, workspaceTitleForSource } from './connectorWorkspaceMetadata'
import { operationsSectionsForSource } from './connectorWorkspaceOperationsSections'
import { getSourceDataPreview } from './sourceDataPreviews'
import type { ConsoleIntegration } from '../types/console'
import type { ConnectorWorkspacePayload, ConnectorWorkspaceSection, WorkspaceMetric } from '../types/connectorWorkspace'

function metric(label: string, value: string, detail: string): WorkspaceMetric {
  return { label, value, detail }
}

function genericSections(source: ConsoleIntegration, highlights: WorkspaceMetric[]): ConnectorWorkspaceSection[] {
  return [
    {
      id: 'source-overview',
      label: 'Overview',
      eyebrow: 'Overview',
      title: workspaceTitleForSource(source),
      surface: 'table',
      metrics: highlights,
    },
  ]
}

function sectionsForSource(source: ConsoleIntegration, highlights: WorkspaceMetric[]): ConnectorWorkspaceSection[] {
  return (
    analyticsSectionsForSource(source, highlights) ??
    operationsSectionsForSource(source, highlights) ??
    genericSections(source, highlights)
  )
}

export function getConnectorWorkspace(source: ConsoleIntegration): ConnectorWorkspacePayload {
  const preview = getSourceDataPreview(source)
  const highlights = preview.rows.map((row) => metric(row.label, row.value, row.detail))

  return {
    connector: {
      description: preview.description,
      freshness: preview.freshness,
      headline: preview.headline,
      id: source.id,
      name: source.name,
      primaryDataset: preview.primaryDataset,
      purpose: source.purpose,
      status: source.status,
      workspaceDescription: workspaceDescriptionForSource(source, preview.description),
      workspaceTitle: workspaceTitleForSource(source),
    },
    highlights,
    inspect: preview.inspect,
    questions: preview.questions,
    reviewCases: preview.reviewCases,
    sections: sectionsForSource(source, highlights),
    views: preview.views,
    workflows: preview.workflows,
  }
}

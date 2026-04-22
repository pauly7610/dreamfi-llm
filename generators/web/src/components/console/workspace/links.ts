import type { ConnectorWorkspacePayload, ConnectorWorkspaceSection } from '../../../types/connectorWorkspace'

export function askHref(sourceId: string, question: string): string {
  return `/console/knowledge/ask?source=${sourceId}&q=${encodeURIComponent(question)}`
}

export function rowQuestion(sourceName: string, label: string): string {
  return `What should Product know about ${label} in ${sourceName}?`
}

export function sectionById(
  workspace: ConnectorWorkspacePayload,
  sectionId: string,
): ConnectorWorkspaceSection | null {
  return workspace.sections.find((section) => section.id === sectionId) ?? null
}

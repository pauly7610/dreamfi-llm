import { sectionById } from './links'
import { ConnectorWorkspaceShell } from './shell'
import type { WorkspaceRendererProps } from './types'
import { LinkedTable, MetricsStrip, PanelHeading } from './primitives'

export function renderConfluenceWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const pagesSection = sectionById(workspace, 'source-pages')
  const recentSection = sectionById(workspace, 'source-recent')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Confluence-style workspace"
      outerClassName="connector-workspace-confluence"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-confluence"
      workspace={workspace}
    >
      {pagesSection?.table ? (
        <section id={pagesSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={pagesSection.eyebrow} title={pagesSection.title} />
          <LinkedTable sourceId={sourceId} sourceName={sourceName} table={pagesSection.table} />
        </section>
      ) : null}

      {recentSection?.metrics ? (
        <section id={recentSection.id} className="connector-doc-panel">
          <PanelHeading eyebrow={recentSection.eyebrow} title={recentSection.title} />
          <MetricsStrip metrics={recentSection.metrics} sourceId={sourceId} sourceName={sourceName} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderGenericWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  return (
    <ConnectorWorkspaceShell
      eyebrow="Connector workspace"
      outerClassName={`connector-workspace-${workspace.connector.id}`}
      relatedTopics={relatedTopics}
      showNavigation={false}
      showStatus={false}
      workspace={workspace}
    >
      <MetricsStrip
        metrics={workspace.highlights}
        sourceId={workspace.connector.id}
        sourceName={workspace.connector.name}
      />
    </ConnectorWorkspaceShell>
  )
}

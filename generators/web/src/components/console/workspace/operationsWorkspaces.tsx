import { askHref, sectionById } from './links'
import { ConnectorWorkspaceShell } from './shell'
import type { WorkspaceRendererProps } from './types'
import { AreaTrendChart } from './charts'
import { DashboardBadge, KeyValueList, LinkedTable, MetricsStrip, PanelHeading, Roadmap } from './primitives'

export function renderJiraWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const boardSection = sectionById(workspace, 'source-board')
  const deliverySection = sectionById(workspace, 'source-delivery')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Atlassian-style workspace"
      outerClassName="connector-workspace-jira"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-jira"
      workspace={workspace}
    >
      {boardSection ? (
        <section id={boardSection.id} className="connector-board-panel">
          <PanelHeading eyebrow={boardSection.eyebrow} title={boardSection.title} />
          {boardSection.badges ? (
            <div className="jira-board-toolbar">
              <div className="jira-toolbar-group">
                {boardSection.badges.map((badge) => (
                  <DashboardBadge key={badge.label} tone={badge.tone}>
                    {badge.label}
                  </DashboardBadge>
                ))}
              </div>
              <div className="jira-toolbar-group">
                <span>Only my issues</span>
                <span>Assignee</span>
                <span>Epic</span>
              </div>
            </div>
          ) : null}
          <div className="jira-insight-grid">
            {boardSection.chart ? (
              <article className="jira-insight-card">
                <PanelHeading compact eyebrow="Insights" title="Sprint burndown" />
                <AreaTrendChart ariaLabel={boardSection.chart.ariaLabel} series={boardSection.chart.series} />
              </article>
            ) : null}
            {boardSection.keyValues ? (
              <article className="jira-insight-card">
                <PanelHeading compact eyebrow="Sprint health" title="Current delivery posture" />
                <KeyValueList items={boardSection.keyValues} />
              </article>
            ) : null}
          </div>
          {boardSection.board ? (
            <div className="jira-board-columns">
              {boardSection.board.map((column) => (
                <article key={column.name} className="jira-board-column">
                  <header>{column.name}</header>
                  <div>
                    {column.items.map((item) => (
                      <a
                        key={item.id}
                        className="jira-issue-card"
                        href={askHref(sourceId, `What does ${item.id} mean for Product, and is it actually implemented?`)}
                      >
                        <strong>{item.id}</strong>
                        <p>{item.title}</p>
                        <small>{item.assignee}</small>
                      </a>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {deliverySection?.metrics ? (
        <section id={deliverySection.id} className="connector-table-panel">
          <PanelHeading eyebrow={deliverySection.eyebrow} title={deliverySection.title} />
          <MetricsStrip
            metrics={deliverySection.metrics}
            sourceId={workspace.connector.id}
            sourceName={workspace.connector.name}
          />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderDragonboatWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const roadmapSection = sectionById(workspace, 'source-roadmap')
  const portfolioSection = sectionById(workspace, 'source-portfolio')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Dragonboat-style workspace"
      outerClassName="connector-workspace-dragonboat"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-dragonboat"
      workspace={workspace}
    >
      {roadmapSection ? (
        <section id={roadmapSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={roadmapSection.eyebrow} title={roadmapSection.title} />
          {roadmapSection.timeline ? <Roadmap items={roadmapSection.timeline} /> : null}
          {roadmapSection.table ? (
            <LinkedTable sourceId={sourceId} sourceName={sourceName} table={roadmapSection.table} />
          ) : null}
        </section>
      ) : null}

      {portfolioSection?.metrics ? (
        <section id={portfolioSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={portfolioSection.eyebrow} title={portfolioSection.title} />
          <MetricsStrip metrics={portfolioSection.metrics} sourceId={sourceId} sourceName={sourceName} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderSardineWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const casesSection = sectionById(workspace, 'source-cases')
  const rulesSection = sectionById(workspace, 'source-rules')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Sardine-style workspace"
      outerClassName="connector-workspace-sardine"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-sardine"
      workspace={workspace}
    >
      {casesSection?.table ? (
        <section id={casesSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={casesSection.eyebrow} title={casesSection.title} />
          <LinkedTable sourceId={sourceId} sourceName={sourceName} table={casesSection.table} />
        </section>
      ) : null}

      {rulesSection?.metrics ? (
        <section id={rulesSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={rulesSection.eyebrow} title={rulesSection.title} />
          <MetricsStrip metrics={rulesSection.metrics} sourceId={sourceId} sourceName={sourceName} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderNetxdWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const ledgerSection = sectionById(workspace, 'source-ledger')
  const transactionsSection = sectionById(workspace, 'source-transactions')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Payments operations workspace"
      outerClassName="connector-workspace-netxd"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-netxd"
      workspace={workspace}
    >
      {ledgerSection?.metrics ? (
        <section id={ledgerSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={ledgerSection.eyebrow} title={ledgerSection.title} />
          <MetricsStrip metrics={ledgerSection.metrics} sourceId={sourceId} sourceName={sourceName} />
        </section>
      ) : null}

      {transactionsSection?.table ? (
        <section id={transactionsSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={transactionsSection.eyebrow} title={transactionsSection.title} />
          <LinkedTable sourceId={sourceId} sourceName={sourceName} table={transactionsSection.table} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

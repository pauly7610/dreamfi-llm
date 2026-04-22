import { askHref, rowQuestion, sectionById } from './links'
import { ConnectorWorkspaceShell } from './shell'
import type { WorkspaceRendererProps } from './types'
import { AreaTrendChart, ColumnBarsChart } from './charts'
import {
  DashboardBadge,
  KeyValueList,
  LinkedTable,
  MetricsStrip,
  PanelHeading,
  SummaryCards,
  TextList,
} from './primitives'

export function renderPosthogWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const insightsSection = sectionById(workspace, 'source-insights')
  const funnelSection = sectionById(workspace, 'source-funnel')
  const eventsSection = sectionById(workspace, 'source-events')

  return (
    <ConnectorWorkspaceShell
      eyebrow="PostHog-style workspace"
      outerClassName="connector-workspace-posthog"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-posthog"
      workspace={workspace}
    >
      {insightsSection ? (
        <section id={insightsSection.id} className="connector-dark-panel">
          <PanelHeading eyebrow={insightsSection.eyebrow} title={insightsSection.title} />
          {insightsSection.badges ? (
            <div className="posthog-toolbar">
              <div className="posthog-toolbar-group">
                {insightsSection.badges.map((badge) => (
                  <DashboardBadge key={badge.label} tone={badge.tone}>
                    {badge.label}
                  </DashboardBadge>
                ))}
              </div>
              <div className="posthog-toolbar-group">
                <span>started_kyc</span>
                <span>completed_kyc</span>
                <span>Formula</span>
              </div>
            </div>
          ) : null}
          <div className="posthog-insight-layout">
            {insightsSection.chart ? (
              <article className="posthog-visual-card">
                <PanelHeading compact eyebrow="Conversion trend" title="KYC completion versus entry volume" />
                <AreaTrendChart ariaLabel={insightsSection.chart.ariaLabel} dark series={insightsSection.chart.series} />
                <div className="chart-legend">
                  {insightsSection.chart.series.map((entry) => (
                    <span key={entry.name}>
                      <i style={{ background: entry.color }} />
                      {entry.name}
                    </span>
                  ))}
                </div>
              </article>
            ) : null}
            {insightsSection.textItems ? (
              <article className="posthog-replay-card">
                <PanelHeading compact eyebrow="Session replay" title="Recent friction callouts" />
                <TextList items={insightsSection.textItems} />
              </article>
            ) : null}
          </div>
          {insightsSection.metrics ? (
            <MetricsStrip metrics={insightsSection.metrics} sourceId={sourceId} sourceName={sourceName} />
          ) : null}
        </section>
      ) : null}

      {funnelSection ? (
        <section id={funnelSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={funnelSection.eyebrow} title={funnelSection.title} />
          {funnelSection.badges ? (
            <div className="posthog-funnel-summary">
              {funnelSection.badges.map((badge) => (
                <DashboardBadge key={badge.label} tone={badge.tone}>
                  {badge.label}
                </DashboardBadge>
              ))}
            </div>
          ) : null}
          <div className="posthog-funnel-list">
            {(funnelSection.funnelRows ?? []).map((row, index) => (
              <a key={row.label} className="posthog-funnel-link" href={askHref(sourceId, rowQuestion(sourceName, row.label))}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <strong>{row.label}</strong>
                <div className={`posthog-bar bar-${index + 1}`} />
                <b>{row.value}</b>
              </a>
            ))}
          </div>
        </section>
      ) : null}

      {eventsSection?.table ? (
        <section id={eventsSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={eventsSection.eyebrow} title={eventsSection.title} />
          <LinkedTable sourceId={sourceId} sourceName={sourceName} table={eventsSection.table} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderMetabaseWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const dashboardsSection = sectionById(workspace, 'source-dashboards')
  const questionsSection = sectionById(workspace, 'source-questions')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Metabase-style workspace"
      outerClassName="connector-workspace-metabase"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-metabase"
      workspace={workspace}
    >
      {dashboardsSection ? (
        <section id={dashboardsSection.id} className="connector-dashboard-panel">
          <PanelHeading eyebrow={dashboardsSection.eyebrow} title={dashboardsSection.title} />
          {dashboardsSection.collection ? (
            <div className="metabase-collection-strip">
              <div className="metabase-collection-copy">
                <strong>{dashboardsSection.collection.title}</strong>
                <small>{dashboardsSection.collection.subtitle}</small>
              </div>
              <div className="metabase-collection-badges">
                {dashboardsSection.collection.badges.map((badge) => (
                  <DashboardBadge key={badge.label} tone={badge.tone}>
                    {badge.label}
                  </DashboardBadge>
                ))}
              </div>
            </div>
          ) : null}
          {dashboardsSection.metrics ? (
            <MetricsStrip metrics={dashboardsSection.metrics} sourceId={sourceId} sourceName={sourceName} />
          ) : null}
          <div className="metabase-chart-grid">
            {dashboardsSection.chart ? (
              <article className="metabase-dashboard-card wide">
                <PanelHeading compact eyebrow="Verified dashboard card" title="KYC conversion funnel" />
                <AreaTrendChart ariaLabel={dashboardsSection.chart.ariaLabel} series={dashboardsSection.chart.series} />
              </article>
            ) : null}
            {dashboardsSection.barChart ? (
              <article className="metabase-dashboard-card">
                <PanelHeading compact eyebrow="Breakdown" title="Stage completion" />
                <ColumnBarsChart
                  ariaLabel={dashboardsSection.barChart.ariaLabel}
                  bars={dashboardsSection.barChart.bars}
                  color={dashboardsSection.barChart.color}
                />
              </article>
            ) : null}
          </div>
        </section>
      ) : null}

      {questionsSection?.table ? (
        <section id={questionsSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={questionsSection.eyebrow} title={questionsSection.title} />
          <LinkedTable sourceId={sourceId} sourceName={sourceName} table={questionsSection.table} />
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderKlaviyoWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const flowsSection = sectionById(workspace, 'source-flows')
  const performanceSection = sectionById(workspace, 'source-performance')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Klaviyo-style workspace"
      outerClassName="connector-workspace-klaviyo"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-klaviyo"
      workspace={workspace}
    >
      {flowsSection ? (
        <section id={flowsSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={flowsSection.eyebrow} title={flowsSection.title} />
          {flowsSection.rows ? <SummaryCards items={flowsSection.rows} /> : null}
          {flowsSection.table ? (
            <LinkedTable sourceId={sourceId} sourceName={sourceName} table={flowsSection.table} />
          ) : null}
        </section>
      ) : null}

      {performanceSection ? (
        <section id={performanceSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={performanceSection.eyebrow} title={performanceSection.title} />
          <div className="klaviyo-performance-layout">
            {performanceSection.chart ? (
              <article className="klaviyo-performance-card wide">
                <PanelHeading compact eyebrow="30-day analytics snapshot" title="Attributed conversions by week" />
                <AreaTrendChart ariaLabel={performanceSection.chart.ariaLabel} series={performanceSection.chart.series} />
              </article>
            ) : null}
            {performanceSection.barChart ? (
              <article className="klaviyo-performance-card">
                <PanelHeading compact eyebrow="Channel mix" title="Contribution by channel" />
                <ColumnBarsChart
                  ariaLabel={performanceSection.barChart.ariaLabel}
                  bars={performanceSection.barChart.bars}
                  color={performanceSection.barChart.color}
                />
              </article>
            ) : null}
          </div>
          {performanceSection.metrics ? (
            <MetricsStrip metrics={performanceSection.metrics} sourceId={sourceId} sourceName={sourceName} />
          ) : null}
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

export function renderGaWorkspace({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name
  const snapshotSection = sectionById(workspace, 'source-snapshot')
  const realtimeSection = sectionById(workspace, 'source-realtime')

  return (
    <ConnectorWorkspaceShell
      eyebrow="Google Analytics-style workspace"
      outerClassName="connector-workspace-ga"
      relatedTopics={relatedTopics}
      shellClassName="connector-shell-ga"
      workspace={workspace}
    >
      {snapshotSection ? (
        <section id={snapshotSection.id} className="connector-chart-panel">
          <PanelHeading eyebrow={snapshotSection.eyebrow} title={snapshotSection.title} />
          {snapshotSection.rows ? <SummaryCards items={snapshotSection.rows} /> : null}
          {snapshotSection.chart ? (
            <article className="ga-overview-chart-card">
              <PanelHeading compact eyebrow="Overview report" title="Sessions and conversion signal" />
              <AreaTrendChart ariaLabel={snapshotSection.chart.ariaLabel} series={snapshotSection.chart.series} />
            </article>
          ) : null}
          {snapshotSection.metrics ? (
            <MetricsStrip metrics={snapshotSection.metrics} sourceId={sourceId} sourceName={sourceName} />
          ) : null}
        </section>
      ) : null}

      {realtimeSection ? (
        <section id={realtimeSection.id} className="connector-table-panel">
          <PanelHeading eyebrow={realtimeSection.eyebrow} title={realtimeSection.title} />
          <div className="ga-realtime-layout">
            {realtimeSection.barChart ? (
              <article className="ga-realtime-card">
                <PanelHeading compact eyebrow="Last 30 minutes" title="Active users" />
                <ColumnBarsChart
                  ariaLabel={realtimeSection.barChart.ariaLabel}
                  bars={realtimeSection.barChart.bars}
                  color={realtimeSection.barChart.color}
                />
              </article>
            ) : null}
            {realtimeSection.keyValues ? (
              <article className="ga-realtime-card">
                <PanelHeading compact eyebrow="Realtime cards" title="Immediate signals" />
                <KeyValueList items={realtimeSection.keyValues} />
              </article>
            ) : null}
          </div>
          {realtimeSection.table ? (
            <LinkedTable sourceId={sourceId} sourceName={sourceName} table={realtimeSection.table} />
          ) : null}
        </section>
      ) : null}
    </ConnectorWorkspaceShell>
  )
}

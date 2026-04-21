import type { ProductTopic } from '../../fixtures/productTopics'
import type { SourceDataPreview } from '../../fixtures/sourceDataPreviews'
import type { ConsoleIntegration } from '../../types/console'

type ConnectorWorkspaceProps = {
  preview: SourceDataPreview
  relatedTopics: ProductTopic[]
  source: ConsoleIntegration
}

type WorkspaceLink = {
  href: string
  label: string
}

type WorkspaceStatus = {
  label: string
  tone: 'active' | 'neutral' | 'warning'
}

type BoardColumn = {
  name: string
  items: {
    assignee: string
    id: string
    title: string
  }[]
}

type TableRow = {
  cells: string[]
}

function navLinksForSource(source: ConsoleIntegration): WorkspaceLink[] {
  switch (source.id) {
    case 'jira':
      return [
        { href: '#source-board', label: 'Board' },
        { href: '#source-delivery', label: 'Delivery' },
        { href: '#source-context', label: 'Context' },
      ]
    case 'posthog':
      return [
        { href: '#source-insights', label: 'Insights' },
        { href: '#source-funnel', label: 'Funnels' },
        { href: '#source-events', label: 'Events' },
      ]
    case 'metabase':
      return [
        { href: '#source-dashboards', label: 'Dashboards' },
        { href: '#source-questions', label: 'Questions' },
        { href: '#source-context', label: 'Collections' },
      ]
    case 'klaviyo':
      return [
        { href: '#source-flows', label: 'Flows' },
        { href: '#source-performance', label: 'Performance' },
        { href: '#source-context', label: 'Segments' },
      ]
    case 'confluence':
      return [
        { href: '#source-pages', label: 'Pages' },
        { href: '#source-recent', label: 'Recent' },
        { href: '#source-context', label: 'Space' },
      ]
    case 'ga':
      return [
        { href: '#source-snapshot', label: 'Snapshot' },
        { href: '#source-realtime', label: 'Realtime' },
        { href: '#source-context', label: 'Reports' },
      ]
    case 'dragonboat':
      return [
        { href: '#source-roadmap', label: 'Roadmap' },
        { href: '#source-portfolio', label: 'Portfolio' },
        { href: '#source-context', label: 'Allocation' },
      ]
    case 'sardine':
      return [
        { href: '#source-cases', label: 'Cases' },
        { href: '#source-rules', label: 'Rules' },
        { href: '#source-context', label: 'Signals' },
      ]
    case 'netxd':
      return [
        { href: '#source-ledger', label: 'Ledger' },
        { href: '#source-transactions', label: 'Transactions' },
        { href: '#source-context', label: 'Monitors' },
      ]
    default:
      return [
        { href: '#source-overview', label: 'Overview' },
        { href: '#source-context', label: 'Context' },
      ]
  }
}

function panelTitleForSource(source: ConsoleIntegration): string {
  switch (source.id) {
    case 'jira':
      return 'Delivery board'
    case 'posthog':
      return 'Product analytics'
    case 'metabase':
      return 'Dashboard collection'
    case 'klaviyo':
      return 'Lifecycle workspace'
    case 'confluence':
      return 'Knowledge space'
    case 'ga':
      return 'Reports snapshot'
    case 'dragonboat':
      return 'Portfolio planner'
    case 'sardine':
      return 'Risk operations'
    case 'netxd':
      return 'Transaction monitor'
    default:
      return `${source.name} workspace`
  }
}

function panelDescriptionForSource(source: ConsoleIntegration, preview: SourceDataPreview): string {
  switch (source.id) {
    case 'jira':
      return 'Review work as issues move across the board, then audit whether done work is really implemented.'
    case 'posthog':
      return 'Analyze product behavior using insight tabs, funnel breakdowns, and an event stream.'
    case 'metabase':
      return 'Open an official dashboard, inspect the verified questions behind it, and drill into the governed metric layer.'
    case 'klaviyo':
      return 'Check flow health, message performance, and lifecycle segments in one marketing workspace.'
    case 'confluence':
      return 'Browse the knowledge space the way Product would: recent pages, trusted docs, and structured page hierarchy.'
    case 'ga':
      return 'Start from the reports snapshot, then drop into realtime acquisition and event signals.'
    case 'dragonboat':
      return 'Plan and track initiatives like a portfolio layer sitting on top of delivery systems.'
    case 'sardine':
      return 'Review active fraud cases, risk rules, and signal coverage the way a modern risk ops team would.'
    case 'netxd':
      return 'Inspect payments, ledger movement, and queue monitors the way a transaction operations console would.'
    default:
      return preview.description
  }
}

function statusTone(status: ConsoleIntegration['status']): WorkspaceStatus['tone'] {
  if (status === 'degraded' || status === 'not_configured') {
    return 'warning'
  }
  if (status === 'available') {
    return 'neutral'
  }
  return 'active'
}

function statusSummary(source: ConsoleIntegration, preview: SourceDataPreview): WorkspaceStatus[] {
  return [
    { label: preview.freshness, tone: statusTone(source.status) },
    { label: preview.primaryDataset, tone: 'neutral' },
    { label: source.status === 'connected' ? 'Live source' : source.status === 'available' ? 'Preview source' : 'Needs review', tone: statusTone(source.status) },
  ]
}

function topicsBlock(relatedTopics: ProductTopic[]) {
  if (relatedTopics.length === 0) {
    return null
  }

  return (
    <section className="connector-topic-block">
      <span className="eyebrow">Connected rooms</span>
      <div className="connector-topic-list">
        {relatedTopics.map((topic) => (
          <a key={topic.id} href={`/console/topics/${topic.id}`}>
            <strong>{topic.title}</strong>
            <small>{topic.question}</small>
          </a>
        ))}
      </div>
    </section>
  )
}

function workflowBlock(preview: SourceDataPreview) {
  return (
    <section className="connector-topic-block">
      <span className="eyebrow">Useful actions</span>
      <div className="connector-topic-list">
        {preview.workflows.map((workflow) => (
          <a key={workflow.title} href={workflow.href}>
            <strong>{workflow.title}</strong>
            <small>{workflow.detail}</small>
          </a>
        ))}
      </div>
    </section>
  )
}

function contextRail(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <aside id="source-context" className="connector-context-rail">
      <section className="connector-topic-block">
        <span className="eyebrow">In scope</span>
        <div className="connector-chip-row">
          {preview.views.map((view) => (
            <span key={view} className="connector-chip">
              {view}
            </span>
          ))}
        </div>
      </section>
      <section className="connector-topic-block">
        <span className="eyebrow">What Product should inspect</span>
        <div className="connector-note-list">
          {preview.inspect.map((item) => (
            <article key={item.title}>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>
      {topicsBlock(relatedTopics)}
      {workflowBlock(preview)}
      <section className="connector-topic-block">
        <span className="eyebrow">Question to start with</span>
        <p className="connector-side-question">{preview.questions[0] ?? `What should Product know from ${source.name}?`}</p>
      </section>
    </aside>
  )
}

function metricsStrip(preview: SourceDataPreview) {
  return (
    <div className="connector-metric-strip">
      {preview.rows.map((row) => (
        <article key={row.label}>
          <span>{row.label}</span>
          <strong>{row.value}</strong>
          <p>{row.detail}</p>
        </article>
      ))}
    </div>
  )
}

function jiraColumns(): BoardColumn[] {
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

function jiraWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  const columns = jiraColumns()

  return (
    <section id="source-data" className="connector-workspace connector-workspace-jira panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Atlassian-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-jira">
        <div className="connector-main">
          <section id="source-board" className="connector-board-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Board</span>
              <h3>Current sprint board</h3>
            </div>
            <div className="jira-board-columns">
              {columns.map((column) => (
                <article key={column.name} className="jira-board-column">
                  <header>{column.name}</header>
                  <div>
                    {column.items.map((item) => (
                      <section key={item.id} className="jira-issue-card">
                        <strong>{item.id}</strong>
                        <p>{item.title}</p>
                        <small>{item.assignee}</small>
                      </section>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
          <section id="source-delivery" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Delivery audit</span>
              <h3>Done vs code reality</h3>
            </div>
            {metricsStrip(preview)}
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function posthogEventRows(): TableRow[] {
  return [
    { cells: ['started_kyc', '12,481', '+4.1%', 'Primary entry'] },
    { cells: ['document_retry', '2,038', '+18.7%', 'Friction spike'] },
    { cells: ['completed_kyc', '8,532', '-2.9%', 'Outcome'] },
    { cells: ['funding_page_view', '3,184', '+6.0%', 'Downstream'] },
  ]
}

function posthogWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-posthog panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">PostHog-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-posthog">
        <div className="connector-main">
          <section id="source-insights" className="connector-dark-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Insights</span>
              <h3>Graphs, trends, and replay context</h3>
            </div>
            {metricsStrip(preview)}
          </section>
          <section id="source-funnel" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Funnels</span>
              <h3>KYC path breakdown</h3>
            </div>
            <div className="posthog-funnel-list">
              {preview.rows.map((row, index) => (
                <article key={row.label}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <strong>{row.label}</strong>
                  <div className={`posthog-bar bar-${index + 1}`} />
                  <b>{row.value}</b>
                </article>
              ))}
            </div>
          </section>
          <section id="source-events" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Events</span>
              <h3>Latest event stream</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Count</th>
                  <th>Trend</th>
                  <th>Read</th>
                </tr>
              </thead>
              <tbody>
                {posthogEventRows().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function metabaseQuestions(): TableRow[] {
  return [
    { cells: ['KYC conversion by source', 'Verified', 'Dashboard card'] },
    { cells: ['Funding-ready accounts by cohort', 'Official', 'Saved question'] },
    { cells: ['Retry friction by day', 'Draft', 'SQL question'] },
  ]
}

function metabaseWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-metabase panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Metabase-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-metabase">
        <div className="connector-main">
          <section id="source-dashboards" className="connector-dashboard-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Dashboards</span>
              <h3>Official KPI boards</h3>
            </div>
            {metricsStrip(preview)}
            <div className="metabase-chart-grid">
              <article className="metabase-chart-card chart-area" />
              <article className="metabase-chart-card chart-bars" />
            </div>
          </section>
          <section id="source-questions" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Questions</span>
              <h3>Verified questions in this collection</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Status</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {metabaseQuestions().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function klaviyoRows(): TableRow[] {
  return [
    { cells: ['Welcome series', 'Email + SMS', 'Live', '9.4% conversion'] },
    { cells: ['KYC reminder', 'Email', 'Live', '6.8% lift'] },
    { cells: ['Browse abandon', 'Email', 'Draft', '3.2% click'] },
  ]
}

function klaviyoWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-klaviyo panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Klaviyo-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-klaviyo">
        <div className="connector-main">
          <section id="source-flows" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Flows</span>
              <h3>Flow library and current performance</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Flow</th>
                  <th>Channel</th>
                  <th>Status</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {klaviyoRows().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section id="source-performance" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Analytics snapshot</span>
              <h3>Flow performance and audience lift</h3>
            </div>
            {metricsStrip(preview)}
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function confluencePages(): TableRow[] {
  return [
    { cells: ['KYC Retry Policy', 'PRD', 'Updated 2h ago'] },
    { cells: ['Identity Decision Notes', 'Decision record', 'Updated yesterday'] },
    { cells: ['Weekly PM Brief', 'Published brief', 'Updated 3 days ago'] },
  ]
}

function confluenceWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-confluence panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Confluence-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-confluence">
        <div className="connector-main">
          <section id="source-pages" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Pages</span>
              <h3>Space pages and trusted docs</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Type</th>
                  <th>Freshness</th>
                </tr>
              </thead>
              <tbody>
                {confluencePages().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section id="source-recent" className="connector-doc-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Recent updates</span>
              <h3>Single source of truth</h3>
            </div>
            {metricsStrip(preview)}
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function gaRows(): TableRow[] {
  return [
    { cells: ['Paid Search', '3.9%', 'High-intent'] },
    { cells: ['Email', 'Top assist', 'Returning users'] },
    { cells: ['Organic', '+12.4%', 'Education pages'] },
  ]
}

function gaWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-ga panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Google Analytics-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-ga">
        <div className="connector-main">
          <section id="source-snapshot" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Reports snapshot</span>
              <h3>Acquisition overview</h3>
            </div>
            {metricsStrip(preview)}
          </section>
          <section id="source-realtime" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Realtime</span>
              <h3>Channels and active sessions</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Signal</th>
                  <th>Read</th>
                </tr>
              </thead>
              <tbody>
                {gaRows().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function dragonboatPortfolio(): TableRow[] {
  return [
    { cells: ['KYC conversion', 'On track', 'Identity flow hardening'] },
    { cells: ['Funding experience', 'Watch', 'Retry handling'] },
    { cells: ['Lifecycle messaging', 'At risk', 'Cross-team dependency'] },
  ]
}

function dragonboatWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-dragonboat panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Dragonboat-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-dragonboat">
        <div className="connector-main">
          <section id="source-roadmap" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Roadmap</span>
              <h3>Portfolio allocation and initiative health</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Initiative</th>
                  <th>Health</th>
                  <th>Focus</th>
                </tr>
              </thead>
              <tbody>
                {dragonboatPortfolio().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section id="source-portfolio" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Portfolio intelligence</span>
              <h3>Demand, resource, and scenario view</h3>
            </div>
            {metricsStrip(preview)}
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function sardineCases(): TableRow[] {
  return [
    { cells: ['ATO review', 'High risk', 'Escalated'] },
    { cells: ['Behavioral anomaly', 'Medium risk', '2FA suggested'] },
    { cells: ['Connection graph cluster', 'High risk', 'Fraud ring review'] },
  ]
}

function sardineWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-sardine panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Sardine-style workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-sardine">
        <div className="connector-main">
          <section id="source-cases" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Cases</span>
              <h3>Case management queue</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Risk</th>
                  <th>Disposition</th>
                </tr>
              </thead>
              <tbody>
                {sardineCases().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section id="source-rules" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Rules and signals</span>
              <h3>Behavior, connections, and disposition signals</h3>
            </div>
            {metricsStrip(preview)}
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function netxdTransactions(): TableRow[] {
  return [
    { cells: ['ACH deposit', 'Queued', '$14,200'] },
    { cells: ['Debit return', 'Watch', '$980'] },
    { cells: ['Funding transfer', 'Settled', '$6,420'] },
  ]
}

function netxdWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className="connector-workspace connector-workspace-netxd panel">
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Payments operations workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
        <nav className="connector-workspace-tabs" aria-label={`${source.name} workspace sections`}>
          {navLinksForSource(source).map((link) => (
            <a key={link.label} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="connector-status-row">
        {statusSummary(source, preview).map((item) => (
          <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
            {item.label}
          </span>
        ))}
      </div>
      <div className="connector-shell connector-shell-netxd">
        <div className="connector-main">
          <section id="source-ledger" className="connector-chart-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Ledger</span>
              <h3>Transaction health and monitor view</h3>
            </div>
            {metricsStrip(preview)}
          </section>
          <section id="source-transactions" className="connector-table-panel">
            <div className="connector-panel-heading">
              <span className="eyebrow">Transactions</span>
              <h3>Recent movement</h3>
            </div>
            <table className="connector-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {netxdTransactions().map((row) => (
                  <tr key={row.cells[0]}>
                    {row.cells.map((cell) => (
                      <td key={cell}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function genericWorkspace(source: ConsoleIntegration, preview: SourceDataPreview, relatedTopics: ProductTopic[]) {
  return (
    <section id="source-data" className={`connector-workspace connector-workspace-${source.id} panel`}>
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">Connector workspace</span>
          <h2>{panelTitleForSource(source)}</h2>
          <p>{panelDescriptionForSource(source, preview)}</p>
        </div>
      </div>
      <div className="connector-shell">
        <div className="connector-main">{metricsStrip(preview)}</div>
        {contextRail(source, preview, relatedTopics)}
      </div>
    </section>
  )
}

function ConnectorWorkspace({ preview, relatedTopics, source }: ConnectorWorkspaceProps) {
  switch (source.id) {
    case 'jira':
      return jiraWorkspace(source, preview, relatedTopics)
    case 'posthog':
      return posthogWorkspace(source, preview, relatedTopics)
    case 'metabase':
      return metabaseWorkspace(source, preview, relatedTopics)
    case 'klaviyo':
      return klaviyoWorkspace(source, preview, relatedTopics)
    case 'confluence':
      return confluenceWorkspace(source, preview, relatedTopics)
    case 'ga':
      return gaWorkspace(source, preview, relatedTopics)
    case 'dragonboat':
      return dragonboatWorkspace(source, preview, relatedTopics)
    case 'sardine':
      return sardineWorkspace(source, preview, relatedTopics)
    case 'netxd':
      return netxdWorkspace(source, preview, relatedTopics)
    default:
      return genericWorkspace(source, preview, relatedTopics)
  }
}

export default ConnectorWorkspace

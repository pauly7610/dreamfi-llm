import type {
  ConnectorWorkspaceSection,
  WorkspaceKeyValue,
  WorkspaceMetric,
  WorkspaceRoadmapItem,
  WorkspaceSummaryCard,
  WorkspaceTableRow,
  WorkspaceTextItem,
} from '../../../types/connectorWorkspace'
import { askHref, rowQuestion } from './links'

export function DashboardBadge({
  children,
  tone = 'default',
}: {
  children: string
  tone?: 'default' | 'success' | 'warning'
}) {
  return <span className={`dashboard-badge tone-${tone}`}>{children}</span>
}

export function KeyValueList({ items }: { items: WorkspaceKeyValue[] }) {
  return (
    <dl className="key-value-list">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function PanelHeading({
  eyebrow,
  title,
  compact = false,
}: {
  compact?: boolean
  eyebrow: string
  title: string
}) {
  return (
    <div className={`connector-panel-heading${compact ? ' compact' : ''}`}>
      <span className="eyebrow">{eyebrow}</span>
      <h3>{title}</h3>
    </div>
  )
}

export function MetricsStrip({
  sourceId,
  sourceName,
  metrics,
}: {
  metrics: WorkspaceMetric[]
  sourceId: string
  sourceName: string
}) {
  return (
    <div className="connector-metric-strip">
      {metrics.map((row) => (
        <a key={row.label} className="connector-metric-link" href={askHref(sourceId, rowQuestion(sourceName, row.label))}>
          <span>{row.label}</span>
          <strong>{row.value}</strong>
          <p>{row.detail}</p>
        </a>
      ))}
    </div>
  )
}

export function SummaryCards({ items }: { items: WorkspaceSummaryCard[] }) {
  return (
    <div className={items.length === 4 ? 'ga-overview-grid' : 'klaviyo-home-strip'}>
      {items.map((item) => (
        <article key={item.label} className={items.length === 4 ? 'ga-summary-card' : ''}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.detail}</small>
        </article>
      ))}
    </div>
  )
}

export function TextList({ items }: { items: WorkspaceTextItem[] }) {
  return (
    <div className="posthog-replay-list">
      {items.map((item) => (
        <div key={item.title}>
          <strong>{item.title}</strong>
          <p>{item.detail}</p>
        </div>
      ))}
    </div>
  )
}

export function Roadmap({ items }: { items: WorkspaceRoadmapItem[] }) {
  return (
    <div className="dragonboat-roadmap">
      {items.map((item) => (
        <article key={item.title}>
          <strong>{item.title}</strong>
          <div>
            <span className={`phase-${item.tone}`} />
          </div>
          <small>{item.timeframe}</small>
        </article>
      ))}
    </div>
  )
}

function linkedTableBody(sourceId: string, sourceName: string, rows: WorkspaceTableRow[]) {
  return rows.map((row) => (
    <tr key={row.cells[0]}>
      {row.cells.map((cell, index) => (
        <td key={cell}>
          {index === 0 ? (
            <a className="connector-table-link" href={askHref(sourceId, rowQuestion(sourceName, cell))}>
              {cell}
            </a>
          ) : (
            cell
          )}
        </td>
      ))}
    </tr>
  ))
}

export function LinkedTable({
  sourceId,
  sourceName,
  table,
}: {
  sourceId: string
  sourceName: string
  table: NonNullable<ConnectorWorkspaceSection['table']>
}) {
  return (
    <table className="connector-table">
      <thead>
        <tr>
          {table.columns.map((column) => (
            <th key={column}>{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>{linkedTableBody(sourceId, sourceName, table.rows)}</tbody>
    </table>
  )
}

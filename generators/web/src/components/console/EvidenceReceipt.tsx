import type { ConsoleIntegration } from '../../types/console'
import ConnectorLogo from './ConnectorLogo'

type EvidenceReceiptProps = {
  sources: ConsoleIntegration[]
  gaps?: string[]
  title?: string
  compact?: boolean
}

function EvidenceReceipt({
  sources,
  gaps = [],
  title = 'Evidence receipt',
  compact = false,
}: EvidenceReceiptProps) {
  if (sources.length === 0 && gaps.length === 0) {
    return null
  }

  return (
    <aside className={`evidence-receipt panel${compact ? ' compact' : ''}`}>
      <span className="eyebrow">{title}</span>
      <div className="receipt-source-list">
        {sources.map((source) => (
          <a key={source.id} className="receipt-source" href={source.href}>
            <ConnectorLogo id={source.id} name={source.name} />
            <span>
              <strong>{source.name}</strong>
              <small>{source.status === 'connected' ? 'Live source' : 'Context available'}</small>
            </span>
          </a>
        ))}
      </div>
      {gaps.length > 0 ? (
        <div className="receipt-gaps">
          <strong>Known limits</strong>
          {gaps.map((gap) => (
            <p key={gap}>{gap}</p>
          ))}
        </div>
      ) : null}
    </aside>
  )
}

export default EvidenceReceipt

import type { ConsoleAlert } from '../../types/console'
import { formatDate } from './formatters'

type AlertsPanelProps = {
  alerts: ConsoleAlert[]
}

function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <section className="alerts-panel panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Alerts</span>
          <h2>What needs attention now</h2>
        </div>
      </div>
      <div className="alerts-list">
        {alerts.length ? (
          alerts.map((alert) => (
            <article key={alert.id} className={`alert-row ${alert.severity}`}>
              <div>
                <strong>{alert.title}</strong>
                <p>{alert.message}</p>
              </div>
              <div className="alert-meta">
                <span className={`status-badge ${alert.severity}`}>{alert.severity}</span>
                {alert.href ? <a href={alert.href}>Open</a> : null}
                <time>{formatDate(alert.created_at)}</time>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state compact">
            <h3>No active alerts</h3>
            <p>Recent outputs are not raising operator-visible alert conditions.</p>
          </div>
        )}
      </div>
    </section>
  )
}

export default AlertsPanel

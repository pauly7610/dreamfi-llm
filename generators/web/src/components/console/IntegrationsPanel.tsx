import type { ConsoleIntegration, IntegrationCategory } from '../../types/console'

type IntegrationsPanelProps = {
  items: ConsoleIntegration[]
  title?: string
  description?: string
}

const CATEGORY_LABEL: Record<IntegrationCategory, string> = {
  planning: 'Planning',
  docs: 'Docs',
  metrics: 'Metrics',
  product_analytics: 'Product analytics',
  marketing_analytics: 'Marketing analytics',
  marketing: 'Marketing',
  payments: 'Payments',
  risk: 'Risk',
  identity: 'Identity',
}

const STATUS_LABEL: Record<ConsoleIntegration['status'], string> = {
  connected: 'Connected',
  degraded: 'Degraded',
  available: 'Available',
  not_configured: 'Not configured',
}

const ACTION_LABEL: Record<string, string> = {
  'weekly-brief': 'Weekly brief',
  'technical-prd': 'Technical PRD',
  'business-prd': 'Business PRD',
  'risk-brd': 'Risk BRD',
}

function IntegrationsPanel({
  items,
  title = 'Grounding sources',
  description = 'Where DreamFi pulls signal from to generate PRDs, briefs, and trust-scored artifacts.',
}: IntegrationsPanelProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section className="integrations-panel panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Integrations</span>
          <h2>{title}</h2>
          <p className="section-subtle">{description}</p>
        </div>
        <a className="text-link" href="/console/integrations">Manage connections</a>
      </div>
      <div className="integration-grid">
        {items.map((item) => (
          <article key={item.id} className={`integration-card status-${item.status}`}>
            <header>
              <strong>{item.name}</strong>
              <span className={`status-pill status-${item.status}`}>{STATUS_LABEL[item.status]}</span>
            </header>
            <span className="metric-label">{CATEGORY_LABEL[item.category]}</span>
            <p>{item.purpose}</p>
            {item.used_for.length > 0 ? (
              <ul className="integration-uses">
                {item.used_for.map((use) => (
                  <li key={use}>{ACTION_LABEL[use] ?? use}</li>
                ))}
              </ul>
            ) : null}
            <a className="text-link" href={item.href}>Configure</a>
          </article>
        ))}
      </div>
    </section>
  )
}

export default IntegrationsPanel

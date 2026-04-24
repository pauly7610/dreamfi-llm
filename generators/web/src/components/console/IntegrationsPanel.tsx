import type { ConsoleIntegration, IntegrationCategory } from '../../types/console'
import ConnectorLogo from './ConnectorLogo'

type IntegrationsPanelProps = {
  items: ConsoleIntegration[]
  title?: string
  description?: string
}

const STATUS_LABEL: Record<ConsoleIntegration['status'], string> = {
  connected: 'Live',
  degraded: 'Needs attention',
  available: 'Ready',
  not_configured: 'Setup needed',
}

const SOURCE_GROUPS: Array<{
  id: string
  title: string
  description: string
  categories: IntegrationCategory[]
}> = [
  {
    id: 'planning-docs',
    title: 'Planning + docs',
    description: 'Roadmaps, tickets, and specs Product checks before making a call.',
    categories: ['planning', 'docs'],
  },
  {
    id: 'metrics-growth',
    title: 'Metrics + growth',
    description: 'Funnels, dashboards, campaigns, and user behavior.',
    categories: ['metrics', 'product_analytics', 'marketing_analytics', 'marketing'],
  },
  {
    id: 'risk-money',
    title: 'Risk + money',
    description: 'Payments, identity, fraud, and review queues.',
    categories: ['payments', 'risk', 'identity'],
  },
]

function integrationGroups(items: ConsoleIntegration[]) {
  const grouped = SOURCE_GROUPS
    .map((group) => ({
      ...group,
      items: items.filter((item) => group.categories.includes(item.category)),
    }))
    .filter((group) => group.items.length > 0)
  const groupedIds = new Set(grouped.flatMap((group) => group.items.map((item) => item.id)))
  const otherItems = items.filter((item) => !groupedIds.has(item.id))

  if (otherItems.length === 0) {
    return grouped
  }

  return [
    ...grouped,
    {
      id: 'other',
      title: 'Other sources',
      description: 'Additional systems available to the product source room.',
      categories: [] as IntegrationCategory[],
      items: otherItems,
    },
  ]
}

function IntegrationsPanel({
  items,
  title = 'Browse the sources Product can inspect.',
  description = 'Open a connector to see what DreamFi can use right now.',
}: IntegrationsPanelProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section id="sources" className="integrations-panel panel">
      <div
        className="section-heading inline"
        style={{
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '18px 24px',
        }}
      >
        <div
          style={{
            flex: '1 1 560px',
            minWidth: 0,
            maxWidth: 760,
          }}
        >
          <span className="eyebrow">Integrations</span>
          <h2
            style={{
              margin: '10px 0 8px',
              maxWidth: '15ch',
              fontSize: 'clamp(2rem, 3.1vw, 3.15rem)',
              letterSpacing: '-0.05em',
              lineHeight: 1.02,
            }}
          >
            {title}
          </h2>
          <p
            className="section-subtle"
            style={{
              margin: 0,
              fontSize: '1rem',
              lineHeight: 1.55,
              maxWidth: '44ch',
            }}
          >
            {description}
          </p>
        </div>
        <a
          className="text-link"
          href="/console/integrations"
          style={{
            flex: '0 0 auto',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            minHeight: 44,
            padding: '0 16px',
            borderRadius: 999,
            border: '1px solid rgba(15, 159, 154, 0.16)',
            background: 'rgba(255, 255, 255, 0.66)',
            boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.75)',
            whiteSpace: 'nowrap',
          }}
        >
          Open source directory
          <span aria-hidden="true">→</span>
        </a>
      </div>
      <div className="source-choice-strip" aria-label="How to use the source room">
        <span>
          <strong>1</strong>
          Pick a connector
        </span>
        <span>
          <strong>2</strong>
          View its data slice
        </span>
        <span>
          <strong>3</strong>
          Ask or generate with citations
        </span>
      </div>
      <div className="source-map-grid">
        {integrationGroups(items).map((group) => (
          <article key={group.id} className="source-map-lane">
            <header>
              <div>
                <h3>{group.title}</h3>
                <p>{group.description}</p>
              </div>
              <span className="source-count">{group.items.length}</span>
            </header>
            <div className="source-chip-list">
              {group.items.map((item) => (
                <a key={item.id} className={`source-chip status-${item.status}`} href={item.href}>
                  <ConnectorLogo id={item.id} name={item.name} />
                  <span>
                    <strong>{item.name}</strong>
                    <small>
                      View data · {STATUS_LABEL[item.status]} · {item.purpose}
                    </small>
                  </span>
                  <span className="source-chip-arrow" aria-hidden="true">Open</span>
                </a>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default IntegrationsPanel

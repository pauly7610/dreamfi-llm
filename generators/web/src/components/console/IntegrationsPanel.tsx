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

function setupLabel(item: ConsoleIntegration): string {
  return item.setup_method ?? (item.connection_method === 'onyx_native' ? 'Onyx native connector' : 'Custom ingestion')
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
  title = 'Browse evidence-producing sources.',
  description = 'Open a source to inspect what its current information says and where it can support a decision.',
}: IntegrationsPanelProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section id="sources" className="integrations-panel panel">
      <div className="section-heading inline integrations-panel-header">
        <div className="integrations-panel-copy">
          <span className="eyebrow">Sources</span>
          <h2 className="integrations-panel-title">{title}</h2>
          <p className="section-subtle integrations-panel-description">{description}</p>
        </div>
        <a className="text-link integrations-panel-cta" href="/console/integrations">
          Open source directory
          <span aria-hidden="true">-&gt;</span>
        </a>
      </div>
      <div className="source-choice-strip" aria-label="How to use the source room">
        <span>
          <strong>1</strong>
          Pick a source
        </span>
        <span>
          <strong>2</strong>
          Review current signal
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
                      {item.purpose} - {setupLabel(item)} - {STATUS_LABEL[item.status]}
                    </small>
                  </span>
                  <span className="source-chip-arrow" aria-hidden="true">
                    Open
                  </span>
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

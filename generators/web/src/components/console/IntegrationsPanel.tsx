import type { ConsoleIntegration, IntegrationCategory } from '../../types/console'
import ConnectorIcon from './ConnectorLogo'

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
  connected: 'Live',
  degraded: 'Needs attention',
  available: 'Ready',
  not_configured: 'Setup needed',
}

const ACTION_LABEL: Record<string, string> = {
  'weekly-brief': 'Weekly brief',
  'technical-prd': 'Technical PRD',
  'business-prd': 'Business PRD',
  'risk-brd': 'Risk BRD',
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
    description: 'Roadmap, tickets, specs, and source-of-truth product docs.',
    categories: ['planning', 'docs'],
  },
  {
    id: 'metrics-growth',
    title: 'Metrics + growth',
    description: 'Behavior, funnels, acquisition, lifecycle, and KPI context.',
    categories: ['metrics', 'product_analytics', 'marketing_analytics', 'marketing'],
  },
  {
    id: 'risk-money',
    title: 'Risk + money',
    description: 'Payments, identity, KYC, fraud, and risk-review evidence.',
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
  title = 'Shared connector space',
  description = 'The product department source room: planning, docs, analytics, risk, identity, and payment context in one evidence-backed surface.',
}: IntegrationsPanelProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section id="sources" className="integrations-panel panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Integrations</span>
          <h2>{title}</h2>
          <p className="section-subtle">{description}</p>
        </div>
        <a className="text-link" href="/console/integrations">Open source directory</a>
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
                  <ConnectorIcon id={item.id} name={item.name} />
                  <span>
                    <strong>{item.name}</strong>
                    <small>
                      View data · {STATUS_LABEL[item.status]} · {CATEGORY_LABEL[item.category]}
                    </small>
                  </span>
                  <span className="source-chip-arrow" aria-hidden="true">Open</span>
                </a>
              ))}
            </div>
            <div className="source-lane-uses">
              {Array.from(new Set(group.items.flatMap((item) => item.used_for))).slice(0, 4).map((use) => (
                <span key={use}>{ACTION_LABEL[use] ?? use}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default IntegrationsPanel

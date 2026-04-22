import ConnectorLogo from '../components/console/ConnectorLogo'
import ConnectorWorkspace from '../components/console/ConnectorWorkspace'
import SocureWorkspace from '../components/console/SocureWorkspace'
import { getConnectorWorkspace } from '../content/connectorWorkspaces'
import { topicsForSource } from '../content/productTopics'
import type { ConsoleIntegration, ConsolePayload, IntegrationCategory } from '../types/console'

type SourceDetailPageProps = {
  data: ConsolePayload | null
  sourceId: string | null
}

type SourceActionContent = {
  heroEyebrow: string
  heroTags: string[]
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
  available: 'Ready to connect',
  not_configured: 'Setup needed',
}

function actionContentForSource(source: ConsoleIntegration): SourceActionContent {
  if (source.id === 'socure') {
    return {
      heroEyebrow: 'Identity and risk workspace',
      heroTags: ['Decision layer', 'Explainability', 'Case management'],
    }
  }

  if (source.id === 'jira') {
    return {
      heroEyebrow: 'Atlassian delivery workspace',
      heroTags: ['Boards', 'Issues', 'Automations'],
    }
  }

  if (source.id === 'posthog') {
    return {
      heroEyebrow: 'PostHog analytics workspace',
      heroTags: ['Insights', 'Funnels', 'Events'],
    }
  }

  if (source.id === 'metabase') {
    return {
      heroEyebrow: 'Metabase collections workspace',
      heroTags: ['Dashboards', 'Official collections', 'Verified questions'],
    }
  }

  if (source.id === 'klaviyo') {
    return {
      heroEyebrow: 'Klaviyo lifecycle workspace',
      heroTags: ['Flows', 'Campaign analytics', 'Segments'],
    }
  }

  if (source.id === 'confluence') {
    return {
      heroEyebrow: 'Confluence knowledge workspace',
      heroTags: ['Pages', 'Knowledge base', 'Live docs'],
    }
  }

  if (source.id === 'ga') {
    return {
      heroEyebrow: 'Google Analytics workspace',
      heroTags: ['Reports snapshot', 'Realtime', 'Collections'],
    }
  }

  if (source.id === 'dragonboat') {
    return {
      heroEyebrow: 'Dragonboat portfolio workspace',
      heroTags: ['Roadmaps', 'Outcomes', 'Portfolio'],
    }
  }

  if (source.id === 'sardine') {
    return {
      heroEyebrow: 'Sardine risk workspace',
      heroTags: ['Case management', 'Rules engine', 'Connections graph'],
    }
  }

  if (source.id === 'netxd') {
    return {
      heroEyebrow: 'Payments operations workspace',
      heroTags: ['Monitors', 'Settlement', 'Operations'],
    }
  }

  return {
    heroEyebrow: `${CATEGORY_LABEL[source.category]} source`,
    heroTags: [],
  }
}

function Breadcrumbs({ source }: { source?: ConsoleIntegration }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <a href="/console">Product Source Room</a>
      <span aria-hidden="true">/</span>
      <a href="/console/integrations">Sources</a>
      {source ? (
        <>
          <span aria-hidden="true">/</span>
          <span>{source.name}</span>
        </>
      ) : null}
    </nav>
  )
}

function SourceDirectory({ data }: { data: ConsolePayload | null }) {
  const integrations = data?.integrations ?? []

  return (
    <div className="page-grid source-detail-page">
      <Breadcrumbs />
      <section className="source-detail-hero panel">
        <div>
          <span className="eyebrow">Source directory</span>
          <h2>Choose a connector to inspect its data slice.</h2>
          <p>
            This is the calmer version of the source room: pick a system, see what DreamFi can gather from it, then
            ask or generate with that evidence.
          </p>
        </div>
      </section>
      <section className="source-directory-panel panel" aria-label="Available sources">
        {integrations.map((source) => (
          <a key={source.id} className="source-directory-row" href={source.href}>
            <ConnectorLogo id={source.id} name={source.name} />
            <span>
              <strong>{source.name}</strong>
              <small>
                {STATUS_LABEL[source.status]} · {CATEGORY_LABEL[source.category]}
              </small>
            </span>
            <p>{source.purpose}</p>
            <b>View data</b>
          </a>
        ))}
      </section>
    </div>
  )
}

function SourceNotFound() {
  return (
    <div className="page-grid source-detail-page">
      <Breadcrumbs />
      <section className="empty-state panel">
        <span className="eyebrow">Source not found</span>
        <h2>This connector is not in the current source-room slice.</h2>
        <p>Head back to the source directory and choose one of the available product systems.</p>
        <a className="button secondary" href="/console/integrations">Back to sources</a>
      </section>
    </div>
  )
}

function SourceDetailPage({ data, sourceId }: SourceDetailPageProps) {
  if (!sourceId) {
    return <SourceDirectory data={data} />
  }

  const source = data?.integrations.find((item) => item.id === sourceId)
  if (!source) {
    return <SourceNotFound />
  }

  const workspace = getConnectorWorkspace(source)
  const relatedTopics = topicsForSource(source.id)
  const actionContent = actionContentForSource(source)
  const heroDescription = workspace.connector.description

  return (
    <div className={`page-grid source-detail-page source-page-${source.id}`}>
      <Breadcrumbs source={source} />
      <section className="source-detail-hero panel">
        <div className="source-detail-heading">
          <ConnectorLogo id={source.id} name={source.name} size="large" />
          <div>
            <span className="eyebrow">{actionContent.heroEyebrow}</span>
            <h2>{source.name}</h2>
            <p>{heroDescription}</p>
            {actionContent.heroTags.length > 0 ? (
              <div className="source-brand-strip" aria-label={`${source.name} design cues`}>
                {actionContent.heroTags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        <aside className={`source-status-card status-${source.status}`}>
          <span>Status</span>
          <strong>{STATUS_LABEL[source.status]}</strong>
          <small>{workspace.connector.freshness}</small>
        </aside>
      </section>

      {source.id === 'socure' ? (
        <SocureWorkspace workspace={workspace} relatedTopics={relatedTopics} />
      ) : (
        <ConnectorWorkspace workspace={workspace} relatedTopics={relatedTopics} />
      )}
    </div>
  )
}

export default SourceDetailPage

import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import ConnectorCoveragePanel from '../components/console/ConnectorCoveragePanel'
import ConnectorLogo from '../components/console/ConnectorLogo'
import EvidenceReceipt from '../components/console/EvidenceReceipt'
import WorkflowSnapshotPanel from '../components/console/WorkflowSnapshotPanel'
import { productTopics, topicById } from '../content/productTopics'
import type { ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from '../utils/consoleRoutes'

type TopicRoomPageProps = {
  data: ConsolePayload | null
  topicId: string | null
}

function sourcesForTopic(topic: ProductTopic, integrations: ConsoleIntegration[]): ConsoleIntegration[] {
  return topic.sources
    .map((sourceId) => integrations.find((source) => source.id === sourceId))
    .filter((source): source is ConsoleIntegration => Boolean(source))
}

function signalHref(sourceId?: string): string | null {
  if (!sourceId) {
    return null
  }

  return `/console/integrations/${sourceId}#source-data`
}

function metricHref(sourceId?: string): string | null {
  return signalHref(sourceId)
}

function TopicDirectory({ data }: { data: ConsolePayload | null }) {
  const integrations = data?.integrations ?? []

  return (
    <div className="page-grid topic-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console">Product Source Room</a>
        <span aria-hidden="true">/</span>
        <span>Topics</span>
      </nav>
      <section className="topic-hero panel">
        <span className="eyebrow">Problem rooms</span>
        <h2>Choose the product question before choosing the tool.</h2>
        <p>
          Topics gather sources, evidence, gaps, and generated work around recurring Product decisions like KYC,
          onboarding, funding, and lifecycle messaging.
        </p>
      </section>
      <section className="topic-directory panel" aria-label="Topic rooms">
        {productTopics.map((topic) => {
          const topicSources = sourcesForTopic(topic, integrations).slice(0, 5)
          return (
            <a key={topic.id} className="topic-directory-row" href={`/console/topics/${topic.id}`}>
              <span>
                <strong>{topic.title}</strong>
                <small>{topic.summary}</small>
              </span>
              <span className="topic-source-stack" aria-label={`${topic.title} evidence sources`}>
                {topicSources.map((source) => (
                  <ConnectorLogo key={source.id} id={source.id} name={source.name} />
                ))}
              </span>
              <b>Open room</b>
            </a>
          )
        })}
      </section>
    </div>
  )
}

function TopicNotFound() {
  return (
    <div className="page-grid topic-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console">Product Source Room</a>
        <span aria-hidden="true">/</span>
        <a href="/console/topics">Topics</a>
      </nav>
      <section className="empty-state panel">
        <span className="eyebrow">Topic not found</span>
        <h2>This product room is not in the current development slice.</h2>
        <p>Head back to the topic directory and choose one of the available rooms.</p>
        <a className="button secondary" href="/console/topics">Back to topics</a>
      </section>
    </div>
  )
}

function TopicRoomPage({ data, topicId }: TopicRoomPageProps) {
  const { buildAskHref, buildGenerateHref } = useConsoleWorkspace()

  if (!topicId) {
    return <TopicDirectory data={data} />
  }

  const topic = topicById(topicId)
  if (!topic) {
    return <TopicNotFound />
  }

  const integrations = data?.integrations ?? []
  const topicSources = sourcesForTopic(topic, integrations)
  const workflow = workflowByTopicId(topic.id)
  const recommendedGeneratorSlug = topic.defaultGeneratorSlug ?? 'weekly-brief'
  const recommendedGeneratorTitle = generatorTitleFromSlug(recommendedGeneratorSlug)
  const askHref = buildAskHref({ question: topic.question, topicId: topic.id })
  const generateHref = buildGenerateHref(recommendedGeneratorSlug, {
    question: topic.question,
    topicId: topic.id,
  })

  return (
    <div className="page-grid topic-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console">Product Source Room</a>
        <span aria-hidden="true">/</span>
        <a href="/console/topics">Topics</a>
        <span aria-hidden="true">/</span>
        <span>{topic.title}</span>
      </nav>

      <section className="topic-hero panel">
        <span className="eyebrow">Product intelligence room</span>
        <h2>{topic.title}</h2>
        <p>{topic.summary}</p>
        <div className="hero-actions">
          <a className="button primary" href={askHref}>
            Ask about this topic
          </a>
          <a className="button secondary" href={generateHref}>Generate {recommendedGeneratorTitle}</a>
        </div>
        <div className="topic-topline-strip" aria-label="Top line metrics">
          {topic.toplineMetrics.map((metric) => {
            const href = metricHref(metric.sourceId)
            const content = (
              <>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <small>{metric.detail}</small>
              </>
            )

            if (!href) {
              return (
                <div key={metric.label} className="topic-topline-metric">
                  {content}
                </div>
              )
            }

            return (
              <a key={metric.label} className="topic-topline-metric topic-topline-link" href={href}>
                {content}
              </a>
            )
          })}
        </div>
      </section>

      {workflow ? (
        <section className="topic-workflow-grid">
          <WorkflowSnapshotPanel workflow={workflow} />
          <div className="topic-evidence-rail">
            <EvidenceReceipt sources={topicSources} gaps={topic.gaps} />
            <ConnectorCoveragePanel workflow={workflow} integrations={integrations} />
          </div>
        </section>
      ) : (
        <section className="topic-workspace-grid">
          <EvidenceReceipt sources={topicSources} gaps={topic.gaps} />
        </section>
      )}

      <article className="topic-signal-panel panel">
        <span className="eyebrow">Current signals</span>
        <h2>{topic.question}</h2>
        <div className="topic-signal-list">
          {topic.signals.map((signal) => {
            const href = signalHref(signal.sourceId)
            const content = (
              <>
                <span>{signal.label}</span>
                <strong>{signal.value}</strong>
                <p>{signal.detail}</p>
              </>
            )

            if (!href) {
              return (
                <div key={signal.label} className="topic-signal-row">
                  {content}
                </div>
              )
            }

            return (
              <a key={signal.label} className="topic-signal-row topic-signal-link" href={href}>
                {content}
              </a>
            )
          })}
        </div>
      </article>

      <section className="topic-output-panel panel">
        <div>
          <span className="eyebrow">Product outputs</span>
          <h2>Work this room can produce</h2>
        </div>
        <div className="topic-output-list">
          {topic.artifacts.map((artifact) => {
            const slug = generatorSlugFromIdentifier(artifact)
            return (
              <a
                key={artifact}
                href={buildGenerateHref(slug, {
                  question: topic.question,
                  topicId: topic.id,
                })}
              >
                {artifact}
              </a>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default TopicRoomPage

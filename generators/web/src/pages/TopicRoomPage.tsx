import ConnectorIcon from '../components/console/ConnectorLogo'
import EvidenceReceipt from '../components/console/EvidenceReceipt'
import { productTopics, topicById } from '../fixtures/productTopics'
import type { ProductTopic } from '../fixtures/productTopics'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'

type TopicRoomPageProps = {
  data: ConsolePayload | null
  topicId: string | null
}

function sourcesForTopic(topic: ProductTopic, integrations: ConsoleIntegration[]): ConsoleIntegration[] {
  return topic.sources
    .map((sourceId) => integrations.find((source) => source.id === sourceId))
    .filter((source): source is ConsoleIntegration => Boolean(source))
}

function TopicDirectory({ data }: { data: ConsolePayload | null }) {
  const integrations = data?.integrations ?? []

  return (
    <div className="page-grid topic-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console#sources">Product Source Room</a>
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
                  <ConnectorIcon key={source.id} id={source.id} name={source.name} />
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
        <a href="/console#sources">Product Source Room</a>
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
  if (!topicId) {
    return <TopicDirectory data={data} />
  }

  const topic = topicById(topicId)
  if (!topic) {
    return <TopicNotFound />
  }

  const integrations = data?.integrations ?? []
  const topicSources = sourcesForTopic(topic, integrations)

  return (
    <div className="page-grid topic-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console#sources">Product Source Room</a>
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
          <a className="button primary" href={`/console/knowledge/ask?topic=${topic.id}&q=${encodeURIComponent(topic.question)}`}>
            Ask about this topic
          </a>
          <a className="button secondary" href="/console/generate/weekly-brief">Generate brief</a>
        </div>
      </section>

      <section className="topic-workspace-grid">
        <article className="topic-signal-panel panel">
          <span className="eyebrow">Current signals</span>
          <h2>{topic.question}</h2>
          <div className="topic-signal-list">
            {topic.signals.map((signal) => (
              <div key={signal.label} className="topic-signal-row">
                <span>{signal.label}</span>
                <strong>{signal.value}</strong>
                <p>{signal.detail}</p>
              </div>
            ))}
          </div>
        </article>
        <EvidenceReceipt sources={topicSources} gaps={topic.gaps} />
      </section>

      <section className="topic-output-panel panel">
        <div>
          <span className="eyebrow">Product outputs</span>
          <h2>Work this room can produce</h2>
        </div>
        <div className="topic-output-list">
          {topic.artifacts.map((artifact) => (
            <a key={artifact} href={`/console/generate/${artifact.toLowerCase().replace(/\s+/g, '-')}`}>
              {artifact}
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

export default TopicRoomPage

import { productTopics } from '../../fixtures/productTopics'
import type { ConsoleIntegration } from '../../types/console'
import ConnectorIcon from './ConnectorLogo'

type TopicRoomsPanelProps = {
  integrations: ConsoleIntegration[]
}

function isIntegration(source: ConsoleIntegration | undefined): source is ConsoleIntegration {
  return Boolean(source)
}

function TopicRoomsPanel({ integrations }: TopicRoomsPanelProps) {
  const sourceById = new Map(integrations.map((source) => [source.id, source]))

  return (
    <section className="topic-rooms-panel panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Problem rooms</span>
          <h2>Start with the product question, not the system.</h2>
          <p className="section-subtle">
            Topic rooms gather the relevant sources, starter questions, evidence, and artifacts for a recurring Product
            decision.
          </p>
        </div>
        <a className="text-link" href="/console/topics">Open all topics</a>
      </div>
      <div className="topic-room-list">
        {productTopics.map((topic) => {
          const topicSources = topic.sources.map((sourceId) => sourceById.get(sourceId)).filter(isIntegration).slice(0, 4)

          return (
            <a key={topic.id} className="topic-room-row" href={`/console/topics/${topic.id}`}>
              <span>
                <strong>{topic.title}</strong>
                <small>{topic.summary}</small>
              </span>
              <span className="topic-source-stack" aria-label={`${topic.title} sources`}>
                {topicSources.map((source) => (
                  <ConnectorIcon key={source.id} id={source.id} name={source.name} />
                ))}
              </span>
              <b>Open room</b>
            </a>
          )
        })}
      </div>
    </section>
  )
}

export default TopicRoomsPanel

import { useState } from 'react'

import IntegrationsPanel from '../components/console/IntegrationsPanel'
import LoadingSkeleton from '../components/console/LoadingSkeleton'
import TopicRoomsPanel from '../components/console/TopicRoomsPanel'
import { formatPercent } from '../components/console/formatters'
import { starterTopics } from '../content/productTopics'
import type { ConsolePayload } from '../types/console'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

function OperatorConsolePage({ data, loading, error, retry }: OperatorConsolePageProps) {
  if (loading && !data) {
    return <LoadingSkeleton />
  }

  const defaultQuestion = starterTopics[0]?.question ?? 'What should Product know before the next decision?'
  const [draftQuestion, setDraftQuestion] = useState(defaultQuestion)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)
  const integrations = data?.integrations ?? []
  const roomLinks = [
    {
      label: 'Mapped sources',
      value: String(integrations.length || '—'),
      note: 'Open sources',
      href: '/console/integrations',
    },
    {
      label: 'Hard gate pass',
      value: formatPercent(data?.summary.hard_gate_pass_rate),
      note: 'Open trust',
      href: '/console/trust',
    },
    {
      label: 'Needs review',
      value: String(data?.summary.needs_review_count ?? '—'),
      note: 'Open review',
      href: '/console/review',
    },
    {
      label: 'Eval skills',
      value: String(data?.summary.skill_count ?? '—'),
      note: 'See coverage',
      href: '/console/trust',
    },
  ]

  return (
    <div className="page-grid home-page">
      <section className="hero-panel source-hero panel">
        <div className="hero-copy">
          <span className="eyebrow">Shared product source room</span>
          <h2>Ask across every product system. Get answers with evidence.</h2>
          <p>
            DreamFi gives Product one calm place to gather information from Onyx-connected sources, inspect citations,
            and turn trusted context into briefs, PRDs, and follow-up work.
          </p>
          <div className="home-chat-panel">
            <div className="home-chat-message" aria-label="DreamFi starter prompt">
              <span>DreamFi</span>
              <p>What do you want to understand today? Start with a product question and I&apos;ll pull the right evidence.</p>
            </div>
            <form className="ask-box home-ask-box" action="/console/knowledge/ask">
              <label htmlFor="home-ask-query">Start with a question</label>
              <textarea
                id="home-ask-query"
                name="q"
                value={draftQuestion}
                onChange={(event) => {
                  const nextValue = event.target.value
                  setDraftQuestion(nextValue)

                  if (selectedTopicId) {
                    const selectedTopic = starterTopics.find((topic) => topic.id === selectedTopicId)
                    if (!selectedTopic || selectedTopic.question !== nextValue) {
                      setSelectedTopicId(null)
                    }
                  }
                }}
                placeholder="Why did KYC conversion move this week?"
              />
              {selectedTopicId ? <input type="hidden" name="topic" value={selectedTopicId} /> : null}
              <div className="ask-box-actions">
                <button type="submit" className="button primary">Ask DreamFi</button>
                <a className="button secondary" href="/console/topics">Browse topic rooms</a>
              </div>
            </form>
            <div className="prompt-chips home-prompt-chips" aria-label="Starter questions">
              {starterTopics.map((topic) => (
                <button
                  key={topic.id}
                  type="button"
                  className={selectedTopicId === topic.id ? 'active' : ''}
                  onClick={() => {
                    setDraftQuestion(topic.question)
                    setSelectedTopicId(topic.id)
                  }}
                >
                  {topic.question}
                </button>
              ))}
            </div>
          </div>
          <div className="hero-actions">
            <a className="button secondary" href="/console/knowledge/ask">Open full Ask view</a>
            <a className="button secondary" href="/console/topics">Open topic rooms</a>
            <a className="button secondary" href="#sources">Browse connectors</a>
          </div>
          {error ? (
            <div className="error-banner">
              <span>{error}</span>
              <button type="button" onClick={retry}>Retry</button>
            </div>
          ) : null}
        </div>
        <aside className="hero-aside panel inset-panel source-room-card">
          <span className="metric-label">How the room works</span>
          <h3>Pick a connector, inspect the slice, then ask with citations.</h3>
          <div className="snapshot-stats compact source-room-links">
            {roomLinks.map((item) => (
              <a key={item.label} className="source-room-link" href={item.href}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.note}</small>
              </a>
            ))}
          </div>
          <p className="source-room-note">
            Start from a topic or a source, then ask from grounded context instead of chasing systems one by one.
          </p>
        </aside>
      </section>

      <TopicRoomsPanel integrations={integrations} />

      <IntegrationsPanel items={integrations} />
    </div>
  )
}

export default OperatorConsolePage

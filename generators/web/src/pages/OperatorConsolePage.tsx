import { useState } from 'react'

import IntegrationsPanel from '../components/console/IntegrationsPanel'
import LoadingSkeleton from '../components/console/LoadingSkeleton'
import TopicRoomsPanel from '../components/console/TopicRoomsPanel'
import { starterTopics } from '../content/productTopics'
import type { ConsolePayload } from '../types/console'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

function OperatorConsolePage({ data, loading, error, retry }: OperatorConsolePageProps) {
  const defaultQuestion = starterTopics[0]?.question ?? 'What should Product know before the next decision?'
  const [draftQuestion, setDraftQuestion] = useState(defaultQuestion)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)

  if (loading && !data) {
    return <LoadingSkeleton />
  }

  const integrations = data?.integrations ?? []
  const recentChanges = (data?.context_changes ?? []).slice(0, 2)
  const changedRecentlyCount = data?.context_changes?.length ?? 0
  const connectedCount = integrations.filter((integration) => integration.status === 'connected').length
  const attentionCount = integrations.filter((integration) => integration.status === 'degraded').length
  const roomLinks = [
    {
      label: 'Mapped sources',
      value: String(integrations.length || '—'),
      note: 'Open sources',
      href: '/console/integrations',
    },
    {
      label: 'Changed yesterday',
      value: String(changedRecentlyCount || '0'),
      note: 'Open latest changes',
      href: recentChanges[0]?.href ?? '/console/topics',
    },
    {
      label: 'Connected live',
      value: String(connectedCount || '0'),
      note: 'Open sources',
      href: '/console/integrations',
    },
    {
      label: 'Need attention',
      value: String(attentionCount || '0'),
      note: 'Check source health',
      href: '/console/integrations',
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

      {recentChanges.length > 0 ? (
        <section className="context-change-strip panel" aria-label="Since you were last here">
          <div className="section-heading inline">
            <div>
              <span className="eyebrow">Since you were last here</span>
              <h2>Pick up from the changes that matter.</h2>
            </div>
          </div>
          <div className="context-change-list">
            {recentChanges.map((change) => (
              <a key={change.id} className={`context-change-row ${change.tone}`} href={change.href}>
                <strong>{change.title}</strong>
                <p>{change.summary}</p>
              </a>
            ))}
          </div>
        </section>
      ) : null}

      <TopicRoomsPanel integrations={integrations} />

      <IntegrationsPanel items={integrations} />
    </div>
  )
}

export default OperatorConsolePage

import { useState } from 'react'

import LivePulsePanel from '../components/console/LivePulsePanel'
import TrustActionRail from '../components/console/TrustActionRail'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import IntegrationsPanel from '../components/console/IntegrationsPanel'
import LoadingSkeleton from '../components/console/LoadingSkeleton'
import TopicRoomsPanel from '../components/console/TopicRoomsPanel'
import { formatPercent } from '../components/console/formatters'
import { starterTopics, topicById } from '../content/productTopics'
import type { ConsolePayload } from '../types/console'
import {
  recommendedGeneratorSlugForContext,
  recommendedGeneratorTitleForContext,
} from '../utils/generatorRecommendations'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

function OperatorConsolePage({ data, loading, error, retry }: OperatorConsolePageProps) {
  const { buildAskHref, buildGenerateHref, recentAsks } = useConsoleWorkspace()

  if (loading && !data) {
    return <LoadingSkeleton />
  }

  const defaultQuestion = starterTopics[0]?.question ?? 'What should Product know before the next decision?'
  const [draftQuestion, setDraftQuestion] = useState(defaultQuestion)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)
  const integrations = data?.integrations ?? []
  const selectedTopic = topicById(selectedTopicId)
  const connectedSources = integrations.filter((integration) => integration.status === 'connected')
  const degradedSources = integrations.filter((integration) => integration.status === 'degraded')
  const latestAlert = data?.alerts[0] ?? null
  const latestArtifact = data?.artifact_queue[0] ?? null
  const latestPublish = data?.publish_activity[0] ?? null
  const primaryDegradedSource = degradedSources[0] ?? null
  const recentThread = recentAsks[0] ?? null
  const recentThreadTopic = topicById(recentThread?.topicId ?? null)
  const recommendedGeneratorSlug = recommendedGeneratorSlugForContext({
    question: draftQuestion,
    topicId: selectedTopicId,
    source: null,
  })
  const recommendedGeneratorTitle = recommendedGeneratorTitleForContext({
    question: draftQuestion,
    topicId: selectedTopicId,
    source: null,
  })
  const generateFromContextHref = buildGenerateHref(recommendedGeneratorSlug, {
    question: draftQuestion,
    topicId: selectedTopicId,
  })
  const liveProofs = [
    {
      label: 'Knows the room',
      value: selectedTopic ? selectedTopic.title : recentThreadTopic?.title ?? 'Across product topics',
      detail: selectedTopic
        ? 'The active question is already scoped to a recurring product decision.'
        : recentThreadTopic
          ? `Recent memory is still anchored to ${recentThreadTopic.title}.`
          : 'Starter prompts map directly to recurring product rooms.',
    },
    {
      label: 'Pulls live sources',
      value: `${connectedSources.length} connected`,
      detail:
        degradedSources.length > 0
          ? `${degradedSources.map((source) => source.name).join(', ')} still needs review before publish.`
          : 'Sources are ready to cite inline as the answer develops.',
    },
    {
      label: 'Carries trust',
      value: data?.summary.needs_review_count ? `${data.summary.needs_review_count} needs review` : 'Ready to draft',
      detail: `Hard gate ${formatPercent(data?.summary.hard_gate_pass_rate)} and receipts stay attached to the thread.`,
    },
  ]
  const roomLinks = [
    {
      label: 'Mapped sources',
      value: String(integrations.length || '--'),
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
      value: String(data?.summary.needs_review_count ?? '--'),
      note: 'Open review',
      href: '/console/review',
    },
    {
      label: 'Eval skills',
      value: String(data?.summary.skill_count ?? '--'),
      note: 'See coverage',
      href: '/console/trust',
    },
  ]
  const livePulseItems = [
    latestAlert
      ? {
          label: 'Attention now',
          value: latestAlert.title,
          detail: latestAlert.message,
          href: latestAlert.href ?? '/console/trust',
          hrefLabel: latestAlert.href ? 'Open issue' : 'Open trust',
        }
      : null,
    latestArtifact
      ? {
          label: 'Latest draft',
          value: latestArtifact.test_input_label,
          detail: `${latestArtifact.skill_display_name ?? 'Artifact'} is currently ${latestArtifact.status.replace('_', ' ')}.`,
          href: latestArtifact.status === 'needs_review' ? '/console/review' : '/console/generate/technical-prd',
          hrefLabel: latestArtifact.status === 'needs_review' ? 'Review draft' : 'Open workflow',
        }
      : null,
    latestPublish
      ? {
          label: 'Latest publish',
          value: latestPublish.destination_ref ?? latestPublish.destination,
          detail: `${latestPublish.decision} ${latestPublish.skill_id.replace(/[_-]+/g, ' ')} into the shared product workspace.`,
          href: '/console/trust',
          hrefLabel: 'Open publish trail',
        }
      : null,
    primaryDegradedSource
      ? {
          label: 'Source freshness',
          value: `${primaryDegradedSource.name} needs attention`,
          detail: 'DreamFi keeps the degraded connector visible so trust does not disappear behind the draft.',
          href: primaryDegradedSource.href,
          hrefLabel: 'Inspect source',
        }
      : {
          label: 'Source freshness',
          value: `${connectedSources.length} connectors live`,
          detail: 'Connected sources are ready to keep answers and artifacts grounded in the same working thread.',
          href: '/console/integrations',
          hrefLabel: 'Browse sources',
        },
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))
  const trustActions = [
    primaryDegradedSource
      ? {
          title: `Review ${primaryDegradedSource.name} before publish`,
          detail: 'The riskiest connector should be one click away from the home screen while you are shaping the next decision.',
          href: primaryDegradedSource.href,
          hrefLabel: 'Inspect source',
          tone: 'warning' as const,
        }
      : null,
    data?.summary.needs_review_count
      ? {
          title: 'Clear the draft that still needs review',
          detail: 'Trust should stay operational, not just informational, so the review queue remains directly actionable from home.',
          href: '/console/review',
          hrefLabel: 'Open review',
          tone: 'info' as const,
        }
      : null,
    {
      title: `Generate ${recommendedGeneratorTitle} from this thread`,
      detail: 'The next artifact should inherit the same question and room instead of restarting from a blank template.',
      href: generateFromContextHref,
      hrefLabel: `Generate ${recommendedGeneratorTitle}`,
      tone: 'ready' as const,
    },
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))

  return (
    <div className="page-grid home-page">
      <section className="hero-panel source-hero panel">
        <div className="hero-copy">
          <span className="eyebrow">Shared product source room</span>
          <h2>Ask once. DreamFi pulls the product context, receipts, and next artifact.</h2>
          <p>
            This is not chat plus tabs. DreamFi starts from your product rooms, pulls live source context, keeps trust
            visible, and turns the same grounded thread into briefs, PRDs, and review-ready work.
          </p>
          <div className="home-chat-panel">
            <div className="home-chat-message" aria-label="DreamFi starter prompt">
              <span>DreamFi</span>
              <p>I know the rooms, sources, and trust rails around this product. Start with the question and I&apos;ll keep the receipts attached.</p>
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
                    const topic = starterTopics.find((candidate) => candidate.id === selectedTopicId)
                    if (!topic || topic.question !== nextValue) {
                      setSelectedTopicId(null)
                    }
                  }
                }}
                placeholder="Why did KYC conversion move this week?"
              />
              {selectedTopicId ? <input type="hidden" name="topic" value={selectedTopicId} /> : null}
              <div className="ask-box-actions">
                <button type="submit" className="button primary">Ask DreamFi</button>
                <a className="button secondary" href={generateFromContextHref}>Generate {recommendedGeneratorTitle}</a>
                <a className="button secondary" href="/console/topics">Browse topic rooms</a>
              </div>
            </form>
            <div className="home-proof-strip" aria-label="Why DreamFi is different">
              {liveProofs.map((proof) => (
                <article key={proof.label} className="home-proof-card">
                  <span>{proof.label}</span>
                  <strong>{proof.value}</strong>
                  <p>{proof.detail}</p>
                </article>
              ))}
            </div>
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
          <span className="metric-label">Why this beats tabs</span>
          <h3>DreamFi remembers the thread, carries trust, and generates from the same grounded context.</h3>
          <div className="snapshot-stats compact source-room-links">
            {roomLinks.map((item) => (
              <a key={item.label} className="source-room-link" href={item.href}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.note}</small>
              </a>
            ))}
          </div>
          {recentThread ? (
            <div className="home-memory-card">
              <span className="metric-label">Resume recent thread</span>
              <p>{recentThread.question}</p>
              <div className="home-memory-actions">
                <a
                  className="button secondary"
                  href={buildAskHref({
                    question: recentThread.question,
                    topicId: recentThread.topicId,
                    sourceId: recentThread.sourceId,
                  })}
                >
                  Reopen with receipts
                </a>
              </div>
            </div>
          ) : null}
          <p className="source-room-note">
            Start from a topic or a source, keep the question alive across pages, then generate from the same grounded
            context instead of rebuilding it every time.
          </p>
        </aside>
      </section>

      <LivePulsePanel
        title="The product world is changing right now"
        description="DreamFi should feel alive in the first 30 seconds, so the home surface pulls the latest trust, draft, publish, and source-state signals into one working view."
        items={livePulseItems}
      />

      <TrustActionRail
        title="Act on trust without leaving the thread"
        description="Use trust as guidance for the next move, not as a separate dashboard you visit after the fact."
        actions={trustActions}
      />

      <TopicRoomsPanel integrations={integrations} />

      <IntegrationsPanel items={integrations} />
    </div>
  )
}

export default OperatorConsolePage

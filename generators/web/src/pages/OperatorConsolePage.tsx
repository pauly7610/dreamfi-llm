import ActionCenter from '../components/console/ActionCenter'
import IntegrationsPanel from '../components/console/IntegrationsPanel'
import LoadingSkeleton from '../components/console/LoadingSkeleton'
import TopicRoomsPanel from '../components/console/TopicRoomsPanel'
import { formatDate, formatPercent, formatScore } from '../components/console/formatters'
import type { ConsolePayload } from '../types/console'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

const suggestedQuestions = [
  'Why did KYC conversion move this week?',
  'What changed in onboarding since the last roadmap review?',
  'Where do Jira delivery risks conflict with the PRD?',
]

const creationActionIds = ['weekly-brief', 'technical-prd', 'risk-brd']

function OperatorConsolePage({ data, loading, error, retry }: OperatorConsolePageProps) {
  if (loading && !data) {
    return <LoadingSkeleton />
  }

  const integrations = data?.integrations ?? []
  const creationActions = (data?.quick_actions ?? []).filter((action) => creationActionIds.includes(action.id))

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
          <div className="question-card">
            <span className="question-label">Start with a question</span>
            <strong>What should Product know before the next decision?</strong>
            <div className="prompt-chips">
              {suggestedQuestions.map((question) => (
                <a key={question} href={`/console/knowledge/ask?q=${encodeURIComponent(question)}`}>
                  {question}
                </a>
              ))}
            </div>
          </div>
          <div className="hero-actions">
            <a className="button primary" href="/console/knowledge/ask">Ask across sources</a>
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
          <dl className="snapshot-stats compact">
            <div>
              <dt>Mapped sources</dt>
              <dd>{integrations.length || '—'}</dd>
            </div>
            <div>
              <dt>Hard gate pass</dt>
              <dd>{formatPercent(data?.summary.hard_gate_pass_rate)}</dd>
            </div>
            <div>
              <dt>Needs review</dt>
              <dd>{data?.summary.needs_review_count ?? '—'}</dd>
            </div>
            <div>
              <dt>Eval skills</dt>
              <dd>{data?.summary.skill_count ?? '—'}</dd>
            </div>
          </dl>
          <p className="source-room-note">
            Onyx retrieves the evidence. DreamFi keeps the quality loop visible, but the main Product motion starts with
            choosing a source.
          </p>
        </aside>
      </section>

      <TopicRoomsPanel integrations={integrations} />

      <IntegrationsPanel
        items={integrations}
        title="Product connector space"
        description="A shared connector space for Product to see what DreamFi can gather, where context comes from, and how each source is used."
      />

      <ActionCenter
        actions={creationActions}
        eyebrow="Create from context"
        title="Turn gathered evidence into product work"
        description="Once the source room has the right context, generate the artifact that helps the team move."
      />

      <section className="home-pulse panel">
        <div className="section-heading">
          <span className="eyebrow">Quiet system pulse</span>
          <h2>The machinery is still here, just not shouting.</h2>
        </div>
        <div className="pulse-strip">
          <div>
            <span>Evidence trust</span>
            <strong>{formatScore(data?.summary.average_export_readiness)}</strong>
          </div>
          <div>
            <span>Needs review</span>
            <strong>{data?.summary.needs_review_count ?? '—'}</strong>
          </div>
          <div>
            <span>Latest signal</span>
            <strong>{formatDate(data?.artifact_queue[0]?.created_at)}</strong>
          </div>
        </div>
        <div className="pulse-links">
          <a href="/console/trust">Open trust view</a>
          <a href="/console/review?status=blocked">Review blocked work</a>
          <a href="/console/artifacts">Browse artifacts</a>
        </div>
      </section>
    </div>
  )
}

export default OperatorConsolePage

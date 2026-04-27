import { topicById } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { Chip, Cite, KPI, SectionHead, ConnectorLogo, connectorKeyFromId } from '../components/system/atoms'
import { labelForIntegrationStatus, sourceHref, topicHref, toneForIntegrationStatus } from './redesignSupport'

type AskNewPageProps = {
  data: ConsolePayload | null
}

function reasoningPoints(topicId: string | null, sourceId: string | null): string[] {
  const topic = topicById(topicId)
  const workflow = workflowByTopicId(topicId)

  if (topic && workflow) {
    return [
      `DreamFi keeps this answer in the ${workflow.currentState.phase.toLowerCase()} phase, where the next decision is still explicit.`,
      workflow.nextDecision,
      ...workflow.missing.slice(0, 2),
    ]
  }

  if (topic) {
    return topic.signals.map((signal) => `${signal.label}: ${signal.detail}`)
  }

  if (sourceId) {
    return [
      'This ask is scoped to one connector, so the answer should stay close to source evidence.',
      'Use the linked source workspace to inspect the raw slice before publishing a claim.',
      'When the answer is stable, carry the same citations into the next artifact.',
    ]
  }

  return [
    'Start with the current product question, not the tool.',
    'Keep source evidence visible before moving into generated work.',
    'Escalate to a topic room when the question becomes a recurring decision.',
  ]
}

export function AskNewPage({ data }: AskNewPageProps) {
  const {
    buildGenerateHref,
    currentQuestion,
    currentSource,
    currentSourceId,
    currentTopic,
    currentTopicId,
    recommendedGeneratorSlug,
    recommendedGeneratorTitle,
  } = useConsoleWorkspace()
  const integrations = data?.integrations ?? []
  const selectedSources = currentTopic
    ? currentTopic.sources
        .map((sourceId) => integrations.find((integration) => integration.id === sourceId))
        .filter((integration): integration is NonNullable<typeof integration> => Boolean(integration))
        .slice(0, 6)
    : currentSource
      ? [currentSource]
      : integrations.slice(0, 4)
  const workflow = workflowByTopicId(currentTopicId)
  const headline =
    currentQuestion ||
    currentTopic?.question ||
    (currentSource ? `What should Product know from ${currentSource.name}?` : 'Ask the company what it already knows.')

  const primarySource = selectedSources[0] ?? null
  const answerLead = workflow
    ? workflow.recommendation
    : currentSource
      ? `${currentSource.name} is the current source of truth for this thread. ${currentSource.purpose}`
      : 'DreamFi should answer from connected evidence, show the limits, and keep the next move ready.'

  const answerDetail = workflow
    ? workflow.missing[0] ?? 'The current room is grounded, but still needs one more review pass before publish.'
    : currentSource
      ? `Status: ${labelForIntegrationStatus(currentSource.status)}. This answer should keep that connector posture visible.`
      : 'Choose a topic or source if you want the next artifact to stay tightly scoped.'

  return (
    <div className="page page-narrow">
      <div className="eyebrow" style={{ marginBottom: 12 }}>ASK</div>

      <h1 className="display-question" style={{ marginBottom: 28 }}>{headline}</h1>

      <div className="trust-strip" style={{ marginBottom: 24 }}>
        <span style={{ color: 'var(--ink-2)' }}>Grounded in</span>
        {selectedSources.map((integration) => (
          <a key={integration.id} href={sourceHref(integration.id)} aria-label={integration.name}>
            <ConnectorLogo connector={connectorKeyFromId(integration.id)} />
          </a>
        ))}
        <span className={`pill ${currentSource?.status === 'degraded' ? 'warn' : 'ready'}`}>
          {currentSource?.status === 'degraded' ? 'connector needs attention' : 'sources in scope'}
        </span>
        <div className="spacer" />
        <span style={{ color: 'var(--ink-2)' }}>confidence</span>
        <b style={{ fontFamily: 'var(--font-mono)' }}>{formatPercent(data?.summary.average_confidence)}</b>
      </div>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ padding: '22px 24px 8px' }}>
          <div className="eyebrow" style={{ marginBottom: 10 }}>ANSWER</div>
          <p style={{ fontSize: 17, lineHeight: 1.55, color: 'var(--ink-0)', margin: 0 }}>
            {answerLead}
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--ink-1)', margin: '14px 0 0' }}>
            {answerDetail}
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', borderTop: '1px solid var(--line)' }}>
          <KPI
            label="QUESTION"
            value={currentTopic?.title ?? currentSource?.name ?? 'General'}
            delta={selectedSources.length === 1 ? 'source-scoped' : `${selectedSources.length} sources`}
            source={
              primarySource
                ? {
                    connector: connectorKeyFromId(primarySource.id),
                    href: sourceHref(primarySource.id),
                    label: primarySource.name,
                  }
                : undefined
            }
          />
          <KPI
            label="TRUST"
            value={formatPercent(data?.summary.hard_gate_pass_rate)}
            delta={workflow?.currentState.readiness ?? 'current posture'}
            deltaTone={currentSource?.status === 'degraded' ? 'down' : 'up'}
          />
          <KPI
            label="ARTIFACT NEXT"
            value={recommendedGeneratorTitle}
            delta="carry this thread forward"
          />
          <KPI
            label="QUEUE"
            value={data?.summary.needs_review_count ?? 0}
            delta={`${data?.summary.blocked_artifact_count ?? 0} blocked`}
            deltaTone={(data?.summary.blocked_artifact_count ?? 0) > 0 ? 'down' : 'flat'}
          />
        </div>
      </div>

      <div className="surface" style={{ marginBottom: 20 }}>
        <SectionHead title="Reasoning" eyebrow="WHY THIS ANSWER" />
        <ol style={{ margin: 0, padding: '8px 0' }}>
          {reasoningPoints(currentTopicId, currentSourceId).map((point, index) => (
            <li
              key={point}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 14,
                padding: '14px 24px',
                borderBottom: index < reasoningPoints(currentTopicId, currentSourceId).length - 1 ? '1px solid var(--line)' : 'none',
              }}
            >
              <span style={{ minWidth: 20, paddingTop: 2, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                {`0${index + 1}`}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--ink-1)', fontSize: 13.5, lineHeight: 1.55 }}>{point}</div>
                {selectedSources[index] ? (
                  <div style={{ marginTop: 6 }}>
                    <Cite
                      connector={connectorKeyFromId(selectedSources[index].id)}
                      href={sourceHref(selectedSources[index].id)}
                      label={selectedSources[index].name}
                    />
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="surface">
        <SectionHead title="Next moves" eyebrow="WHAT TO DO" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', borderTop: '1px solid var(--line)' }}>
          <div style={{ padding: '18px 22px', borderRight: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div className="eyebrow">01</div>
            <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500 }}>{currentTopic ? 'Open topic room' : 'Browse topic rooms'}</div>
            <div style={{ color: 'var(--ink-2)', fontSize: 12.5 }}>
              {currentTopic ? `${currentTopic.title} stays decision-first.` : 'Escalate repeated asks into a shared room.'}
            </div>
            <a className="btn btn-sm btn-primary" href={currentTopic ? topicHref(currentTopic.id) : '/console/topics'} style={{ alignSelf: 'flex-start', marginTop: 6 }}>
              {currentTopic ? 'Open room' : 'Browse'}
            </a>
          </div>
          <div style={{ padding: '18px 22px', borderRight: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div className="eyebrow">02</div>
            <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500 }}>{`Generate ${recommendedGeneratorTitle}`}</div>
            <div style={{ color: 'var(--ink-2)', fontSize: 12.5 }}>Carry the same question, topic, and source context into the draft.</div>
            <a className="btn btn-sm" href={buildGenerateHref(recommendedGeneratorSlug)} style={{ alignSelf: 'flex-start', marginTop: 6 }}>
              Compose
            </a>
          </div>
          <div style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div className="eyebrow">03</div>
            <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500 }}>{currentSource ? 'Inspect connector' : 'Open source directory'}</div>
            <div style={{ color: 'var(--ink-2)', fontSize: 12.5 }}>
              {currentSource ? `Stay inside ${currentSource.name} before you publish.` : 'Jump into the one system you need most.'}
            </div>
            <a className="btn btn-sm" href={currentSource ? sourceHref(currentSource.id) : '/console/integrations'} style={{ alignSelf: 'flex-start', marginTop: 6 }}>
              Inspect
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

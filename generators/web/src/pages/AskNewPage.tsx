import { topicById, topicsForSource, type ProductTopic } from '../content/productTopics'
import { workflowByTopicId, workflowQuestionsForTopic, type ProductWorkflowModel } from '../content/productWorkflows'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { Chip, Cite, KPI, SectionHead, ConnectorLogo, connectorKeyFromId } from '../components/system/atoms'
import { labelForIntegrationStatus, sourceHref, topicHref, toneForIntegrationStatus, toneForWorkflowTone } from './redesignSupport'

type AskNewPageProps = {
  data: ConsolePayload | null
}

type AskInsight = {
  eyebrow: string
  title: string
  body: string
  sourceId?: string | null
}

type AskResultCard = {
  title: string
  body: string
  href: string
  meta: string
  sourceId: string
}

type AskMode = 'why' | 'where' | 'decision' | 'what'

function questionMode(question: string): AskMode {
  const normalizedQuestion = question.trim().toLowerCase()

  if (normalizedQuestion.startsWith('why')) {
    return 'why'
  }

  if (normalizedQuestion.startsWith('where') || normalizedQuestion.includes('stuck')) {
    return 'where'
  }

  if (
    normalizedQuestion.startsWith('should') ||
    normalizedQuestion.startsWith('can') ||
    normalizedQuestion.includes('ready') ||
    normalizedQuestion.includes('move forward')
  ) {
    return 'decision'
  }

  return 'what'
}

function uniqueQuestions(questions: string[], currentQuestion: string): string[] {
  const seen = new Set<string>()
  const normalizedCurrent = currentQuestion.trim().toLowerCase()

  return questions.filter((question) => {
    const normalizedQuestion = question.trim().toLowerCase()
    if (!normalizedQuestion || normalizedQuestion === normalizedCurrent || seen.has(normalizedQuestion)) {
      return false
    }

    seen.add(normalizedQuestion)
    return true
  })
}

function answerLead(
  mode: AskMode,
  workflow: ProductWorkflowModel | null,
  topic: ProductTopic | null,
  source: ConsoleIntegration | null,
): string {
  if (workflow && topic) {
    if (mode === 'why') {
      const primarySignal = topic.signals[0]
      return primarySignal
        ? `${primarySignal.label} is the clearest signal right now, and it supports keeping this thread in ${workflow.currentState.phase.toLowerCase()} until the missing decision inputs are closed.`
        : workflow.recommendation
    }

    if (mode === 'where') {
      const frictionSignal = topic.signals[1] ?? topic.signals[0]
      return frictionSignal
        ? `The sharpest friction is showing up in ${frictionSignal.label.toLowerCase()}, which is where this ask should stay grounded before we broaden the scope.`
        : workflow.recommendation
    }

    if (mode === 'decision') {
      return `${workflow.nextDecision} Right now the answer leans toward holding scope until the blockers are explicit.`
    }

    return workflow.recommendation
  }

  if (topic) {
    const primaryMetric = topic.toplineMetrics[0]
    return primaryMetric
      ? `${topic.title} is currently anchored in ${primaryMetric.label.toLowerCase()} at ${primaryMetric.value}, with the answer staying inside the topic room's source set.`
      : topic.summary
  }

  if (source) {
    return `${source.name} is the best source of truth for this question, so the answer should stay close to that connector before it becomes a generated artifact.`
  }

  return 'DreamFi should answer from connected evidence, show confidence and caveats, and keep the next move easy to take.'
}

function answerDetail(
  workflow: ProductWorkflowModel | null,
  topic: ProductTopic | null,
  source: ConsoleIntegration | null,
): string {
  if (workflow) {
    return workflow.missing[0] ?? workflow.currentState.readiness
  }

  if (topic) {
    return topic.gaps[0] ?? topic.summary
  }

  if (source) {
    return `Status: ${labelForIntegrationStatus(source.status)}. ${source.purpose}`
  }

  return 'Scope to a topic or source when you want the answer to stay tightly grounded and easier to turn into an artifact.'
}

function buildInsights(
  mode: AskMode,
  workflow: ProductWorkflowModel | null,
  topic: ProductTopic | null,
  source: ConsoleIntegration | null,
): AskInsight[] {
  if (workflow && topic) {
    const primarySignal = topic.signals[0]
    const secondarySignal = topic.signals[1] ?? topic.signals[0]

    return [
      {
        eyebrow: mode === 'decision' ? 'DECISION PATH' : 'WHAT WE KNOW',
        title: workflow.currentState.readiness,
        body: workflow.recommendation,
        sourceId: primarySignal?.sourceId,
      },
      {
        eyebrow: mode === 'where' ? 'FRICTION' : 'EVIDENCE',
        title: secondarySignal?.label ?? workflow.currentState.step,
        body: secondarySignal ? `${secondarySignal.value} — ${secondarySignal.detail}` : workflow.nextDecision,
        sourceId: secondarySignal?.sourceId,
      },
      {
        eyebrow: 'WATCHOUT',
        title: 'What still limits the answer',
        body: workflow.missing[0] ?? topic.gaps[0] ?? 'One more review pass is still needed before publish.',
        sourceId: workflow.gates.find((gate) => gate.status !== 'ready')?.sourceIds[0],
      },
    ]
  }

  if (topic) {
    return topic.signals.slice(0, 3).map((signal, index) => ({
      eyebrow: index === 0 ? 'WHAT WE KNOW' : index === 1 ? 'SUPPORTING SIGNAL' : 'WATCHOUT',
      title: `${signal.label} · ${signal.value}`,
      body: signal.detail,
      sourceId: signal.sourceId,
    }))
  }

  if (source) {
    return [
      {
        eyebrow: 'SOURCE TRUTH',
        title: `${source.name} is in scope`,
        body: source.purpose,
        sourceId: source.id,
      },
      {
        eyebrow: 'BEST FOR',
        title: `Use ${source.name} before expanding the answer`,
        body: `This connector is currently used for ${source.used_for.join(', ') || 'grounded product work'}.`,
        sourceId: source.id,
      },
      {
        eyebrow: 'WATCHOUT',
        title: 'Keep the caveat visible',
        body: `Current status is ${labelForIntegrationStatus(source.status)}. Any generated follow-up should keep that posture explicit.`,
        sourceId: source.id,
      },
    ]
  }

  return [
    {
      eyebrow: 'START HERE',
      title: 'Ask the company, not a tool',
      body: 'Start from the decision or product question, then tighten the scope after the first answer comes back.',
    },
    {
      eyebrow: 'GROUNDING',
      title: 'Keep evidence visible',
      body: 'DreamFi should show which systems are in the answer, not make you guess where the conclusion came from.',
    },
    {
      eyebrow: 'NEXT MOVE',
      title: 'Make the follow-up easy',
      body: 'Once the answer feels stable, hand the same context into a topic room or generated artifact.',
    },
  ]
}

function buildResultCards(
  selectedSources: ConsoleIntegration[],
  workflow: ProductWorkflowModel | null,
  topic: ProductTopic | null,
): AskResultCard[] {
  if (workflow) {
    return workflow.connectorCoverage
      .map((coverage) => {
        const integration = selectedSources.find((source) => source.id === coverage.sourceId)
        if (!integration) {
          return null
        }

        return {
          title: `${integration.name} · ${coverage.role}`,
          body: coverage.detail,
          href: sourceHref(integration.id),
          meta: coverage.bestFor,
          sourceId: integration.id,
        }
      })
      .filter((card): card is AskResultCard => Boolean(card))
      .slice(0, 4)
  }

  if (topic) {
    return topic.signals
      .map((signal) => {
        if (!signal.sourceId) {
          return null
        }

        return {
          title: signal.label,
          body: signal.detail,
          href: sourceHref(signal.sourceId),
          meta: signal.value,
          sourceId: signal.sourceId,
        }
      })
      .filter((card): card is AskResultCard => Boolean(card))
      .slice(0, 4)
  }

  return selectedSources.slice(0, 4).map((source) => ({
    title: source.name,
    body: source.purpose,
    href: sourceHref(source.id),
    meta: labelForIntegrationStatus(source.status),
    sourceId: source.id,
  }))
}

function buildFollowUps(
  currentQuestion: string,
  currentTopic: ProductTopic | null,
  currentSource: ConsoleIntegration | null,
): string[] {
  if (currentTopic) {
    return uniqueQuestions(
      [
        ...workflowQuestionsForTopic(currentTopic.id),
        ...currentTopic.signals.map((signal) => `What should Product know about ${signal.label.toLowerCase()}?`),
        currentTopic.question,
      ],
      currentQuestion,
    ).slice(0, 6)
  }

  if (currentSource) {
    return uniqueQuestions(
      [
        `What should Product know from ${currentSource.name}?`,
        ...topicsForSource(currentSource.id).map((topic) => topic.question),
        `Which decisions depend most on ${currentSource.name}?`,
      ],
      currentQuestion,
    ).slice(0, 6)
  }

  return uniqueQuestions(
    [
      'Where are users getting stuck before first funding?',
      'Why did KYC conversion move this week?',
      'What changed in onboarding since the last roadmap review?',
      'Which lifecycle messages are helping users finish onboarding?',
    ],
    currentQuestion,
  ).slice(0, 6)
}

export function AskNewPage({ data }: AskNewPageProps) {
  const {
    buildAskHref,
    buildGenerateHref,
    currentQuestion,
    currentSource,
    currentSourceId,
    currentTopic,
    currentTopicId,
    recentAsks,
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
  const mode = questionMode(headline)
  const primarySource = selectedSources[0] ?? null
  const insights = buildInsights(mode, workflow, currentTopic, currentSource)
  const resultCards = buildResultCards(selectedSources, workflow, currentTopic)
  const followUps = buildFollowUps(headline, currentTopic, currentSource)
  const recentAskLinks = recentAsks.filter((ask) => ask.question !== headline).slice(0, 4)
  const sourceTopics = currentSource ? topicsForSource(currentSource.id).slice(0, 3) : []
  const topicScope = currentTopic ?? topicById(currentTopicId)

  return (
    <div className="page page-narrow">
      <div className="eyebrow" style={{ marginBottom: 12 }}>ASK</div>

      <h1 className="display-question" style={{ marginBottom: 18 }}>{headline}</h1>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ padding: '22px 24px 18px' }}>
          <div className="row" style={{ alignItems: 'flex-start', gap: 18, marginBottom: 14 }}>
            <div style={{ flex: 1 }}>
              <div className="eyebrow" style={{ marginBottom: 10 }}>QUESTION COMPOSER</div>
              <form action="/console/knowledge/ask" method="get" style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label htmlFor="ask-page-question" style={{ display: 'block', color: 'var(--ink-2)', fontSize: 12, marginBottom: 8 }}>
                    Question
                  </label>
                  <textarea
                    id="ask-page-question"
                    name="q"
                    defaultValue={headline}
                    rows={2}
                    style={{
                      width: '100%',
                      resize: 'vertical',
                      padding: '14px 16px',
                      borderRadius: 16,
                      border: '1px solid var(--line)',
                      background: 'var(--bg-soft)',
                      color: 'var(--ink-0)',
                      font: 'inherit',
                      lineHeight: 1.45,
                    }}
                  />
                  {currentTopicId ? <input name="topic" type="hidden" value={currentTopicId} /> : null}
                  {currentSourceId ? <input name="source" type="hidden" value={currentSourceId} /> : null}
                </div>
                <button className="btn btn-primary" type="submit">
                  Ask
                </button>
              </form>
            </div>

            <div style={{ minWidth: 240, maxWidth: 260 }}>
              <div className="eyebrow" style={{ marginBottom: 10 }}>ANSWER MODE</div>
              <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
                <Chip tone={workflow ? toneForWorkflowTone(workflow.currentState.tone) : 'signal'}>
                  {mode === 'why' ? 'causal answer' : mode === 'where' ? 'friction answer' : mode === 'decision' ? 'decision answer' : 'grounded answer'}
                </Chip>
                <Chip tone={currentSource?.status === 'degraded' ? 'warn' : 'ready'}>
                  {selectedSources.length === 1 ? 'single source scope' : `${selectedSources.length} sources in scope`}
                </Chip>
              </div>
            </div>
          </div>

          <div className="trust-strip" style={{ marginBottom: 16 }}>
            <span style={{ color: 'var(--ink-2)' }}>Grounded in</span>
            {selectedSources.map((integration) => (
              <a key={integration.id} href={sourceHref(integration.id)} aria-label={integration.name}>
                <ConnectorLogo connector={connectorKeyFromId(integration.id)} />
              </a>
            ))}
            {topicScope ? <Chip tone="signal">{topicScope.title}</Chip> : null}
            {currentSource ? <Chip tone={toneForIntegrationStatus(currentSource.status)}>{labelForIntegrationStatus(currentSource.status)}</Chip> : null}
            <div className="spacer" />
            <span style={{ color: 'var(--ink-2)' }}>confidence</span>
            <b style={{ fontFamily: 'var(--font-mono)' }}>{formatPercent(data?.summary.average_confidence)}</b>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {followUps.slice(0, 4).map((question) => (
              <a
                key={question}
                className="chip"
                href={buildAskHref({ question })}
                style={{ textDecoration: 'none', color: 'var(--ink-1)' }}
              >
                {question}
              </a>
            ))}
            {(currentTopic || currentSource) ? (
              <a
                className="chip"
                href={buildAskHref({ question: headline, topicId: null, sourceId: null })}
                style={{ textDecoration: 'none', color: 'var(--ink-1)' }}
              >
                Search all knowledge
              </a>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.45fr) minmax(280px, 0.8fr)', gap: 20, marginBottom: 20 }}>
        <div className="surface">
          <div style={{ padding: '22px 24px 8px' }}>
            <div className="eyebrow" style={{ marginBottom: 10 }}>BEST ANSWER</div>
            <p style={{ fontSize: 17, lineHeight: 1.55, color: 'var(--ink-0)', margin: 0 }}>
              {answerLead(mode, workflow, currentTopic, currentSource)}
            </p>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--ink-1)', margin: '14px 0 0' }}>
              {answerDetail(workflow, currentTopic, currentSource)}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', borderTop: '1px solid var(--line)' }}>
            <KPI
              label="SCOPE"
              value={currentTopic?.title ?? currentSource?.name ?? 'Company'}
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

        <div style={{ display: 'grid', gap: 20 }}>
          <div className="surface">
            <SectionHead title="People to ask" eyebrow="WHO OWNS THE NEXT DECISION" />
            <div style={{ padding: '8px 0' }}>
              {(workflow?.owners ?? []).slice(0, 3).map((owner, index) => (
                <div
                  key={`${owner.role}-${owner.owner}`}
                  style={{
                    padding: '14px 24px',
                    borderBottom: index < Math.min((workflow?.owners ?? []).length, 3) - 1 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <div className="row" style={{ marginBottom: 6 }}>
                    <span style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500 }}>{owner.owner}</span>
                    <div className="spacer" />
                    <Chip tone="signal">{owner.role}</Chip>
                  </div>
                  <div style={{ color: 'var(--ink-2)', fontSize: 12.5, lineHeight: 1.55 }}>{owner.nextAction}</div>
                </div>
              ))}
              {!workflow ? (
                <div style={{ padding: '14px 24px', color: 'var(--ink-2)', fontSize: 12.5, lineHeight: 1.55 }}>
                  Scope to a topic room when you want DreamFi to surface explicit owners and decision handoffs.
                </div>
              ) : null}
            </div>
          </div>

          <div className="surface">
            <SectionHead title="Recent asks" eyebrow="PICK UP A THREAD" />
            <div style={{ padding: '8px 0' }}>
              {recentAskLinks.length > 0 ? recentAskLinks.map((recentAsk, index) => (
                <a
                  key={`${recentAsk.question}-${recentAsk.topicId ?? 'topicless'}-${recentAsk.sourceId ?? 'sourceless'}`}
                  href={buildAskHref({
                    question: recentAsk.question,
                    topicId: recentAsk.topicId,
                    sourceId: recentAsk.sourceId,
                  })}
                  style={{
                    display: 'block',
                    padding: '14px 24px',
                    textDecoration: 'none',
                    color: 'inherit',
                    borderBottom: index < recentAskLinks.length - 1 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <div style={{ color: 'var(--ink-0)', fontSize: 14, lineHeight: 1.45 }}>{recentAsk.question}</div>
                  <div style={{ color: 'var(--ink-2)', fontSize: 12 }}>
                    {recentAsk.topicId ? topicById(recentAsk.topicId)?.title ?? 'Topic' : recentAsk.sourceId ? integrations.find((source) => source.id === recentAsk.sourceId)?.name ?? 'Source' : 'General'}
                  </div>
                </a>
              )) : (
                <div style={{ padding: '14px 24px', color: 'var(--ink-2)', fontSize: 12.5, lineHeight: 1.55 }}>
                  Your recent asks show up here once you start exploring product questions.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(280px, 0.85fr)', gap: 20, marginBottom: 20 }}>
        <div className="surface">
          <SectionHead title="How this answer was built" eyebrow="REASONING" />
          <div style={{ padding: '8px 0' }}>
            {insights.map((insight, index) => {
              const citedSource = insight.sourceId
                ? integrations.find((integration) => integration.id === insight.sourceId) ?? selectedSources.find((integration) => integration.id === insight.sourceId) ?? null
                : null

              return (
                <div
                  key={`${insight.eyebrow}-${insight.title}`}
                  style={{
                    display: 'flex',
                    gap: 14,
                    padding: '14px 24px',
                    borderBottom: index < insights.length - 1 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <span style={{ minWidth: 24, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)', fontSize: 11, paddingTop: 2 }}>
                    {`0${index + 1}`}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div className="eyebrow" style={{ marginBottom: 6 }}>{insight.eyebrow}</div>
                    <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500, marginBottom: 6 }}>{insight.title}</div>
                    <div style={{ color: 'var(--ink-2)', fontSize: 13.5, lineHeight: 1.55 }}>{insight.body}</div>
                    {citedSource ? (
                      <div style={{ marginTop: 8 }}>
                        <Cite
                          connector={connectorKeyFromId(citedSource.id)}
                          href={sourceHref(citedSource.id)}
                          label={citedSource.name}
                        />
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'grid', gap: 20 }}>
          <div className="surface">
            <SectionHead title="Source results" eyebrow="WHAT DREAMFI PULLED" />
            <div style={{ padding: '8px 0' }}>
              {resultCards.map((card, index) => {
                const integration = integrations.find((item) => item.id === card.sourceId)
                if (!integration) {
                  return null
                }

                return (
                  <a
                    key={`${card.title}-${card.sourceId}`}
                    href={card.href}
                    style={{
                      display: 'block',
                      padding: '14px 24px',
                      textDecoration: 'none',
                      color: 'inherit',
                      borderBottom: index < resultCards.length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div className="row" style={{ marginBottom: 8 }}>
                      <Cite connector={connectorKeyFromId(integration.id)} label={integration.name} />
                      <div className="spacer" />
                      <Chip tone={toneForIntegrationStatus(integration.status)}>{labelForIntegrationStatus(integration.status)}</Chip>
                    </div>
                    <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500, marginBottom: 6 }}>{card.title}</div>
                    <div style={{ color: 'var(--ink-2)', fontSize: 12.5, lineHeight: 1.55, marginBottom: 8 }}>{card.body}</div>
                    <div style={{ color: 'var(--ink-3)', fontSize: 11 }}>{card.meta}</div>
                  </a>
                )
              })}
            </div>
          </div>

          <div className="surface">
            <SectionHead title="Suggested follow-ups" eyebrow="KEEP ASKING" />
            <div style={{ padding: '8px 0' }}>
              {followUps.map((question, index) => (
                <a
                  key={question}
                  href={buildAskHref({ question })}
                  style={{
                    display: 'block',
                    padding: '14px 24px',
                    textDecoration: 'none',
                    color: 'inherit',
                    borderBottom: index < followUps.length - 1 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <div style={{ color: 'var(--ink-0)', fontSize: 14, lineHeight: 1.45 }}>{question}</div>
                  <div style={{ color: 'var(--ink-2)', fontSize: 12 }}>
                    {currentTopic ? 'Stay in the same topic room' : currentSource ? 'Keep the same source scope' : 'Open a nearby company question'}
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
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

      {sourceTopics.length > 0 ? (
        <div className="surface" style={{ marginTop: 20 }}>
          <SectionHead title="Related topic rooms" eyebrow="TURN THIS INTO A RECURRING THREAD" />
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(sourceTopics.length, 3)}, minmax(0, 1fr))`, borderTop: '1px solid var(--line)' }}>
            {sourceTopics.map((topic, index) => (
              <div
                key={topic.id}
                style={{
                  padding: '18px 22px',
                  borderRight: index < sourceTopics.length - 1 ? '1px solid var(--line)' : 'none',
                }}
              >
                <div className="eyebrow" style={{ marginBottom: 8 }}>TOPIC ROOM</div>
                <div style={{ color: 'var(--ink-0)', fontSize: 14, fontWeight: 500, marginBottom: 6 }}>{topic.title}</div>
                <div style={{ color: 'var(--ink-2)', fontSize: 12.5, lineHeight: 1.55, marginBottom: 12 }}>{topic.summary}</div>
                <a className="btn btn-sm" href={topicHref(topic.id)}>
                  Open room
                </a>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

import { useMemo, useState, type FormEvent } from 'react'

import type { ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ConsolePayload } from '../types/console'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { Chip, Cite, KPI, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { generatorTitleFromSlug } from '../utils/consoleRoutes'
import { navigateConsole } from '../utils/consoleNavigation'
import { sourceHref, toneForWorkflowTone, topicHref } from './redesignSupport'

type TopicNewPageProps = {
  data: ConsolePayload | null
  topicId: string | null
}

const TOPIC_TEMPLATE_OPTIONS = [
  { slug: 'weekly-brief', label: generatorTitleFromSlug('weekly-brief') },
  { slug: 'technical-prd', label: generatorTitleFromSlug('technical-prd') },
  { slug: 'business-prd', label: generatorTitleFromSlug('business-prd') },
  { slug: 'risk-brd', label: generatorTitleFromSlug('risk-brd') },
] as const

function topicSources(topic: ProductTopic, data: ConsolePayload | null) {
  const integrations = data?.integrations ?? []
  return topic.sources
    .map((sourceId) => integrations.find((integration) => integration.id === sourceId))
    .filter((integration): integration is NonNullable<typeof integration> => Boolean(integration))
}

function fallbackTimeline(topic: ProductTopic) {
  return [
    {
      label: 'CUSTOM ROOM',
      summary: 'Created locally',
      detail: `Ask the starter question, inspect ${topic.sources.length || 1} connected sources, and draft the first artifact from this room.`,
      sourceIds: topic.sources,
    },
    {
      label: 'GROUNDING',
      summary: 'Verify source freshness',
      detail: 'Keep the first recommendation grounded in connected evidence before it moves into trust review.',
      sourceIds: topic.sources,
    },
  ]
}

function TopicDirectory({ data }: { data: ConsolePayload | null }) {
  const { addTopic, topics } = useConsoleWorkspace()
  const integrations = data?.integrations ?? []
  const suggestedSourceIds = useMemo(
    () =>
      integrations
        .filter((integration) => integration.status !== 'not_configured')
        .slice(0, 3)
        .map((integration) => integration.id),
    [integrations],
  )
  const [isCreating, setIsCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [question, setQuestion] = useState('')
  const [summary, setSummary] = useState('')
  const [defaultGeneratorSlug, setDefaultGeneratorSlug] = useState<string>('weekly-brief')
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>(suggestedSourceIds)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  function resetForm() {
    setTitle('')
    setQuestion('')
    setSummary('')
    setDefaultGeneratorSlug('weekly-brief')
    setSelectedSourceIds(suggestedSourceIds)
    setFormError(null)
  }

  function toggleCreateForm() {
    if (!isCreating) {
      resetForm()
    } else {
      setFormError(null)
    }

    setIsCreating((current) => !current)
  }

  function toggleSource(sourceId: string) {
    setSelectedSourceIds((current) =>
      current.includes(sourceId)
        ? current.filter((value) => value !== sourceId)
        : [...current, sourceId],
    )
  }

  async function handleCreateTopic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedTitle = title.trim()
    const trimmedQuestion = question.trim()
    if (!trimmedTitle) {
      setFormError('Add a topic name first.')
      return
    }

    if (!trimmedQuestion) {
      setFormError('Add the starter question this room should answer.')
      return
    }

    if (selectedSourceIds.length === 0) {
      setFormError('Pick at least one source to ground the room.')
      return
    }

    try {
      setIsSaving(true)
      const createdTopic = await addTopic({
        defaultGeneratorSlug,
        question: trimmedQuestion,
        sourceIds: selectedSourceIds,
        summary,
        title: trimmedTitle,
      })

      setIsCreating(false)
      resetForm()
      navigateConsole(topicHref(createdTopic.id))
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Unable to create topic.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TOPICS</div>
      <h1 className="display-question" style={{ marginBottom: 24, maxWidth: 820 }}>
        Choose the <em>decision room</em> before choosing the tool.
      </h1>

      <div className="surface" style={{ marginBottom: 20 }}>
        <SectionHead
          title="Create a room"
          eyebrow="NEW TOPIC"
          right={(
            <button className={isCreating ? 'btn btn-sm' : 'btn btn-sm btn-primary'} onClick={toggleCreateForm} type="button">
              {isCreating ? 'Close' : 'New topic'}
            </button>
          )}
        />
        <div style={{ padding: '18px 24px' }}>
          <p style={{ margin: '0 0 14px', color: 'var(--ink-2)', fontSize: 13.5, lineHeight: 1.55 }}>
            Add a new topic room in one pass, pick the connectors it should stay grounded in, and DreamFi will carry it through Ask, Generate, and the sidebar.
          </p>

          {isCreating ? (
            <form method="post" onSubmit={handleCreateTopic} style={{ display: 'grid', gap: 16 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 16 }}>
                <label style={{ display: 'grid', gap: 8 }}>
                  <span className="eyebrow">Topic name</span>
                  <input
                    name="title"
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="Example: Card disputes"
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      borderRadius: 12,
                      border: '1px solid var(--line)',
                      background: 'var(--bg-2)',
                      color: 'var(--ink-0)',
                    }}
                    value={title}
                  />
                </label>

                <label style={{ display: 'grid', gap: 8 }}>
                  <span className="eyebrow">Default artifact</span>
                  <select
                    name="defaultGeneratorSlug"
                    onChange={(event) => setDefaultGeneratorSlug(event.target.value)}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      borderRadius: 12,
                      border: '1px solid var(--line)',
                      background: 'var(--bg-2)',
                      color: 'var(--ink-0)',
                    }}
                    value={defaultGeneratorSlug}
                  >
                    {TOPIC_TEMPLATE_OPTIONS.map((option) => (
                      <option key={option.slug} value={option.slug}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              <label style={{ display: 'grid', gap: 8 }}>
                <span className="eyebrow">Starter question</span>
                <textarea
                  name="question"
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="What should this room help the team decide?"
                  rows={2}
                  style={{
                    width: '100%',
                    resize: 'vertical',
                    padding: '12px 14px',
                    borderRadius: 12,
                    border: '1px solid var(--line)',
                    background: 'var(--bg-2)',
                    color: 'var(--ink-0)',
                  }}
                  value={question}
                />
              </label>

              <label style={{ display: 'grid', gap: 8 }}>
                <span className="eyebrow">What this room is for</span>
                <textarea
                  name="summary"
                  onChange={(event) => setSummary(event.target.value)}
                  placeholder="Optional: describe the decision, KPI, or workflow this room should track."
                  rows={2}
                  style={{
                    width: '100%',
                    resize: 'vertical',
                    padding: '12px 14px',
                    borderRadius: 12,
                    border: '1px solid var(--line)',
                    background: 'var(--bg-2)',
                    color: 'var(--ink-0)',
                  }}
                  value={summary}
                />
              </label>

              <div style={{ display: 'grid', gap: 10 }}>
                <div className="eyebrow">Connected sources</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                  {integrations.map((integration) => (
                    <label
                      key={integration.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 10,
                        padding: '12px 14px',
                        borderRadius: 12,
                        border: '1px solid var(--line)',
                        background: selectedSourceIds.includes(integration.id) ? 'var(--bg-2)' : 'transparent',
                      }}
                    >
                      <input
                        checked={selectedSourceIds.includes(integration.id)}
                        name={`source-${integration.id}`}
                    disabled={isSaving}
                    onChange={() => toggleSource(integration.id)}
                    type="checkbox"
                  />
                      <span>
                        <span className="strong" style={{ display: 'block' }}>{integration.name}</span>
                        <span className="muted" style={{ display: 'block', fontSize: 11.5 }}>{integration.purpose}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {formError ? (
                <div style={{ color: 'var(--bad)', fontSize: 12.5 }}>{formError}</div>
              ) : null}

              <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
                <div className="muted" style={{ fontSize: 12 }}>
                  {topics.length} total topic rooms available after this add.
                </div>
                <div className="row" style={{ gap: 10 }}>
                  <button className="btn btn-sm btn-ghost" disabled={isSaving} onClick={toggleCreateForm} type="button">
                    Cancel
                  </button>
                  <button className="btn btn-sm btn-primary" disabled={isSaving} type="submit">
                    {isSaving ? 'Saving…' : 'Create topic'}
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
              {suggestedSourceIds.slice(0, 3).map((sourceId) => {
                const integration = integrations.find((item) => item.id === sourceId)
                if (!integration) {
                  return null
                }

                return (
                  <Cite
                    key={integration.id}
                    connector={connectorKeyFromId(integration.id)}
                    href={sourceHref(integration.id)}
                    label={integration.name}
                  />
                )
              })}
            </div>
          )}
        </div>
      </div>

      <div className="surface">
        <SectionHead title="Problem rooms" eyebrow="CURRENT PRODUCT QUESTIONS" />
        <table className="dfi-table">
          <tbody>
            {topics.map((topic) => (
              <tr key={topic.id}>
                <td style={{ width: '40%' }}>
                  <a className="strong" href={topicHref(topic.id)}>{topic.title}</a>
                  <div className="muted">{topic.summary}</div>
                </td>
                <td>
                  <div className="row" style={{ gap: 4, flexWrap: 'wrap' }}>
                    {topicSources(topic, data).slice(0, 5).map((integration) => (
                      <Cite
                        key={integration.id}
                        connector={connectorKeyFromId(integration.id)}
                        href={sourceHref(integration.id)}
                        label={integration.name}
                      />
                    ))}
                  </div>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <a className="btn btn-sm" href={topicHref(topic.id)}>Open room</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function TopicNewPage({ data, topicId }: TopicNewPageProps) {
  const { buildAskHref, buildGenerateHref, topicById } = useConsoleWorkspace()
  const topic = topicById(topicId)
  const workflow = workflowByTopicId(topicId)

  if (!topic) {
    return <TopicDirectory data={data} />
  }

  const integrations = topicSources(topic, data)
  const primaryQuestion = topic.question
  const timelineRows = workflow?.gates.length ? workflow.gates : fallbackTimeline(topic)

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TOPIC ROOM</div>

      <div className="row" style={{ marginBottom: 24, gap: 14 }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em' }}>
          {topic.title}
        </h1>
        {workflow ? <Chip tone={toneForWorkflowTone(workflow.currentState.tone)}>{workflow.currentState.phase}</Chip> : <Chip tone="signal">custom room</Chip>}
        <Chip>{`${topic.sources.length} connected sources`}</Chip>
        <div className="spacer" />
        <a className="btn btn-sm" href={buildAskHref({ question: primaryQuestion, topicId: topic.id })}>Ask about this topic</a>
        <a className="btn btn-sm btn-primary" href={buildGenerateHref(topic.defaultGeneratorSlug ?? 'weekly-brief', { question: primaryQuestion, topicId: topic.id })}>Generate</a>
      </div>

      <div className="surface" style={{ marginBottom: 20, borderColor: 'rgba(184,255,61,0.25)' }}>
        <div style={{ padding: '22px 24px' }}>
          <div className="eyebrow" style={{ marginBottom: 10, color: 'var(--signal)' }}>DECISION READY</div>
          <p style={{ fontSize: 18, lineHeight: 1.45, color: 'var(--ink-0)', margin: 0, fontFamily: 'var(--font-serif)' }}>
            {workflow?.nextDecision ?? topic.summary}
          </p>
          <div style={{ display: 'flex', gap: 10, marginTop: 18, flexWrap: 'wrap' }}>
            <a className="btn btn-primary" href={buildGenerateHref(topic.defaultGeneratorSlug ?? 'weekly-brief', { question: primaryQuestion, topicId: topic.id })}>Approve and draft</a>
            <a className="btn" href={buildAskHref({ question: primaryQuestion, topicId: topic.id })}>Discuss in ask</a>
            <a className="btn btn-ghost" href="/console/trust">Open trust</a>
          </div>
        </div>
      </div>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          {topic.toplineMetrics.map((metric) => (
            <KPI
              key={metric.label}
              label={metric.label.toUpperCase()}
              value={metric.value}
              delta={metric.detail}
              source={
                metric.sourceId
                  ? {
                      connector: connectorKeyFromId(metric.sourceId),
                      href: sourceHref(metric.sourceId),
                      label: metric.sourceId,
                    }
                  : undefined
              }
            />
          ))}
          <KPI
            label="NEXT ARTIFACT"
            value={topic.artifacts[0] ?? 'Weekly PM Brief'}
            delta={workflow?.currentState.readiness ?? 'ready to scope'}
            deltaTone={workflow?.currentState.tone === 'blocked' ? 'down' : 'up'}
          />
        </div>
      </div>

      <div className="surface" style={{ marginBottom: 20 }}>
        <SectionHead title="Timeline" eyebrow="WHAT HAPPENED" />
        <div style={{ padding: '6px 0' }}>
          {timelineRows.map((gate, index, all) => (
            <div
              key={gate.label}
              style={{
                display: 'grid',
                gridTemplateColumns: '140px 120px 1fr',
                gap: 16,
                padding: '14px 24px',
                borderBottom: index < all.length - 1 ? '1px solid var(--line)' : 'none',
              }}
            >
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--ink-2)' }}>{gate.label}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-1)' }}>{gate.summary}</div>
              <div>
                <div style={{ color: 'var(--ink-0)', fontSize: 13.5 }}>{gate.detail}</div>
                <div className="row" style={{ marginTop: 6, gap: 6, flexWrap: 'wrap' }}>
                  {gate.sourceIds.map((sourceId) => (
                    <Cite key={sourceId} connector={connectorKeyFromId(sourceId)} href={sourceHref(sourceId)} label={sourceId} />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="surface">
          <SectionHead title="Signals" eyebrow="WHAT THE ROOM KNOWS" />
          <table className="dfi-table">
            <tbody>
              {topic.signals.map((signal) => (
                <tr key={signal.label}>
                  <td>
                    {signal.sourceId ? (
                      <Cite connector={connectorKeyFromId(signal.sourceId)} href={sourceHref(signal.sourceId)} label={signal.label} />
                    ) : (
                      <span className="strong">{signal.label}</span>
                    )}
                  </td>
                  <td className="num">{signal.value}</td>
                  <td className="muted">{signal.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="surface">
          <SectionHead title="Linked work" eyebrow="WHAT HAPPENS NEXT" />
          <table className="dfi-table">
            <tbody>
              {topic.artifacts.map((artifact) => (
                <tr key={artifact}>
                  <td className="strong">{artifact}</td>
                  <td className="muted">Generate from this room</td>
                  <td style={{ textAlign: 'right' }}>
                    <a className="btn btn-sm" href={buildGenerateHref(artifact.toLowerCase().replace(/[^a-z0-9]+/g, '-'), { question: primaryQuestion, topicId: topic.id })}>
                      Open
                    </a>
                  </td>
                </tr>
              ))}
              {integrations.map((integration) => (
                <tr key={integration.id}>
                  <td>
                    <Cite connector={connectorKeyFromId(integration.id)} href={sourceHref(integration.id)} label={integration.name} />
                  </td>
                  <td className="muted">{integration.purpose}</td>
                  <td style={{ textAlign: 'right' }}>
                    <a className="btn btn-sm" href={sourceHref(integration.id)}>Inspect</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

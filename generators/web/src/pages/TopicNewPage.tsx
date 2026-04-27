import { productTopics, topicById, type ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ConsolePayload } from '../types/console'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { Chip, Cite, KPI, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { sourceHref, toneForWorkflowTone, topicHref } from './redesignSupport'

type TopicNewPageProps = {
  data: ConsolePayload | null
  topicId: string | null
}

function topicSources(topic: ProductTopic, data: ConsolePayload | null) {
  const integrations = data?.integrations ?? []
  return topic.sources
    .map((sourceId) => integrations.find((integration) => integration.id === sourceId))
    .filter((integration): integration is NonNullable<typeof integration> => Boolean(integration))
}

function TopicDirectory({ data }: { data: ConsolePayload | null }) {
  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TOPICS</div>
      <h1 className="display-question" style={{ marginBottom: 24, maxWidth: 820 }}>
        Choose the <em>decision room</em> before choosing the tool.
      </h1>

      <div className="surface">
        <SectionHead title="Problem rooms" eyebrow="CURRENT PRODUCT QUESTIONS" />
        <table className="dfi-table">
          <tbody>
            {productTopics.map((topic) => (
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
  const topic = topicById(topicId)
  const workflow = workflowByTopicId(topicId)
  const { buildAskHref, buildGenerateHref } = useConsoleWorkspace()

  if (!topic) {
    return <TopicDirectory data={data} />
  }

  const integrations = topicSources(topic, data)
  const primaryQuestion = topic.question

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TOPIC ROOM</div>

      <div className="row" style={{ marginBottom: 24, gap: 14 }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em' }}>
          {topic.title}
        </h1>
        {workflow ? <Chip tone={toneForWorkflowTone(workflow.currentState.tone)}>{workflow.currentState.phase}</Chip> : null}
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
          {(workflow?.gates ?? []).map((gate, index, all) => (
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

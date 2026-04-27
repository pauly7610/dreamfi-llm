import { productTopics } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { Chip, Cite, KPI, SectionHead, Spark, connectorKeyFromId } from '../components/system/atoms'
import {
  labelForIntegrationStatus,
  sourceHref,
  toneForIntegrationStatus,
  toneForWorkflowTone,
  topicHref,
  topicSparkValues,
} from './redesignSupport'

type HomeNewPageProps = {
  data: ConsolePayload | null
  error?: string | null
  retry?: () => void
}

export function HomeNewPage({ data, error, retry }: HomeNewPageProps) {
  const summary = data?.summary
  const integrations = data?.integrations ?? []
  const topicRows = productTopics.slice(0, 4).map((topic) => {
    const workflow = workflowByTopicId(topic.id)
    return {
      href: topicHref(topic.id),
      label: topic.question,
      metric: topic.toplineMetrics[0]?.value ?? `${topic.sources.length} sources`,
      metricLabel: topic.toplineMetrics[0]?.label.toLowerCase() ?? 'sources',
      status: workflow?.currentState.readiness ?? topic.summary,
      tone: workflow ? toneForWorkflowTone(workflow.currentState.tone) : 'ready',
      topic,
    }
  })

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>HOME</div>

      <h1 className="display-question" style={{ marginBottom: 24, maxWidth: 880 }}>
        Good morning. <em>The product room</em> is ready.
      </h1>

      {error ? (
        <div className="banner" style={{ marginBottom: 20 }}>
          <div>
            <div className="eyebrow" style={{ color: 'var(--bad)' }}>Data fallback</div>
            <p>{error}</p>
          </div>
          {retry ? (
            <button className="btn btn-sm" onClick={retry} type="button">
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <KPI label="OPEN THREADS" value={topicRows.length} delta={`${summary?.needs_review_count ?? 0} require review`} />
          <KPI
            label="DECISIONS PENDING"
            value={summary?.needs_review_count ?? 0}
            delta={`${summary?.blocked_artifact_count ?? 0} blocked artifacts`}
            deltaTone={(summary?.blocked_artifact_count ?? 0) > 0 ? 'down' : 'flat'}
          />
          <KPI label="TRUST POSTURE" value={formatPercent(summary?.hard_gate_pass_rate)} delta="hard-gate pass rate" deltaTone="up" />
          <KPI
            label="SOURCES FRESH"
            value={`${integrations.filter((integration) => integration.status === 'connected').length} / ${integrations.length || 1}`}
            delta={
              integrations.find((integration) => integration.status === 'degraded')
                ? `${integrations.find((integration) => integration.status === 'degraded')?.name} needs attention`
                : 'all connected sources healthy'
            }
            deltaTone={integrations.some((integration) => integration.status === 'degraded') ? 'down' : 'up'}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20 }}>
        <div className="surface">
          <SectionHead title="Open threads" eyebrow="YOUR ATTENTION" right={<a className="btn btn-sm btn-ghost" href="/console/knowledge/ask">Ask new question</a>} />
          <table className="dfi-table">
            <tbody>
              {topicRows.map((row) => (
                <tr key={row.topic.id}>
                  <td style={{ width: '52%' }}>
                    <a className="strong" href={row.href} style={{ display: 'block', fontFamily: 'var(--font-serif)', fontSize: 16, lineHeight: 1.3 }}>
                      {row.label}
                    </a>
                    <div className="muted">{row.status}</div>
                  </td>
                  <td>
                    <Chip tone={row.tone}>{row.topic.title}</Chip>
                  </td>
                  <td>
                    <div className="num">{row.metric}</div>
                    <div className="muted">{row.metricLabel}</div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <a className="btn btn-sm" href={row.href}>
                      Open
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="surface">
          <SectionHead title="Topic pulse" eyebrow="LAST 14 DAYS" />
          <div style={{ padding: '8px 0' }}>
            {productTopics.slice(0, 4).map((topic, index) => {
              const workflow = workflowByTopicId(topic.id)
              const tone = workflow ? toneForWorkflowTone(workflow.currentState.tone) : 'ready'
              const state = workflow?.currentState.phase ?? 'active'
              return (
                <a
                  key={topic.id}
                  href={topicHref(topic.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 18px',
                    borderBottom: index < 3 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: 'var(--ink-0)' }}>{topic.title}</div>
                    <Chip tone={tone}>{state}</Chip>
                  </div>
                  <Spark values={topicSparkValues(topic.id)} hiAt={13} />
                </a>
              )
            })}
          </div>
        </div>
      </div>

      <div className="surface" id="sources" style={{ marginTop: 20 }}>
        <SectionHead title="Source health" eyebrow="WHAT'S GROUNDED" right={<a className="btn btn-sm btn-ghost" href="/console/integrations">Browse connectors</a>} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))' }}>
          {integrations.map((integration, index) => (
            <a
              key={integration.id}
              href={sourceHref(integration.id)}
              style={{
                padding: '16px 18px',
                borderRight: (index + 1) % 5 ? '1px solid var(--line)' : 'none',
                borderTop: index >= 5 ? '1px solid var(--line)' : 'none',
              }}
            >
              <div className="row" style={{ marginBottom: 8 }}>
                <Cite connector={connectorKeyFromId(integration.id)} label={integration.name} />
                <div className="spacer" />
                <Chip tone={toneForIntegrationStatus(integration.status)}>{labelForIntegrationStatus(integration.status)}</Chip>
              </div>
              <div className="num" style={{ fontSize: 16 }}>{integration.category.replace('_', ' ')}</div>
              <div className="muted" style={{ fontSize: 11 }}>{integration.purpose}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}

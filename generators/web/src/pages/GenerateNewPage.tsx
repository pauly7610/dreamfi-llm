import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { Chip, Cite, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { topicById } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import { generatorTitleFromSlug } from '../utils/consoleRoutes'
import { sourceHref, topicHref, toneForIntegrationStatus } from './redesignSupport'

type GenerateNewPageProps = {
  data: ConsolePayload | null
  templateName: string
}

export function GenerateNewPage({ data, templateName }: GenerateNewPageProps) {
  const {
    buildAskHref,
    buildGenerateHref,
    currentQuestion,
    currentSource,
    currentSourceId,
    currentTopic,
    currentTopicId,
  } = useConsoleWorkspace()
  const topic = topicById(currentTopicId)
  const workflow = workflowByTopicId(currentTopicId)
  const templateTitle = generatorTitleFromSlug(templateName)
  const sourceList = topic
    ? topic.sources
    : currentSourceId
      ? [currentSourceId]
      : []

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>{`GENERATE · ${templateTitle.toUpperCase()}`}</div>

      <div className="row" style={{ marginBottom: 24, flexWrap: 'wrap' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em' }}>
          {templateTitle}
        </h1>
        <div className="spacer" />
        <a className="btn btn-sm" href={buildAskHref()}>Back to ask</a>
        <a className="btn btn-sm" href="/console/review">Send to inbox</a>
        <a className="btn btn-sm btn-primary" href="/console/artifacts">Open artifacts</a>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 20 }}>
        <div className="surface">
          <div style={{ padding: '32px 40px' }}>
            <div style={{ marginBottom: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>BACKGROUND</div>
              <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--ink-1)' }}>
                {currentQuestion || topic?.question || 'Start from the active question so the draft is not blank.'}
              </p>
            </div>
            <div style={{ marginBottom: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>PROPOSED CHANGE</div>
              <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--ink-1)' }}>
                {workflow?.recommendation ?? currentSource?.purpose ?? 'Use the current source slice to draft a grounded artifact.'}
              </p>
            </div>
            <div style={{ marginBottom: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>EXPECTED IMPACT</div>
              <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--ink-1)' }}>
                {topic?.toplineMetrics.map((metric) => `${metric.label}: ${metric.value}`).join(' · ') || 'This artifact should stay anchored to measurable product movement.'}
              </p>
            </div>
            <div>
              <div className="eyebrow" style={{ marginBottom: 8 }}>ROLLBACK PLAN</div>
              <p style={{ fontSize: 14.5, lineHeight: 1.65, color: 'var(--ink-1)' }}>
                Keep trust visible. If source health degrades or confidence drops, route the work back to Inbox instead of publishing.
              </p>
            </div>
          </div>
        </div>

        <div className="col" style={{ gap: 20 }}>
          <div className="surface">
            <SectionHead title="Publish checklist" eyebrow="HARD GATES" />
            <div style={{ padding: '4px 0' }}>
              {[
                ['Every claim cited', sourceList.length > 0 ? 'pass' : 'needs sources', sourceList.length > 0 ? 'ready' : 'warn'],
                ['Confidence', formatPercent(data?.summary.average_confidence), (data?.summary.average_confidence ?? 0) >= 0.7 ? 'ready' : 'warn'],
                ['Connector posture', currentSource ? currentSource.status : 'connected', currentSource ? toneForIntegrationStatus(currentSource.status) : 'ready'],
                ['Trust gate', formatPercent(data?.summary.hard_gate_pass_rate), (data?.summary.hard_gate_pass_rate ?? 0) >= 0.8 ? 'ready' : 'warn'],
              ].map(([label, value, tone], index, all) => (
                <div
                  key={label}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '12px 18px',
                    borderBottom: index < all.length - 1 ? '1px solid var(--line)' : 'none',
                  }}
                >
                  <Chip tone={tone as 'ready' | 'warn'}>{value}</Chip>
                  <div className="strong">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="surface">
            <SectionHead title="Context carried forward" eyebrow="GROUND" />
            <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {topic ? <a className="subtle-chip" href={topicHref(topic.id)}>{`Topic · ${topic.title}`}</a> : null}
              {currentSource ? <a className="subtle-chip" href={sourceHref(currentSource.id)}>{`Source · ${currentSource.name}`}</a> : null}
              {sourceList.map((sourceId) => (
                <Cite key={sourceId} connector={connectorKeyFromId(sourceId)} href={sourceHref(sourceId)} label={sourceId} />
              ))}
            </div>
          </div>

          <div className="surface">
            <SectionHead title="Switch templates" eyebrow="STAY IN THREAD" />
            <table className="dfi-table">
              <tbody>
                {['weekly-brief', 'technical-prd', 'business-prd', 'risk-brd']
                  .filter((slug) => slug !== templateName)
                  .map((slug) => (
                    <tr key={slug}>
                      <td className="strong">{generatorTitleFromSlug(slug)}</td>
                      <td className="muted">Reuse the same citations and question context.</td>
                      <td style={{ textAlign: 'right' }}>
                        <a className="btn btn-sm" href={buildGenerateHref(slug)}>Open</a>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

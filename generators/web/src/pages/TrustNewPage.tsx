import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { Chip, Cite, KPI, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { artifactHref, labelForIntegrationStatus, sourceHref, toneForArtifactStatus, toneForIntegrationStatus } from './redesignSupport'

type TrustNewPageProps = {
  data: ConsolePayload | null
}

function formatTimestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Not scheduled'
}

export function TrustNewPage({ data }: TrustNewPageProps) {
  const integrations = data?.integrations ?? []
  const sourceInsights = data?.source_insights ?? []
  const sourcePackets = data?.source_packets ?? []
  const sourceContradictions = data?.source_contradictions ?? []
  const sourceRefresh = data?.source_refresh ?? null
  const evidenceExport = data?.evidence_export_summary ?? null
  const artifacts = data?.artifact_queue ?? []
  const summary = data?.summary
  const firstGap = sourceInsights.find((insight) => insight.gap || insight.quality.blockers.length) ?? null
  const averageSourceQuality = sourceInsights.length
    ? sourceInsights.reduce((total, insight) => total + insight.quality.score, 0) / sourceInsights.length
    : null
  const sourceQualityDelta = sourceInsights.length === 0
    ? 'no source packets yet'
    : firstGap
      ? `${firstGap.source_name} has an evidence gap`
      : 'source intelligence is usable'

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TRUST / SYSTEM HEALTH</div>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em', marginBottom: 20 }}>
        Where the system stands
      </h1>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div className="kpi-grid">
          <KPI label="POSTURE" value={formatPercent(summary?.hard_gate_pass_rate)} delta="hard-gate pass rate" deltaTone="up" />
          <KPI label="CONFIDENCE" value={formatPercent(summary?.average_confidence)} delta="current average" deltaTone="up" />
          <KPI label="BLOCKED" value={summary?.blocked_artifact_count ?? 0} delta="artifacts need intervention" deltaTone={(summary?.blocked_artifact_count ?? 0) > 0 ? 'down' : 'flat'} />
          <KPI
            label="SOURCE QUALITY"
            value={formatPercent(averageSourceQuality)}
            delta={sourceQualityDelta}
            deltaTone={!sourceInsights.length ? 'flat' : firstGap ? 'down' : 'up'}
          />
        </div>
      </div>

      <div className="trust-main-grid">
        <div className="surface">
          <SectionHead title="Source evidence" eyebrow="GROUND TRUTH" />
          <div className="table-scroll table-scroll-medium">
            <table className="dfi-table">
              <tbody>
                {sourceInsights.length > 0 ? sourceInsights.map((insight) => (
                  <tr key={insight.insight_id}>
                    <td>
                      <Cite connector={connectorKeyFromId(insight.source_id)} href={sourceHref(insight.source_id)} label={insight.source_name} />
                    </td>
                    <td className="muted">{insight.title}</td>
                    <td><Chip tone={insight.quality.blockers.length ? 'warn' : 'ready'}>{Math.round(insight.quality.score * 100)} quality</Chip></td>
                    <td className="muted">{insight.gap ?? insight.finding}</td>
                  </tr>
                )) : integrations.map((integration) => (
                  <tr key={integration.id}>
                    <td>
                      <Cite connector={connectorKeyFromId(integration.id)} href={sourceHref(integration.id)} label={integration.name} />
                    </td>
                    <td className="muted">{integration.category.replace('_', ' ')}</td>
                    <td><Chip tone={toneForIntegrationStatus(integration.status)}>{labelForIntegrationStatus(integration.status)}</Chip></td>
                    <td className="muted">{integration.purpose}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="surface">
          <SectionHead title="Artifact posture" eyebrow="CURRENT QUEUE" />
          <div className="table-scroll table-scroll-medium">
            <table className="dfi-table">
              <tbody>
                {artifacts.map((artifact) => (
                  <tr key={artifact.output_id}>
                    <td className="strong">{artifact.test_input_label}</td>
                    <td className="num">{artifact.confidence?.toFixed(2) ?? '--'}</td>
                    <td><Chip tone={toneForArtifactStatus(artifact.status)}>{artifact.status.replace('_', ' ')}</Chip></td>
                    <td style={{ textAlign: 'right' }}>
                      <a className="btn btn-sm" href={artifactHref(artifact.output_id)}>Resolve</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="trust-main-grid" style={{ marginBottom: 20 }}>
        <div className="surface">
          <SectionHead
            title="SOC2 evidence export"
            eyebrow="AUDIT PACKAGE"
            right={<a className="btn btn-sm btn-ghost" href={evidenceExport?.href ?? '/api/console/evidence-export'}>Download JSON</a>}
          />
          <div className="table-scroll table-scroll-medium">
            <table className="dfi-table">
              <tbody>
                <tr>
                  <td className="strong">Source packets</td>
                  <td className="num">{evidenceExport?.source_packet_count ?? sourcePackets.length}</td>
                  <td className="muted">{`${evidenceExport?.real_source_packet_count ?? 0} persisted / ${evidenceExport?.demo_source_packet_count ?? 0} demo`}</td>
                </tr>
                <tr>
                  <td className="strong">Contradictions</td>
                  <td className="num">{evidenceExport?.contradiction_count ?? sourceContradictions.length}</td>
                  <td className="muted">Included so review can verify conflicting signals before decisions.</td>
                </tr>
                <tr>
                  <td className="strong">Demo data</td>
                  <td>
                    <Chip tone={evidenceExport?.contains_demo_data ? 'signal' : 'ready'}>
                      {evidenceExport?.contains_demo_data ? 'present' : 'absent'}
                    </Chip>
                  </td>
                  <td className="muted">Demo packets disappear per source once real packets persist.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="surface">
          <SectionHead title="Source refresh" eyebrow="SCHEDULED JOBS" />
          <div className="table-scroll table-scroll-medium">
            <table className="dfi-table">
              <tbody>
                <tr>
                  <td className="strong">Schedule</td>
                  <td>
                    <Chip tone={sourceRefresh?.configured ? 'ready' : 'warn'}>
                      {sourceRefresh?.configured ? 'configured' : 'not configured'}
                    </Chip>
                  </td>
                  <td className="muted">{sourceRefresh?.cadence_days ? `Every ${sourceRefresh.cadence_days} day(s)` : 'Use the schedule endpoint after API keys are saved.'}</td>
                </tr>
                <tr>
                  <td className="strong">Next run</td>
                  <td className="muted">{formatTimestamp(sourceRefresh?.next_run_at ?? null)}</td>
                  <td className="muted">{sourceRefresh?.latest_sync_status ? `Latest sync: ${sourceRefresh.latest_sync_status}` : 'No sync run yet'}</td>
                </tr>
                <tr>
                  <td className="strong">Freshness risks</td>
                  <td className="num">{(sourceRefresh?.failed_source_count ?? 0) + (sourceRefresh?.stale_source_count ?? 0)}</td>
                  <td className="muted">{`${sourceRefresh?.failed_source_count ?? 0} failed / ${sourceRefresh?.stale_source_count ?? 0} stale`}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {sourceContradictions.length > 0 ? (
        <div className="surface" style={{ marginBottom: 20 }}>
          <SectionHead title="Source contradictions" eyebrow="VERIFY BEFORE ACTION" />
          <div className="table-scroll table-scroll-wide">
            <table className="dfi-table">
              <tbody>
                {sourceContradictions.map((item) => (
                  <tr key={item.contradiction_id}>
                    <td className="strong">{item.title}</td>
                    <td className="muted">{item.summary}</td>
                    <td><Chip tone={item.is_demo ? 'signal' : 'warn'}>{item.is_demo ? 'demo' : item.severity}</Chip></td>
                    <td className="muted">{item.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="surface">
        <SectionHead title="Alerts" eyebrow="WHAT NEEDS ATTENTION" right={<a className="btn btn-sm btn-ghost" href="/console/review">Open inbox</a>} />
        <div className="table-scroll table-scroll-wide">
          <table className="dfi-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Signal</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {(data?.alerts ?? []).map((alert) => (
                <tr key={alert.id}>
                  <td className="muted">{alert.created_at ? new Date(alert.created_at).toLocaleString() : 'Open'}</td>
                  <td>
                    <div className="strong">{alert.title}</div>
                    <div className="muted">{alert.message}</div>
                  </td>
                  <td>
                    <Chip tone={alert.severity === 'critical' ? 'bad' : alert.severity === 'warning' ? 'warn' : 'ready'}>
                      {alert.severity}
                    </Chip>
                  </td>
                  <td>
                    <a className="btn btn-sm" href={alert.href ?? '/console/review'}>Open</a>
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

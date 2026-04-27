import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { Chip, Cite, KPI, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { artifactHref, labelForIntegrationStatus, sourceHref, toneForArtifactStatus, toneForIntegrationStatus } from './redesignSupport'

type TrustNewPageProps = {
  data: ConsolePayload | null
}

export function TrustNewPage({ data }: TrustNewPageProps) {
  const integrations = data?.integrations ?? []
  const artifacts = data?.artifact_queue ?? []
  const summary = data?.summary
  const degraded = integrations.find((integration) => integration.status === 'degraded') ?? null

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>TRUST · SYSTEM HEALTH</div>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em', marginBottom: 20 }}>
        Where the system stands
      </h1>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <KPI label="POSTURE" value={formatPercent(summary?.hard_gate_pass_rate)} delta="hard-gate pass rate" deltaTone="up" />
          <KPI label="CONFIDENCE" value={formatPercent(summary?.average_confidence)} delta="current average" deltaTone="up" />
          <KPI label="BLOCKED" value={summary?.blocked_artifact_count ?? 0} delta="artifacts need intervention" deltaTone={(summary?.blocked_artifact_count ?? 0) > 0 ? 'down' : 'flat'} />
          <KPI
            label="SOURCES"
            value={`${integrations.filter((integration) => integration.status === 'connected').length} / ${integrations.length || 1}`}
            delta={degraded ? `${degraded.name} degraded` : 'healthy connector set'}
            deltaTone={degraded ? 'down' : 'up'}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div className="surface">
          <SectionHead title="Connector health" eyebrow="GROUND TRUTH" />
          <table className="dfi-table">
            <tbody>
              {integrations.map((integration) => (
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

        <div className="surface">
          <SectionHead title="Artifact posture" eyebrow="CURRENT QUEUE" />
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

      <div className="surface">
        <SectionHead title="Alerts" eyebrow="WHAT NEEDS ATTENTION" right={<a className="btn btn-sm btn-ghost" href="/console/review">Open inbox</a>} />
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
  )
}

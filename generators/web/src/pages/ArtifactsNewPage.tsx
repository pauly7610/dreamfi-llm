import type { ConsolePayload } from '../types/console'
import { formatPercent } from '../components/console/formatters'
import { Chip, Cite, KPI, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { artifactHref, generatorSourcesForArtifact, labelForArtifactStatus, toneForArtifactStatus } from './redesignSupport'

type ArtifactsNewPageProps = {
  data: ConsolePayload | null
}

export function ArtifactsNewPage({ data }: ArtifactsNewPageProps) {
  const artifacts = data?.artifact_queue ?? []
  const summary = data?.summary
  const integrations = data?.integrations ?? []

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>ARTIFACTS</div>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em', marginBottom: 20 }}>
        Generated work
      </h1>

      <div className="surface" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <KPI label="IN QUEUE" value={artifacts.length} delta={`${summary?.published_artifact_count ?? 0} published`} deltaTone="up" />
          <KPI label="PUBLISH READY" value={summary?.publish_ready_count ?? 0} delta="ready for operator action" deltaTone="up" />
          <KPI label="BLOCKED" value={summary?.blocked_artifact_count ?? 0} delta="hard-gate failures" deltaTone={(summary?.blocked_artifact_count ?? 0) > 0 ? 'down' : 'flat'} />
          <KPI label="AVG CONFIDENCE" value={formatPercent(summary?.average_confidence)} delta="across current slice" deltaTone="up" />
        </div>
      </div>

      <div className="surface">
        <SectionHead title="All artifacts" eyebrow="GROUNDED · GENERATED · GATED" right={<a className="btn btn-sm" href="/console/review">Open inbox</a>} />
        <table className="dfi-table">
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Skill</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Sources</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => {
              const sources = generatorSourcesForArtifact(artifact, integrations)
              return (
                <tr key={artifact.output_id}>
                  <td className="strong">{artifact.test_input_label}</td>
                  <td className="muted">{artifact.skill_display_name ?? artifact.skill_id ?? 'Artifact'}</td>
                  <td className="num">{artifact.confidence?.toFixed(2) ?? '--'}</td>
                  <td>
                    <Chip tone={toneForArtifactStatus(artifact.status)}>{labelForArtifactStatus(artifact.status)}</Chip>
                  </td>
                  <td>
                    <div className="row" style={{ gap: 4, flexWrap: 'wrap' }}>
                      {sources.length > 0 ? (
                        sources.map((source) => (
                          <Cite key={source.id} connector={connectorKeyFromId(source.id)} href={source.href} label={source.name} />
                        ))
                      ) : (
                        <span className="muted">No mapped sources</span>
                      )}
                    </div>
                  </td>
                  <td className="muted">{new Date(artifact.created_at).toLocaleDateString()}</td>
                  <td style={{ textAlign: 'right' }}>
                    <a className="btn btn-sm" href={artifactHref(artifact.output_id)}>Open</a>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

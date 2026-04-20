import type { ArtifactRecord } from '../../types/console'
import { formatArtifactStatus, formatDate, formatScore } from './formatters'

type PriorityQueueProps = {
  artifacts: ArtifactRecord[]
  title?: string
}

function PriorityQueue({ artifacts, title = 'Priority queue' }: PriorityQueueProps) {
  return (
    <section className="priority-queue panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Artifacts</span>
          <h2>{title}</h2>
        </div>
        <a className="text-link" href="/console/artifacts">View all artifacts</a>
      </div>
      <div className="queue-list">
        {artifacts.length ? (
          artifacts.map((artifact) => (
            <article key={artifact.output_id} className="queue-row">
              <div className="queue-main">
                <div className="queue-headline">
                  <div>
                    <strong>{artifact.skill_display_name ?? artifact.skill_id ?? 'Unknown skill'}</strong>
                    <p>{artifact.test_input_label}</p>
                  </div>
                  <span className={`status-badge ${artifact.status}`}>{formatArtifactStatus(artifact.status)}</span>
                </div>
                <dl className="queue-metrics">
                  <div>
                    <dt>Confidence</dt>
                    <dd>{formatScore(artifact.confidence)}</dd>
                  </div>
                  <div>
                    <dt>Readiness</dt>
                    <dd>{formatScore(artifact.export_readiness)}</dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{formatDate(artifact.created_at)}</dd>
                  </div>
                </dl>
              </div>
              <div className="queue-actions">
                <a href={`/console/artifacts?focus=${artifact.output_id}`}>Inspect</a>
                {(artifact.status === 'blocked' || artifact.status === 'needs_review') && (
                  <a href={`/console/review?focus=${artifact.output_id}`}>Review</a>
                )}
                {artifact.status === 'publish_ready' && (
                  <a href={`/console/artifacts?status=publish_ready&focus=${artifact.output_id}`}>Publish</a>
                )}
                <a href={`/console/generate/${artifact.skill_id ?? 'artifact'}?source=${artifact.output_id}`}>Regenerate</a>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state compact">
            <h3>No artifacts yet</h3>
            <p>Run a generation workflow to populate the queue.</p>
          </div>
        )}
      </div>
    </section>
  )
}

export default PriorityQueue

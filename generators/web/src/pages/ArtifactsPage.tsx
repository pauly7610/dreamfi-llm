import PriorityQueue from '../components/console/PriorityQueue'
import type { ConsolePayload } from '../types/console'

type ArtifactsPageProps = {
  data: ConsolePayload | null
}

function ArtifactsPage({ data }: ArtifactsPageProps) {
  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Artifacts</span>
        <h2>Inspect recent governed outputs</h2>
        <p>Open generated artifacts, review readiness, and move quickly into inspect, review, publish, or regenerate flows.</p>
      </section>
      <PriorityQueue artifacts={data?.artifact_queue ?? []} title="Recent artifact activity" />
    </div>
  )
}

export default ArtifactsPage

import AlertsPanel from '../components/console/AlertsPanel'
import PriorityQueue from '../components/console/PriorityQueue'
import type { ConsolePayload } from '../types/console'

type ReviewPageProps = {
  data: ConsolePayload | null
}

function ReviewPage({ data }: ReviewPageProps) {
  const reviewQueue = (data?.artifact_queue ?? []).filter(
    (artifact) => artifact.status === 'blocked' || artifact.status === 'needs_review'
  )

  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Review queue</span>
        <h2>Blocked and risky artifacts</h2>
        <p>Prioritize the artifacts that failed trust gates or still require operator judgment.</p>
      </section>
      <section className="split-grid">
        <PriorityQueue artifacts={reviewQueue} title="Needs review" />
        <AlertsPanel alerts={data?.alerts ?? []} />
      </section>
    </div>
  )
}

export default ReviewPage

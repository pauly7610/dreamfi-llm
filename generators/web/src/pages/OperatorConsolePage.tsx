import ActionCenter from '../components/console/ActionCenter'
import AlertsPanel from '../components/console/AlertsPanel'
import DomainHealthGrid from '../components/console/DomainHealthGrid'
import LoadingSkeleton from '../components/console/LoadingSkeleton'
import PriorityQueue from '../components/console/PriorityQueue'
import RecentPublishList from '../components/console/RecentPublishList'
import SkillSnapshot from '../components/console/SkillSnapshot'
import StatusBar from '../components/console/StatusBar'
import { formatDate, formatPercent, formatScore } from '../components/console/formatters'
import type { ConsolePayload } from '../types/console'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

function OperatorConsolePage({ data, loading, error, retry }: OperatorConsolePageProps) {
  if (loading && !data) {
    return <LoadingSkeleton />
  }

  const statusItems: Array<{
    label: string
    value: string | number
    tone?: 'default' | 'alert' | 'success'
  }> = [
    { label: 'API status', value: error ? 'Degraded' : 'Healthy', tone: error ? 'alert' : 'success' },
    { label: 'Blocked', value: data?.summary.blocked_artifact_count ?? '—', tone: 'alert' as const },
    { label: 'Needs review', value: data?.summary.needs_review_count ?? '—' },
    { label: 'Publish ready', value: data?.summary.publish_ready_count ?? '—', tone: 'success' as const },
    { label: 'Avg trust', value: formatScore(data?.summary.average_export_readiness) },
    { label: 'Latest run', value: formatDate(data?.artifact_queue[0]?.created_at) }
  ]

  return (
    <div className="page-grid">
      <section className="hero-panel panel">
        <div>
          <span className="eyebrow">Operator console</span>
          <h2>Trust-scored product operations</h2>
          <p>
            Monitor blocked work, review publishable artifacts, and run governed workflows across planning, metrics,
            generation, and publish safety.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="/console/generate/weekly-brief">Run weekly PM brief</a>
            <a className="button secondary" href="/console/review">Open review queue</a>
            <a className="button secondary" href="/console/trust">View trust dashboard</a>
          </div>
          {error ? (
            <div className="error-banner">
              <span>{error}</span>
              <button type="button" onClick={retry}>Retry</button>
            </div>
          ) : null}
        </div>
        <div className="hero-aside panel inset-panel">
          <span className="metric-label">Live summary</span>
          <dl className="snapshot-stats compact">
            <div>
              <dt>Hard gate pass rate</dt>
              <dd>{formatPercent(data?.summary.hard_gate_pass_rate)}</dd>
            </div>
            <div>
              <dt>Publish success</dt>
              <dd>{formatPercent(data?.summary.publish_success_rate)}</dd>
            </div>
            <div>
              <dt>Artifacts published</dt>
              <dd>{data?.summary.published_artifact_count ?? '—'}</dd>
            </div>
            <div>
              <dt>Skills tracked</dt>
              <dd>{data?.summary.skill_count ?? '—'}</dd>
            </div>
          </dl>
        </div>
      </section>

      <StatusBar items={statusItems} />
      <ActionCenter actions={data?.quick_actions ?? []} />

      <section className="split-grid">
        <PriorityQueue artifacts={data?.artifact_queue.slice(0, 8) ?? []} title="Priority queue" />
        <AlertsPanel alerts={data?.alerts ?? []} />
      </section>

      <section className="split-grid">
        <DomainHealthGrid items={data?.domain_health ?? []} />
        <RecentPublishList items={data?.publish_activity ?? []} />
      </section>

      <section className="split-grid">
        <SkillSnapshot skills={data?.skills ?? []} />
        <section className="panel compact-info-panel">
          <div className="section-heading">
            <span className="eyebrow">Drill down</span>
            <h2>Fast paths into the right object</h2>
          </div>
          <div className="link-stack">
            <a href="/console/review?status=blocked">Inspect latest blocked artifact</a>
            <a href="/console/artifacts?status=published">Inspect latest published artifact</a>
            <a href="/console/trust#metrics">Inspect latest discrepancy surface</a>
          </div>
        </section>
      </section>
    </div>
  )
}

export default OperatorConsolePage

import type { ConsoleDomainHealth } from '../../types/console'
import { formatPercent, formatScore } from './formatters'

type DomainHealthGridProps = {
  items: ConsoleDomainHealth[]
}

function DomainHealthGrid({ items }: DomainHealthGridProps) {
  return (
    <section className="domain-grid panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Domain health</span>
          <h2>Healthy vs risky surfaces</h2>
        </div>
        <a className="text-link" href="/console/trust">Open trust view</a>
      </div>
      <div className="domain-cards">
        {items.map((item) => (
          <article key={item.domain} className="domain-card">
            <span className="metric-label">{item.domain}</span>
            <strong>{formatScore(item.trust_score)}</strong>
            <dl>
              <div>
                <dt>Pass rate</dt>
                <dd>{formatPercent(item.pass_rate)}</dd>
              </div>
              <div>
                <dt>Issues</dt>
                <dd>{item.issue_count}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}

export default DomainHealthGrid

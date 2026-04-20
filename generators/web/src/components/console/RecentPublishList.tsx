import type { PublishActivity } from '../../types/console'
import { formatDate } from './formatters'

type RecentPublishListProps = {
  items: PublishActivity[]
}

function RecentPublishList({ items }: RecentPublishListProps) {
  return (
    <section className="publish-list-panel panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Recent publish activity</span>
          <h2>Latest policy outcomes</h2>
        </div>
      </div>
      <div className="publish-list">
        {items.length ? (
          items.map((item) => (
            <article key={item.publish_id} className="publish-item-row">
              <div>
                <strong>{item.skill_id}</strong>
                <p>
                  {item.destination}
                  {item.destination_ref ? ` · ${item.destination_ref}` : ''}
                </p>
              </div>
              <div className="publish-item-meta">
                <span className={`status-badge ${item.decision === 'published' ? 'published' : 'blocked'}`}>
                  {item.decision}
                </span>
                <time>{formatDate(item.created_at)}</time>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state compact">
            <h3>No publish attempts</h3>
            <p>Receipts appear here after review and publish flows run.</p>
          </div>
        )}
      </div>
    </section>
  )
}

export default RecentPublishList

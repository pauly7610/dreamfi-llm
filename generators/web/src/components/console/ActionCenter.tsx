import type { QuickAction } from '../../types/console'

type ActionCenterProps = {
  actions: QuickAction[]
}

function ActionCenter({ actions }: ActionCenterProps) {
  return (
    <section className="action-center panel">
      <div className="section-heading">
        <span className="eyebrow">Action center</span>
        <h2>What you can do next</h2>
      </div>
      <div className="action-grid">
        {actions.map((action) => (
          <a key={action.id} className={`action-card ${action.kind}`} href={action.href}>
            <strong>{action.label}</strong>
            <span>{action.href.replace('/console/', '')}</span>
          </a>
        ))}
      </div>
    </section>
  )
}

export default ActionCenter

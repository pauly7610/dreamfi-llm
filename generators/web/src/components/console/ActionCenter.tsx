import type { QuickAction } from '../../types/console'

type ActionCenterProps = {
  actions: QuickAction[]
  eyebrow?: string
  title?: string
  description?: string
}

function ActionCenter({
  actions,
  eyebrow = 'Action center',
  title = 'What you can do next',
  description,
}: ActionCenterProps) {
  return (
    <section className="action-center panel">
      <div className="section-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {description ? <p className="section-subtle">{description}</p> : null}
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

type TrustAction = {
  detail: string
  href: string
  hrefLabel: string
  title: string
  tone?: 'info' | 'ready' | 'warning'
}

type TrustActionRailProps = {
  description: string
  eyebrow?: string
  title: string
  actions: TrustAction[]
}

function TrustActionRail({ description, eyebrow = 'Trust actions', title, actions }: TrustActionRailProps) {
  if (actions.length === 0) {
    return null
  }

  return (
    <section className="trust-action-rail panel">
      <div className="section-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p className="section-subtle">{description}</p>
      </div>
      <div className="trust-action-grid">
        {actions.map((action) => (
          <article key={`${action.title}-${action.href}`} className={`trust-action-card ${action.tone ?? 'info'}`}>
            <strong>{action.title}</strong>
            <p>{action.detail}</p>
            <a className="button secondary" href={action.href}>
              {action.hrefLabel}
            </a>
          </article>
        ))}
      </div>
    </section>
  )
}

export default TrustActionRail

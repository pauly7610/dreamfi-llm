type ContextContinuationCard = {
  detail: string
  href?: string
  hrefLabel?: string
  label: string
  value: string
}

type ContextContinuationAction = {
  href: string
  kind?: 'primary' | 'secondary'
  label: string
}

type ContextContinuationPanelProps = {
  actions?: ContextContinuationAction[]
  cards: ContextContinuationCard[]
  description: string
  eyebrow?: string
  title: string
}

function ContextContinuationPanel({
  actions = [],
  cards,
  description,
  eyebrow = 'Stay in context',
  title,
}: ContextContinuationPanelProps) {
  if (cards.length === 0 && actions.length === 0) {
    return null
  }

  return (
    <section className="context-continuation-panel panel">
      <div className="section-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p className="section-subtle">{description}</p>
      </div>
      {cards.length > 0 ? (
        <div className="context-continuation-grid">
          {cards.map((card) => (
            <article key={`${card.label}-${card.value}`} className="context-continuation-card">
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <p>{card.detail}</p>
              {card.href ? (
                <a className="text-link" href={card.href}>
                  {card.hrefLabel ?? 'Open'}
                </a>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
      {actions.length > 0 ? (
        <div className="context-continuation-actions">
          {actions.map((action) => (
            <a key={`${action.label}-${action.href}`} className={`button ${action.kind ?? 'secondary'}`} href={action.href}>
              {action.label}
            </a>
          ))}
        </div>
      ) : null}
    </section>
  )
}

export default ContextContinuationPanel

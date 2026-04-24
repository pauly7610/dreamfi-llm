type LivePulseItem = {
  detail: string
  href?: string
  hrefLabel?: string
  label: string
  value: string
}

type LivePulsePanelProps = {
  description: string
  items: LivePulseItem[]
  title: string
}

function LivePulsePanel({ description, items, title }: LivePulsePanelProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section className="live-pulse-panel panel">
      <div className="section-heading">
        <span className="eyebrow">Live pulse</span>
        <h2>{title}</h2>
        <p className="section-subtle">{description}</p>
      </div>
      <div className="live-pulse-grid">
        {items.map((item) => (
          <article key={`${item.label}-${item.value}`} className="live-pulse-card">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
            {item.href ? (
              <a className="text-link" href={item.href}>
                {item.hrefLabel ?? 'Open'}
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  )
}

export default LivePulsePanel

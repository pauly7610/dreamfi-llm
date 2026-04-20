type StatusItem = {
  label: string
  value: string | number
  tone?: 'default' | 'alert' | 'success'
}

type StatusBarProps = {
  items: StatusItem[]
}

function StatusBar({ items }: StatusBarProps) {
  return (
    <section className="status-bar panel">
      {items.map((item) => (
        <article key={item.label} className={`status-item ${item.tone ?? 'default'}`}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </section>
  )
}

export default StatusBar

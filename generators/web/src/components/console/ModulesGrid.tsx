import { modules } from '../../config/modules'

type ModulesGridProps = {
  title?: string
  description?: string
}

function ModulesGrid({
  title = 'Make product teams smarter',
  description = 'Five operating surfaces that turn your product context into grounded answers, trusted briefs, and publishable artifacts.',
}: ModulesGridProps) {
  return (
    <section className="modules-hero panel">
      <div className="section-heading">
        <span className="eyebrow">DreamFi modules</span>
        <h2>{title}</h2>
        <p className="section-subtle">{description}</p>
      </div>
      <div className="modules-grid">
        {modules.map((module) => (
          <article key={module.id} className={`module-card accent-${module.accent}`}>
            <header>
              <span className="eyebrow">{module.title}</span>
              <h3>{module.tagline}</h3>
            </header>
            <p>{module.description}</p>
            <ul className="module-capabilities">
              {module.capabilities.map((capability) => (
                <li key={capability}>{capability}</li>
              ))}
            </ul>
            <div className="module-actions">
              <a className="button primary" href={module.primaryActionHref}>
                {module.primaryActionLabel}
              </a>
              <a className="text-link" href={module.route}>Open module</a>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default ModulesGrid

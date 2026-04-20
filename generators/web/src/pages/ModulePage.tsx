import ActionCenter from '../components/console/ActionCenter'
import IntegrationsPanel from '../components/console/IntegrationsPanel'
import PriorityQueue from '../components/console/PriorityQueue'
import type { ModuleDefinition } from '../config/modules'
import type { ConsolePayload } from '../types/console'

type ModulePageProps = {
  module: ModuleDefinition
  data: ConsolePayload | null
}

function ModulePage({ module, data }: ModulePageProps) {
  const integrations = (data?.integrations ?? []).filter((integration) =>
    module.integrations.includes(integration.id),
  )
  const actions = (data?.quick_actions ?? []).filter((action) => module.actions.includes(action.id))
  const relevantArtifacts = (data?.artifact_queue ?? [])
    .filter((artifact) =>
      module.actions.some((actionId) =>
        (artifact.skill_id ?? '').includes(actionId.replace(/-/g, '_')),
      ),
    )
    .slice(0, 6)

  return (
    <div className="page-grid">
      <section className={`panel module-hero accent-${module.accent}`}>
        <div>
          <span className="eyebrow">DreamFi module</span>
          <h2>{module.title}</h2>
          <p className="module-tagline">{module.tagline}</p>
          <p>{module.longDescription}</p>
          <div className="hero-actions">
            <a className="button primary" href={module.primaryActionHref}>
              {module.primaryActionLabel}
            </a>
            <a className="button secondary" href="/console">Back to console</a>
          </div>
        </div>
        <aside className="panel inset-panel module-capabilities-panel">
          <span className="metric-label">What this module does</span>
          <ul className="detail-list">
            {module.capabilities.map((capability) => (
              <li key={capability}>{capability}</li>
            ))}
          </ul>
        </aside>
      </section>

      {actions.length > 0 ? <ActionCenter actions={actions} /> : null}

      <IntegrationsPanel
        items={integrations}
        title="Grounding sources for this module"
        description="These systems feed the context and signals this module needs to stay trusted."
      />

      {relevantArtifacts.length > 0 ? (
        <PriorityQueue artifacts={relevantArtifacts} title="Recent artifacts from this module" />
      ) : null}
    </div>
  )
}

export default ModulePage

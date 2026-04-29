import type { SourceDataPreview } from '../../content/sourceDataPreviews'
import type { ConsoleIntegration } from '../../types/console'

type SourceEvidenceMapProps = {
  source: ConsoleIntegration
  preview: SourceDataPreview
}

const THEME_BY_SOURCE: Record<string, string> = {
  metabase: 'metrics',
  posthog: 'behavior',
  klaviyo: 'marketing',
  ga: 'acquisition',
  jira: 'delivery',
  confluence: 'docs',
  socure: 'socure',
}

const MAP_TITLE_BY_SOURCE: Record<string, string> = {
  metabase: 'Metric pulse map',
  posthog: 'Behavior journey map',
  klaviyo: 'Lifecycle lift map',
  ga: 'Acquisition quality map',
  jira: 'Delivery truth map',
  confluence: 'Decision lineage map',
  socure: 'Risk decision view',
}

const INSPECT_LABELS = ['Watch', 'Investigate', 'Translate']

function themeForSource(sourceId: string): string {
  return THEME_BY_SOURCE[sourceId] ?? 'general'
}

function mapTitle(source: ConsoleIntegration): string {
  return MAP_TITLE_BY_SOURCE[source.id] ?? `${source.name} evidence map`
}

function signalStep(index: number): string {
  return `Signal ${String(index + 1).padStart(2, '0')}`
}

function SourceEvidenceMap({ source, preview }: SourceEvidenceMapProps) {
  const views = preview.views.slice(0, 3)

  return (
    <section id="source-data" className={`source-visual-panel panel source-theme-${themeForSource(source.id)}`}>
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Evidence map</span>
          <h2>{mapTitle(source)}</h2>
          <p className="section-subtle">
            {preview.headline}. {preview.description}
          </p>
        </div>
        <span className="subtle-chip">{preview.primaryDataset}</span>
      </div>

      <div className="source-visual-layout">
        <aside className="source-context-rail">
          <span className="eyebrow">Connector pull</span>
          <strong>{preview.primaryDataset}</strong>
          <p>{preview.freshness}</p>
          <div className="source-context-views" aria-label={`${source.name} views in scope`}>
            {views.map((view) => (
              <span key={view} className="source-context-chip">
                {view}
              </span>
            ))}
          </div>
        </aside>

        <div className="source-evidence-canvas" aria-label={`${source.name} evidence map`}>
          <div className="source-evidence-track" aria-hidden="true" />

          {preview.rows.slice(0, 3).map((row, index) => (
            <article key={row.label} className={`source-signal-node node-${index + 1}`}>
              <span className="source-signal-step">{signalStep(index)}</span>
              <strong>{row.value}</strong>
              <h3>{row.label}</h3>
              <p>{row.detail}</p>
            </article>
          ))}

          {preview.inspect.slice(0, 3).map((item, index) => (
            <aside key={item.title} className={`source-insight-note note-${index + 1}`}>
              <span className="source-insight-kicker">{INSPECT_LABELS[index] ?? 'Inspect'}</span>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </aside>
          ))}
        </div>
      </div>
    </section>
  )
}

export default SourceEvidenceMap

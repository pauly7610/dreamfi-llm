import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import type { ConsolePayload, QuickAction } from '../types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from '../utils/consoleRoutes'

type GeneratePageProps = {
  data: ConsolePayload | null
  templateName: string
}

function actionHref(action: QuickAction, buildGenerateHref: (slug: string) => string): string {
  if (!action.href.startsWith('/console/generate/')) {
    return action.href
  }

  const slug = generatorSlugFromIdentifier(action.href.split('/').filter(Boolean).pop())
  return buildGenerateHref(slug)
}

function GeneratePage({ data, templateName }: GeneratePageProps) {
  const {
    buildGenerateHref,
    currentQuestion,
    currentSourceLabel,
    currentTopicLabel,
  } = useConsoleWorkspace()
  const pageTitle = generatorTitleFromSlug(templateName)
  const hasContext = Boolean(currentQuestion || currentTopicLabel || currentSourceLabel)

  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Generate</span>
        <h2>{pageTitle}</h2>
        <p>
          Start a governed generation workflow, then inspect the artifact, review trust results, and publish only if
          policy clears.
        </p>
      </section>
      {hasContext ? (
        <section className="generate-context-panel panel">
          <div>
            <span className="eyebrow">Current working context</span>
            <h2>Stay inside the same product thread while you switch outputs.</h2>
            <p>
              DreamFi should carry the active question, topic room, and source workspace into whichever artifact you run
              next.
            </p>
          </div>
          <div className="generate-context-list">
            {currentTopicLabel ? <span className="subtle-chip">Topic · {currentTopicLabel}</span> : null}
            {currentSourceLabel ? <span className="subtle-chip">Source · {currentSourceLabel}</span> : null}
          </div>
          {currentQuestion ? <p className="generate-context-question">{currentQuestion}</p> : null}
        </section>
      ) : null}
      <section className="action-center panel">
        <div className="section-heading">
          <span className="eyebrow">Available workflows</span>
          <h2>Choose the right generation path</h2>
        </div>
        <div className="action-grid">
          {(data?.quick_actions ?? []).map((action) => (
            <a key={action.id} className={`action-card ${action.kind}`} href={actionHref(action, buildGenerateHref)}>
              <strong>{action.label}</strong>
              <span>{action.href.replace('/console/', '')}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

export default GeneratePage

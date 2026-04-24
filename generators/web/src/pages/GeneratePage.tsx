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
    buildAskHref,
    buildGenerateHref,
    currentQuestion,
    currentSource,
    currentSourceLabel,
    currentTopic,
    currentTopicLabel,
  } = useConsoleWorkspace()
  const pageTitle = generatorTitleFromSlug(templateName)
  const hasContext = Boolean(currentQuestion || currentTopicLabel || currentSourceLabel)
  const trustHeadline =
    currentSource?.status === 'degraded' || (currentTopic?.gaps.length ?? 0) > 0
      ? 'Trust review should stay inline during this run.'
      : 'This context is clear enough to start a governed draft.'
  const trustDetail =
    currentSource?.status === 'degraded'
      ? `${currentSource.name} is degraded, so the draft should keep that limitation visible.`
      : currentTopic?.gaps[0] ?? 'No blocking issue is called out in the current topic slice.'

  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Generate</span>
        <h2>{pageTitle}</h2>
        <p>
          Generate from the question already on deck, not from a blank template. DreamFi should carry the active room,
          sources, and trust posture into the artifact from the first draft onward.
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
            {currentTopicLabel ? <span className="subtle-chip">Topic - {currentTopicLabel}</span> : null}
            {currentSourceLabel ? <span className="subtle-chip">Source - {currentSourceLabel}</span> : null}
          </div>
          {currentQuestion ? <p className="generate-context-question">{currentQuestion}</p> : null}
          <div className="generate-proof-grid">
            <article className="generate-proof-card">
              <span>Citations stay attached</span>
              <strong>{currentSourceLabel ? `Grounded in ${currentSourceLabel}` : 'Grounded in the active room'}</strong>
              <p>The artifact should inherit the same source evidence you were already inspecting.</p>
            </article>
            <article className="generate-proof-card">
              <span>Trust stays inline</span>
              <strong>{trustHeadline}</strong>
              <p>{trustDetail}</p>
            </article>
            <article className="generate-proof-card">
              <span>Keep the thread alive</span>
              <strong>Go back without losing context</strong>
              <p>The ask surface stays connected to this generation path, so the question can keep evolving.</p>
            </article>
          </div>
          <div className="generate-context-actions">
            <a className="button secondary" href={buildAskHref()}>Back to receipts</a>
            <a className="button secondary" href="/console/trust">Open trust rails</a>
          </div>
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

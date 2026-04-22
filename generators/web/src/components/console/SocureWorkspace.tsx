import { useMemo, useState } from 'react'

import type { ProductTopic } from '../../content/productTopics'
import type { ConnectorWorkspacePayload, WorkspaceReviewCase } from '../../types/connectorWorkspace'

type SocureWorkspaceProps = {
  relatedTopics: ProductTopic[]
  workspace: ConnectorWorkspacePayload
}

type PromptSuggestion = {
  label: string
  question: string
}

const PROMPT_LABELS = ['Triage', 'Explain', 'Escalate']

function promptSuggestions(workspace: ConnectorWorkspacePayload): PromptSuggestion[] {
  return workspace.questions.slice(0, 3).map((question, index) => ({
    label: PROMPT_LABELS[index] ?? PROMPT_LABELS[PROMPT_LABELS.length - 1],
    question,
  }))
}

function caseStatusLabel(status: WorkspaceReviewCase['status']): string {
  switch (status) {
    case 'questionable':
      return 'Questionable'
    case 'stepped_up':
      return 'Stepped up'
    default:
      return 'Cleared'
  }
}

function caseQuestion(reviewCase: WorkspaceReviewCase | null, workspace: ConnectorWorkspacePayload): string {
  if (!reviewCase) {
    return workspace.questions[0] ?? `What should Product know from ${workspace.connector.name}?`
  }

  if (reviewCase.status === 'stepped_up') {
    return `Why was ${reviewCase.id} stepped up and should Product keep that rule?`
  }

  if (reviewCase.status === 'questionable') {
    return `Why is ${reviewCase.id} questionable and what signal is driving the review?`
  }

  return `Why did ${reviewCase.id} clear and what should Product learn from it?`
}

function helperLine(reviewCase: WorkspaceReviewCase | null, workspace: ConnectorWorkspacePayload, focusTitle: string): string {
  if (!reviewCase) {
    return `The current ${workspace.connector.primaryDataset.toLowerCase()} slice points first to ${focusTitle.toLowerCase()}.`
  }

  return `${reviewCase.id} is currently in ${reviewCase.stage.toLowerCase()}. The review is anchored on ${focusTitle.toLowerCase()}.`
}

function queueSubtitle(reviewCase: WorkspaceReviewCase): string {
  return `${reviewCase.stage} · ${reviewCase.updatedAt}`
}

function SocureWorkspace({ relatedTopics, workspace }: SocureWorkspaceProps) {
  const reviewCases = workspace.reviewCases ?? []
  const suggestions = useMemo(() => promptSuggestions(workspace), [workspace])
  const [selectedCaseIndex, setSelectedCaseIndex] = useState(0)

  const activeCase = reviewCases[selectedCaseIndex] ?? reviewCases[0] ?? null
  const activeFocusIndex =
    workspace.highlights.length > 0 ? (reviewCases.length > 0 ? selectedCaseIndex % workspace.highlights.length : 0) : 0
  const activeSignal = workspace.highlights[activeFocusIndex] ?? workspace.highlights[0] ?? null
  const activeInspect = workspace.inspect[activeFocusIndex] ?? workspace.inspect[0] ?? null
  const initialQuestion = caseQuestion(activeCase, workspace)
  const [draftQuestion, setDraftQuestion] = useState(initialQuestion)
  const [submittedQuestion, setSubmittedQuestion] = useState(initialQuestion)
  const activeWorkflows = workspace.workflows.slice(0, 2)

  return (
    <section id="source-data" className="socure-workspace panel">
      <div className="socure-workspace-header">
        <div>
          <span className="eyebrow">RiskOS workspace</span>
          <h2>Case review queue</h2>
          <p>
            Pull in questionable and stepped-up examples, review the signal behind each one, and decide whether the
            current policy is catching fraud or adding friction.
          </p>
        </div>
        <nav className="socure-workspace-tabs" aria-label="Socure workspace sections">
          <a href="#socure-queue">Review queue</a>
          <a href="#socure-decision-overview">Decision overview</a>
          <a href="#socure-assistant">Assistant</a>
        </nav>
      </div>

      {activeCase ? (
        <section className="socure-active-case-strip" aria-label="Active Socure case">
          <span className={`socure-case-badge status-${activeCase.status}`}>{caseStatusLabel(activeCase.status)}</span>
          <strong>{activeCase.id}</strong>
          <p>{activeCase.detail}</p>
          <b>{activeCase.nextStep}</b>
        </section>
      ) : null}

      <div className="socure-workspace-grid">
        <aside className="socure-rail">
          <div className="socure-rail-section">
            <span className="eyebrow">Connector pull</span>
            <strong>{workspace.connector.primaryDataset}</strong>
            <p>{workspace.connector.freshness}</p>
          </div>

          <div className="socure-rail-section">
            <span className="eyebrow">How to review</span>
            <ol className="socure-guidance-list">
              <li>Scan questionable and stepped-up cases first.</li>
              <li>Use the decision overview to see whether this is a pattern or an outlier.</li>
              <li>Keep the assistant grounded in the active case before escalating.</li>
            </ol>
          </div>

          <div className="socure-rail-section">
            <span className="eyebrow">Views in scope</span>
            <div className="socure-chip-stack">
              {workspace.views.map((view) => (
                <span key={view} className="socure-chip">
                  {view}
                </span>
              ))}
            </div>
          </div>

          {relatedTopics.length > 0 ? (
            <div className="socure-rail-section">
              <span className="eyebrow">Connected rooms</span>
              <div className="socure-topic-list">
                {relatedTopics.map((topic) => (
                  <a key={topic.id} href={`/console/topics/${topic.id}`}>
                    <strong>{topic.title}</strong>
                    <small>{topic.question}</small>
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </aside>

        <div className="socure-main">
          <section id="socure-queue" className="socure-queue-panel">
            <div className="socure-section-intro">
              <span className="eyebrow">Review queue</span>
              <h3>Questionable and stepped-up examples</h3>
              <p>
                Pick a case to review. The selected example drives the explainability and assistant context on this
                page.
              </p>
            </div>

            <div className="socure-queue-list" aria-label="Socure review queue">
              {reviewCases.map((reviewCase, index) => (
                <button
                  key={reviewCase.id}
                  type="button"
                  className={selectedCaseIndex === index ? 'socure-queue-row active' : 'socure-queue-row'}
                  onClick={() => {
                    const nextQuestion = caseQuestion(reviewCase, workspace)
                    setSelectedCaseIndex(index)
                    setDraftQuestion(nextQuestion)
                    setSubmittedQuestion(nextQuestion)
                  }}
                >
                  <span className={`socure-case-badge status-${reviewCase.status}`}>{caseStatusLabel(reviewCase.status)}</span>
                  <span className="socure-queue-primary">
                    <strong>{reviewCase.id}</strong>
                    <small>{queueSubtitle(reviewCase)}</small>
                  </span>
                  <span className="socure-queue-secondary">{reviewCase.signal}</span>
                  <span className="socure-queue-tertiary">{reviewCase.nextStep}</span>
                </button>
              ))}
            </div>
          </section>

          <section id="socure-decision-overview" className="socure-decision-panel">
            <div className="socure-section-intro">
              <span className="eyebrow">Decision overview</span>
              <h3>Pattern snapshot behind the selected case</h3>
              <p>
                Use the current tier and explainability signals to tell whether the active case is isolated or part of a
                larger review trend.
              </p>
            </div>

            <div className="socure-signal-table" aria-label="Socure decision overview">
              {workspace.highlights.map((row, index) => (
                <article key={row.label} className={activeFocusIndex === index ? 'socure-signal-row active' : 'socure-signal-row'}>
                  <div className="socure-signal-rank">{String(index + 1).padStart(2, '0')}</div>
                  <div className="socure-signal-copy">
                    <strong>{row.label}</strong>
                    <p>{row.detail}</p>
                  </div>
                  <div className="socure-signal-value">{row.value}</div>
                </article>
              ))}
            </div>
          </section>

          <section className="socure-explainability-panel">
            <div className="socure-section-intro">
              <span className="eyebrow">Explainability</span>
              <h3>Why this case moved</h3>
              <p>
                Match the active case to the nearest reason-pattern and inspect whether the current rule is too strict,
                too loose, or behaving as expected.
              </p>
            </div>

            <div className="socure-explainability-list">
              {workspace.inspect.map((item, index) => (
                <article
                  key={item.title}
                  className={activeFocusIndex === index ? 'socure-explainability-row active' : 'socure-explainability-row'}
                >
                  <div className="socure-explainability-rank">{String(index + 1).padStart(2, '0')}</div>
                  <div className="socure-explainability-copy">
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </div>
                  <div className="socure-explainability-signal">
                    <span>{workspace.highlights[index]?.label ?? workspace.connector.primaryDataset}</span>
                    <b>{workspace.highlights[index]?.value ?? workspace.connector.primaryDataset}</b>
                  </div>
                </article>
              ))}
            </div>

            <div className="socure-workflow-strip">
              {activeWorkflows.map((workflow) => (
                <a key={workflow.title} href={workflow.href}>
                  <strong>{workflow.title}</strong>
                  <small>{workflow.detail}</small>
                </a>
              ))}
            </div>
          </section>
        </div>

        <aside id="socure-assistant" className="socure-assistant-panel">
          <div className="socure-section-intro">
            <span className="eyebrow">AI suite</span>
            <h3>Review this case in place</h3>
            <p>Ask from the selected example, then decide whether Product should change a rule, step-up, or queue policy.</p>
          </div>

          {activeCase ? (
            <div className="socure-active-investigation">
              <span className="eyebrow">Selected case</span>
              <strong>
                {activeCase.id} · {caseStatusLabel(activeCase.status)}
              </strong>
              <p>{activeCase.signal}</p>
            </div>
          ) : null}

          <div className="socure-prompt-chip-row" aria-label="Suggested Socure prompts">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.question}
                type="button"
                className="socure-prompt-chip"
                onClick={() => setDraftQuestion(suggestion.question)}
              >
                <strong>{suggestion.label}</strong>
                <span>{suggestion.question}</span>
              </button>
            ))}
          </div>

          {activeCase && activeSignal && activeInspect ? (
            <div className="socure-thread" aria-label="Socure assistant conversation">
              <article className="socure-message socure-message-user">
                <span>Product</span>
                <p>{submittedQuestion}</p>
              </article>
              <article className="socure-message socure-message-assistant">
                <span>DreamFi</span>
                <p>{helperLine(activeCase, workspace, activeInspect.title)}</p>
                <ul>
                  <li>
                    <strong>{activeCase.id}</strong>: {activeCase.detail}
                  </li>
                  <li>
                    <strong>{activeInspect.title}</strong>: {activeInspect.detail}
                  </li>
                  <li>
                    <strong>{activeSignal.label}</strong>: {activeSignal.value}. {activeSignal.detail}
                  </li>
                </ul>
                <p>
                  Recommended review path: <strong>{activeCase.nextStep}</strong>
                </p>
              </article>
            </div>
          ) : null}

          <form
            className="socure-compose"
            onSubmit={(event) => {
              event.preventDefault()
              setSubmittedQuestion(draftQuestion)
            }}
          >
            <label htmlFor="socure-in-place-question">Review the selected case</label>
            <textarea
              id="socure-in-place-question"
              name="q"
              value={draftQuestion}
              onChange={(event) => setDraftQuestion(event.target.value)}
              placeholder="Explain whether this case should stay questionable, stay stepped up, or move to a different path."
            />
            <div className="socure-compose-actions">
              <button type="submit" className="button primary">
                Run explainability
              </button>
              {workspace.workflows[0] ? (
                <a className="button secondary" href={workspace.workflows[0].href}>
                  {workspace.workflows[0].title}
                </a>
              ) : null}
            </div>
          </form>
        </aside>
      </div>
    </section>
  )
}

export default SocureWorkspace

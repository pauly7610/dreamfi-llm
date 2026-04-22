import { useEffect, useMemo, useState } from 'react'

import type { SourceDataPreview } from '../../content/sourceDataPreviews'
import type { ConsoleIntegration } from '../../types/console'

type SourceCopilotPanelProps = {
  source: ConsoleIntegration
  preview: SourceDataPreview
}

const COPILOT_LABEL_BY_SOURCE: Record<string, string> = {
  socure: 'Ask the risk copilot',
  klaviyo: 'Ask the lifecycle copilot',
  jira: 'Ask the delivery copilot',
  metabase: 'Ask the metrics copilot',
  posthog: 'Ask the behavior copilot',
}

function starterQuestion(source: ConsoleIntegration, preview: SourceDataPreview): string {
  return preview.questions[0] ?? `What should Product know from ${source.name}?`
}

type PrioritizedQuestion = {
  detail: string
  focus: string
  label: string
  question: string
  rank: string
}

const PRIORITY_LABELS: Record<string, string[]> = {
  socure: ['Triage', 'Explain', 'Escalate'],
}

function prioritizedQuestions(source: ConsoleIntegration, preview: SourceDataPreview): PrioritizedQuestion[] {
  const labels = PRIORITY_LABELS[source.id] ?? ['Start', 'Compare', 'Summarize']

  return preview.questions.slice(0, 3).map((question, index) => {
    const inspectItem = preview.inspect[index] ?? preview.inspect[0]
    const relatedRow = preview.rows[index] ?? preview.rows[0]

    return {
      detail:
        inspectItem?.detail ??
        relatedRow?.detail ??
        `Keep ${source.name} in scope while DreamFi reviews the connector evidence.`,
      focus: inspectItem?.title ?? relatedRow?.label ?? preview.primaryDataset,
      label: labels[index] ?? labels[labels.length - 1] ?? 'Review',
      question,
      rank: String(index + 1).padStart(2, '0'),
    }
  })
}

function introLine(source: ConsoleIntegration, preview: SourceDataPreview, focusRow?: SourceDataPreview['rows'][number]): string {
  const leadSignal = focusRow ?? preview.rows[0]
  if (!leadSignal) {
    return `I pulled the current ${preview.primaryDataset} slice from ${source.name}.`
  }

  return `I pulled the current ${preview.primaryDataset} slice from ${source.name}. The clearest signal in this review is ${leadSignal.label} at ${leadSignal.value}.`
}

function promptLabel(source: ConsoleIntegration): string {
  return COPILOT_LABEL_BY_SOURCE[source.id] ?? `Ask ${source.name}`
}

function eyebrowLabel(source: ConsoleIntegration): string {
  return source.id === 'socure' ? 'Explainability' : 'Connector copilot'
}

function headingLabel(source: ConsoleIntegration): string {
  return source.id === 'socure' ? 'Review this case in place' : `Ask ${source.name} in place`
}

function primaryActionLabel(source: ConsoleIntegration): string {
  return source.id === 'socure' ? 'Open full investigation' : 'Ask with this connector'
}

function SourceCopilotPanel({ source, preview }: SourceCopilotPanelProps) {
  const prioritized = useMemo(() => prioritizedQuestions(source, preview), [preview, source])
  const fallbackQuestion = starterQuestion(source, preview)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [draftQuestion, setDraftQuestion] = useState(prioritized[0]?.question ?? fallbackQuestion)
  const extraWorkflows = preview.workflows.slice(1, 3)
  const activeQuestion = prioritized[selectedIndex] ?? prioritized[0] ?? null
  const activeRow = preview.rows[selectedIndex] ?? preview.rows[0]

  useEffect(() => {
    setSelectedIndex(0)
    setDraftQuestion(prioritized[0]?.question ?? fallbackQuestion)
  }, [fallbackQuestion, prioritized])

  return (
    <aside className={`source-copilot-panel source-copilot-${source.id} panel`}>
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">{eyebrowLabel(source)}</span>
          <h2>{headingLabel(source)}</h2>
          <p className="section-subtle">
            Keep the connector context visible while you inspect, ask, and generate.
            {source.id === 'socure' ? ' Start from the ranked investigations below before opening the broader workspace.' : null}
          </p>
        </div>
        <span className="subtle-chip">{preview.freshness}</span>
      </div>

      <div className="source-priority-panel">
        <span className="eyebrow">{source.id === 'socure' ? 'Priority investigations' : 'Suggested questions'}</span>
        <div className="source-priority-list">
          {prioritized.map((item, index) => (
            <button
              key={item.question}
              type="button"
              className={selectedIndex === index ? 'source-priority-button active' : 'source-priority-button'}
              onClick={() => {
                setSelectedIndex(index)
                setDraftQuestion(item.question)
              }}
            >
              <span className="source-priority-rank">{item.rank}</span>
              <span className="source-priority-copy">
                <strong>{item.label}</strong>
                <b>{item.question}</b>
                <small>{item.focus}</small>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="source-copilot-thread" aria-label={`${source.name} connector copilot`}>
        <article className="source-chat-bubble source-chat-user">
          <span>Product</span>
          <p>{draftQuestion}</p>
        </article>

        <article className="source-chat-bubble source-chat-assistant">
          <span>DreamFi</span>
          <p>{introLine(source, preview, activeRow)}</p>
          {activeQuestion ? (
            <p className="source-chat-focus">
              <strong>{activeQuestion.label}</strong>: {activeQuestion.focus}. {activeQuestion.detail}
            </p>
          ) : null}
          <ul>
            {preview.rows
              .filter((row) => row.label === activeRow?.label || row.label === preview.rows[0]?.label)
              .slice(0, 2)
              .map((row) => (
              <li key={row.label}>
                <strong>{row.label}</strong>: {row.value}. {row.detail}
              </li>
            ))}
          </ul>
          {activeQuestion ? (
            <p>
              Next best check: <strong>{activeQuestion.focus}</strong>. {activeQuestion.detail}
            </p>
          ) : null}
        </article>
      </div>

      <div className="source-copilot-context">
        <span className="eyebrow">Loaded context</span>
        <div className="source-copilot-chip-row">
          <span className="source-copilot-chip">{preview.primaryDataset}</span>
          {preview.views.slice(0, 2).map((view) => (
            <span key={view} className="source-copilot-chip">
              {view}
            </span>
          ))}
        </div>
      </div>

      <form className="source-copilot-compose" action="/console/knowledge/ask">
        <input type="hidden" name="source" value={source.id} />
        <label htmlFor={`source-copilot-${source.id}`}>{promptLabel(source)}</label>
        <textarea
          id={`source-copilot-${source.id}`}
          name="q"
          value={draftQuestion}
          onChange={(event) => setDraftQuestion(event.target.value)}
        />
        <div className="source-copilot-actions">
          <button type="submit" className="button primary">
            {primaryActionLabel(source)}
          </button>
          {preview.workflows[0] ? (
            <a className="button secondary" href={preview.workflows[0].href}>
              {preview.workflows[0].title}
            </a>
          ) : null}
        </div>
      </form>

      {extraWorkflows.length > 0 ? (
        <div className="source-copilot-workflows">
          {extraWorkflows.map((workflow) => (
            <a key={workflow.title} href={workflow.href}>
              {workflow.title}
            </a>
          ))}
        </div>
      ) : null}
    </aside>
  )
}

export default SourceCopilotPanel

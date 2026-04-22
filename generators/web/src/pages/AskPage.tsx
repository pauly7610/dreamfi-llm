import { useEffect, useMemo, useState } from 'react'

import EvidenceReceipt from '../components/console/EvidenceReceipt'
import { productTopics, starterTopics, topicById } from '../content/productTopics'
import type { ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ProductWorkflowModel } from '../content/productWorkflows'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'
import { buildAskHref, generatorHrefForContext, navigateConsole } from '../utils/consoleRoutes'

type AskPageProps = {
  data: ConsolePayload | null
}

const fallbackQuestion = starterTopics[0]?.question ?? 'What should Product know before the next decision?'

function sourceListForAsk(
  integrations: ConsoleIntegration[],
  topic: ProductTopic | null,
  selectedSourceId: string | null,
): ConsoleIntegration[] {
  if (topic) {
    return topic.sources
      .map((sourceId) => integrations.find((source) => source.id === sourceId))
      .filter((source): source is ConsoleIntegration => Boolean(source))
      .slice(0, 6)
  }

  if (selectedSourceId) {
    const source = integrations.find((item) => item.id === selectedSourceId)
    return source ? [source] : []
  }

  return []
}

function answerPoints(
  topic: ProductTopic | null,
  workflow: ProductWorkflowModel | null,
  selectedSource: ConsoleIntegration | null,
): string[] {
  if (topic && workflow) {
    return [
      `Current step: ${workflow.currentState.phase} -> ${workflow.currentState.step}. Jira currently reads ${workflow.currentState.jiraState}.`,
      `Decision required next: ${workflow.nextDecision}`,
      ...workflow.missing.slice(0, 2).map((item) => `Missing before movement: ${item}`),
      ...topic.signals.slice(0, 2).map((signal) => `${signal.label}: ${signal.value}. ${signal.detail}`),
    ]
  }

  if (topic) {
    return topic.signals.map((signal) => `${signal.label}: ${signal.value}. ${signal.detail}`)
  }

  if (selectedSource) {
    return [
      `${selectedSource.name} is in scope for this answer, so DreamFi should cite the connector before making a claim.`,
      selectedSource.purpose,
      'Use the source detail page to inspect the available data slice before generating a publishable artifact.',
    ]
  }

  return [
    'Start by choosing a topic or connector so DreamFi can keep the answer grounded.',
    'Evidence receipts should show which sources were used and what still needs review.',
    'Once the answer is useful, generate a brief, PRD, or BRD from the same cited context.',
  ]
}

function AskPage({ data }: AskPageProps) {
  const searchParams = typeof window === 'undefined' ? new URLSearchParams() : new URLSearchParams(window.location.search)
  const initialQuery = searchParams.get('q') || fallbackQuestion
  const initialSourceId = searchParams.get('source')
  const initialTopicId = searchParams.get('topic')
  const [draftQuestion, setDraftQuestion] = useState(initialQuery)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(initialTopicId)
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(initialSourceId)
  const integrations = data?.integrations ?? []
  const selectedTopic = topicById(selectedTopicId)
  const selectedWorkflow = workflowByTopicId(selectedTopic?.id ?? null)
  const selectedSource = integrations.find((source) => source.id === selectedSourceId) ?? null
  const receiptSources = sourceListForAsk(integrations, selectedTopic, selectedSourceId)
  const gaps = selectedTopic?.gaps ?? []
  const workflowQuestions = selectedWorkflow?.questionGroups ?? []
  const showReceipt = receiptSources.length > 0 || gaps.length > 0
  const askHref = useMemo(() => {
    const params = new URLSearchParams()
    params.set('q', draftQuestion || fallbackQuestion)
    if (selectedTopic) {
      params.set('topic', selectedTopic.id)
    }
    if (selectedSourceId) {
      params.set('source', selectedSourceId)
    }
    return `/console/knowledge/ask?${params.toString()}`
  }, [draftQuestion, selectedSourceId, selectedTopic])
  const generateHref = generatorHrefForContext({
    topicId: selectedTopic?.id,
    sourceId: selectedSourceId,
    query: draftQuestion,
  })

  useEffect(() => {
    setDraftQuestion(initialQuery)
    setSelectedTopicId(initialTopicId)
    setSelectedSourceId(initialSourceId)
  }, [initialQuery, initialSourceId, initialTopicId])

  function syncAskUrl(nextTopicId: string | null, nextQuestion: string, nextSourceId: string | null) {
    const params = new URLSearchParams()
    params.set('q', nextQuestion)
    if (nextTopicId) {
      params.set('topic', nextTopicId)
    }
    if (nextSourceId) {
      params.set('source', nextSourceId)
    }
    navigateConsole(`/console/knowledge/ask?${params.toString()}`, true)
  }

  return (
    <div className="page-grid ask-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <a href="/console">Product Source Room</a>
        <span aria-hidden="true">/</span>
        <span>Ask</span>
      </nav>

      <section className="ask-hero panel">
        <div>
          <span className="eyebrow">Ask DreamFi</span>
          <h2>Ask the company what it already knows.</h2>
          <p>
            Start with a Product question. DreamFi should gather evidence from the right systems, show its receipts, and
            help you turn the answer into real product work.
          </p>
        </div>
        <form
          className="ask-box"
          action="/console/knowledge/ask"
          onSubmit={(event) => {
            event.preventDefault()
            navigateConsole(askHref)
          }}
        >
          <label htmlFor="ask-query">Question</label>
          <textarea
            id="ask-query"
            name="q"
            value={draftQuestion}
            onChange={(event) => {
              const nextQuestion = event.target.value
              setDraftQuestion(nextQuestion)
              syncAskUrl(selectedTopic?.id ?? null, nextQuestion, selectedSourceId)
            }}
          />
          <div className="ask-box-actions">
            {selectedSourceId ? <input type="hidden" name="source" value={selectedSourceId} /> : null}
            {selectedTopic ? <input type="hidden" name="topic" value={selectedTopic.id} /> : null}
            <button type="submit" className="button primary">Ask with receipts</button>
            <a className="button secondary" href="/console/topics">Choose a topic</a>
          </div>
        </form>
      </section>

      <section className="ask-scope-panel panel">
        <div>
          <span className="eyebrow">Scope</span>
          <h3>{selectedTopic ? selectedTopic.title : selectedSource ? selectedSource.name : 'All product sources'}</h3>
          <p>
            {selectedTopic
              ? selectedTopic.summary
              : selectedSource
                ? selectedSource.purpose
                : 'Choose a source or topic when you want a tighter answer with clearer citations.'}
          </p>
        </div>
        <div className="scope-chip-list">
          {productTopics.map((topic) => (
            <button
              key={topic.id}
              type="button"
              className={selectedTopic?.id === topic.id ? 'active' : ''}
              onClick={() => {
                setSelectedTopicId(topic.id)
                setSelectedSourceId(null)
                setDraftQuestion(topic.question)
                syncAskUrl(topic.id, topic.question, null)
              }}
            >
              {topic.title}
            </button>
          ))}
        </div>
      </section>

      {selectedWorkflow ? (
        <section className="ask-workflow-panel panel">
          <div className="section-heading inline">
            <div>
              <span className="eyebrow">Decision support</span>
              <h2>Keep this answer anchored to process state.</h2>
            </div>
            <a className="button secondary" href={`/console/topics/${selectedWorkflow.topicId}`}>Open topic room</a>
          </div>
          <div className="ask-workflow-strip">
            <div className="ask-workflow-card">
              <span>Current step</span>
              <strong>{selectedWorkflow.currentState.step}</strong>
              <small>{selectedWorkflow.currentState.phase}</small>
            </div>
            <div className="ask-workflow-card">
              <span>Next decision</span>
              <strong>{selectedWorkflow.nextDecision}</strong>
              <small>{selectedWorkflow.recommendation}</small>
            </div>
            <div className="ask-workflow-card">
              <span>Missing</span>
              <strong>{selectedWorkflow.missing[0]}</strong>
              <small>
                {selectedWorkflow.missing.length > 1
                  ? `${selectedWorkflow.missing.length - 1} more workflow gaps still open.`
                  : 'The main workflow gap is shown here.'}
              </small>
            </div>
          </div>
        </section>
      ) : null}

      <section className={`ask-answer-grid${showReceipt ? '' : ' no-receipt'}`}>
        <article className="ask-answer-panel panel">
          <span className="eyebrow">Evidence-backed starter answer</span>
          <h2>{draftQuestion}</h2>
          <div className="answer-points">
            {answerPoints(selectedTopic, selectedWorkflow, selectedSource).map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
          <div className="answer-actions">
            <a className="button primary" href={generateHref}>Generate from this</a>
            <a className="button secondary" href="/console/integrations">Inspect sources</a>
          </div>
        </article>
        {showReceipt ? <EvidenceReceipt sources={receiptSources} gaps={gaps} /> : null}
      </section>

      <section className="starter-question-panel panel">
        <div className="section-heading inline">
          <div>
            <span className="eyebrow">Good starts</span>
            <h2>{selectedWorkflow ? 'Decision questions this room should answer' : 'Questions that map cleanly to evidence'}</h2>
          </div>
        </div>
        {selectedWorkflow ? (
          <div className="workflow-question-groups ask-question-groups">
            {workflowQuestions.map((group) => (
              <div key={group.title} className="workflow-question-group">
                <span>{group.title}</span>
                <div className="prompt-chips">
                  {group.questions.map((question) => (
                    <a key={question} href={buildAskHref(selectedWorkflow.topicId, question)}>
                      {question}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="prompt-chips">
            {starterTopics.map((topic) => (
              <a key={topic.id} href={buildAskHref(topic.id, topic.question)}>
                {topic.question}
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default AskPage

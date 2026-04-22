import EvidenceReceipt from '../components/console/EvidenceReceipt'
import { productTopics, starterTopics, topicById } from '../content/productTopics'
import type { ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ProductWorkflowModel } from '../content/productWorkflows'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'

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

  return integrations.filter((source) => ['metabase', 'posthog', 'klaviyo', 'jira'].includes(source.id))
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
      `Missing before movement: ${workflow.missing.slice(0, 2).join('; ')}`,
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
  const query = searchParams.get('q') || fallbackQuestion
  const selectedSourceId = searchParams.get('source')
  const selectedTopic = topicById(searchParams.get('topic'))
  const selectedWorkflow = workflowByTopicId(selectedTopic?.id ?? null)
  const integrations = data?.integrations ?? []
  const selectedSource = integrations.find((source) => source.id === selectedSourceId) ?? null
  const receiptSources = sourceListForAsk(integrations, selectedTopic, selectedSourceId)
  const gaps = selectedTopic?.gaps ?? []
  const workflowQuestions = selectedWorkflow?.questionGroups ?? []

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
        <form className="ask-box" action="/console/knowledge/ask">
          <label htmlFor="ask-query">Question</label>
          <textarea id="ask-query" name="q" defaultValue={query} />
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
            <a
              key={topic.id}
              className={selectedTopic?.id === topic.id ? 'active' : ''}
              href={`/console/knowledge/ask?topic=${topic.id}&q=${encodeURIComponent(topic.question)}`}
            >
              {topic.title}
            </a>
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

      <section className="ask-answer-grid">
        <article className="ask-answer-panel panel">
          <span className="eyebrow">Evidence-backed starter answer</span>
          <h2>{query}</h2>
          <div className="answer-points">
            {answerPoints(selectedTopic, selectedWorkflow, selectedSource).map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
          <div className="answer-actions">
            <a className="button primary" href="/console/generate/weekly-brief">Generate brief from this</a>
            <a className="button secondary" href="/console/integrations">Inspect sources</a>
          </div>
        </article>
        <EvidenceReceipt sources={receiptSources} gaps={gaps} />
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
                    <a key={question} href={`/console/knowledge/ask?topic=${selectedWorkflow.topicId}&q=${encodeURIComponent(question)}`}>
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
              <a key={topic.id} href={`/console/knowledge/ask?topic=${topic.id}&q=${encodeURIComponent(topic.question)}`}>
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

import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import ContextContinuationPanel from '../components/console/ContextContinuationPanel'
import EvidenceReceipt from '../components/console/EvidenceReceipt'
import TrustActionRail from '../components/console/TrustActionRail'
import { productTopics, starterTopics, topicById } from '../content/productTopics'
import type { ProductTopic } from '../content/productTopics'
import { workflowByTopicId } from '../content/productWorkflows'
import type { ProductWorkflowModel } from '../content/productWorkflows'
import type { ConsoleIntegration, ConsolePayload } from '../types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from '../utils/consoleRoutes'
import {
  recommendedGeneratorSlugForContext,
  recommendedGeneratorTitleForContext,
} from '../utils/generatorRecommendations'

type AskPageProps = {
  data: ConsolePayload | null
}

type AskArtifactOption = {
  href: string
  label: string
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

function artifactOptionsForContext(
  topic: ProductTopic | null,
  source: ConsoleIntegration | null,
  buildGenerateHref: (slug: string, options?: { question?: string; sourceId?: string | null; topicId?: string | null }) => string,
  query: string,
): AskArtifactOption[] {
  const labels = topic?.artifacts ?? source?.used_for.map((slug) => generatorTitleFromSlug(slug)) ?? []
  const topicId = topic?.id ?? null
  const sourceId = source?.id ?? null

  return labels
    .map((label) => {
      const slug = generatorSlugFromIdentifier(label)
      return {
        href: buildGenerateHref(slug, {
          question: query,
          topicId,
          sourceId,
        }),
        label: generatorTitleFromSlug(slug),
      }
    })
    .filter((option, index, allOptions) => allOptions.findIndex((candidate) => candidate.href === option.href) === index)
    .slice(0, 3)
}

function AskPage({ data }: AskPageProps) {
  const { buildAskHref, buildGenerateHref } = useConsoleWorkspace()
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
  const recommendedGeneratorSlug = recommendedGeneratorSlugForContext({
    question: query,
    source: selectedSource,
    topicId: selectedTopic?.id ?? null,
  })
  const recommendedGeneratorTitle = recommendedGeneratorTitleForContext({
    question: query,
    source: selectedSource,
    topicId: selectedTopic?.id ?? null,
  })
  const generateHref = buildGenerateHref(recommendedGeneratorSlug, {
    question: query,
    topicId: selectedTopic?.id ?? null,
    sourceId: selectedSourceId,
  })
  const artifactOptions = artifactOptionsForContext(selectedTopic, selectedSource, buildGenerateHref, query)
  const degradedSourceCount = receiptSources.filter((source) => source.status === 'degraded').length
  const trustHeadline = gaps.length > 0 || degradedSourceCount > 0 ? 'Needs review before publish' : 'Ready to draft from current context'
  const trustDetail =
    degradedSourceCount > 0
      ? `${degradedSourceCount} cited source still needs verification before publish.`
      : gaps[0] ?? 'No blocking evidence gaps are called out in this current slice.'
  const reviewSource =
    receiptSources.find((source) => source.status === 'degraded') ??
    receiptSources.find((source) => source.id !== selectedSource?.id) ??
    receiptSources[0] ??
    null
  const continuityCards = [
    reviewSource
      ? {
          label: 'Inspect next',
          value: reviewSource.name,
          detail:
            reviewSource.status === 'degraded'
              ? 'This source is the clearest trust swing in the current thread, so inspect it before you publish from the answer.'
              : 'This connector is one click away when you need a deeper read than the inline citations provide.',
          href: reviewSource.href,
          hrefLabel: 'Open source',
        }
      : null,
    {
      label: 'Generate next',
      value: recommendedGeneratorTitle,
      detail: 'The strongest default move should be to generate from the current question, not to restart context in a separate workflow.',
      href: generateHref,
      hrefLabel: `Generate ${recommendedGeneratorTitle}`,
    },
    selectedWorkflow
      ? {
          label: 'Decision state',
          value: selectedWorkflow.nextDecision,
          detail: `Current workflow step: ${selectedWorkflow.currentState.step}. Keep the answer pinned to this decision while the thread evolves.`,
          href: `/console/topics/${selectedWorkflow.topicId}`,
          hrefLabel: 'Open topic room',
        }
      : selectedTopic
        ? {
            label: 'Room continuity',
            value: selectedTopic.title,
            detail: 'This thread is already anchored to a repeatable product room, so DreamFi should keep that room alive across ask and generate.',
            href: `/console/topics/${selectedTopic.id}`,
            hrefLabel: 'Open topic room',
          }
        : null,
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))
  const trustActions = [
    reviewSource
      ? {
          title: `Inspect ${reviewSource.name} inline`,
          detail:
            reviewSource.status === 'degraded'
              ? 'A cited source still needs attention, so the trust rail should push you straight into that connector.'
              : 'The next best source is available without breaking the current question thread.',
          href: buildAskHref({
            question: query,
            topicId: selectedTopic?.id ?? null,
            sourceId: reviewSource.id,
          }),
          hrefLabel: 'Ask with this source',
          tone: (reviewSource.status === 'degraded' ? 'warning' : 'info') as 'warning' | 'info',
        }
      : null,
    gaps.length > 0
      ? {
          title: 'Clear the known trust gap',
          detail: gaps[0],
          href: '/console/trust',
          hrefLabel: 'Open trust rails',
          tone: 'warning' as const,
        }
      : null,
    {
      title: `Move this answer into ${recommendedGeneratorTitle}`,
      detail: 'Once the answer is useful, the next action should already know which artifact fits the current room best.',
      href: generateHref,
      hrefLabel: `Generate ${recommendedGeneratorTitle}`,
      tone: 'ready' as const,
    },
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))

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
            This is a working thread, not a blank chat. DreamFi should keep the room, sources, citations, and trust
            posture alive while you move from question to artifact.
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

      <section className="ask-thread-panel panel">
        <div>
          <span className="eyebrow">Current thread</span>
          <h2>This thread already knows where to look.</h2>
          <p>
            DreamFi should carry the active room, sources, and trust posture into the answer and the next generated
            artifact instead of making you restate the same context.
          </p>
        </div>
        <div className="ask-thread-grid">
          <article className="ask-thread-card">
            <span>Working room</span>
            <strong>{selectedTopic ? selectedTopic.title : selectedSource ? selectedSource.name : 'Cross-product ask'}</strong>
            <small>
              {selectedTopic
                ? selectedTopic.summary
                : selectedSource
                  ? selectedSource.purpose
                  : 'This ask can still tighten into a topic or source once the question settles.'}
            </small>
          </article>
          <article className="ask-thread-card">
            <span>Citations in scope</span>
            <strong>{receiptSources.length} sources</strong>
            <small>{receiptSources.map((source) => source.name).join(', ')}</small>
          </article>
          <article className="ask-thread-card">
            <span>Trust posture</span>
            <strong>{trustHeadline}</strong>
            <small>{trustDetail}</small>
          </article>
        </div>
        <div className="ask-thread-actions">
          <a className="button primary" href={generateHref}>Generate {recommendedGeneratorTitle}</a>
          <a className="button secondary" href="/console/trust">Open trust rails</a>
        </div>
      </section>

      <TrustActionRail
        title="Trust should tell you what to do next"
        description="These actions keep the answer, receipts, and trust work in the same flow instead of making trust a separate cleanup step."
        actions={trustActions}
      />

      <ContextContinuationPanel
        title="Keep the next move source-aware and effortless"
        description="DreamFi should make the next connector, artifact, and room obvious from the current thread, even when the source slice is still sparse."
        cards={continuityCards}
        actions={[
          {
            label: `Generate ${recommendedGeneratorTitle}`,
            href: generateHref,
            kind: 'primary',
          },
          {
            label: selectedTopic ? 'Open topic room' : 'Inspect sources',
            href: selectedTopic ? `/console/topics/${selectedTopic.id}` : '/console/integrations',
          },
        ]}
      />

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
          <div className="answer-citation-strip" aria-label="Inline citations">
            {receiptSources.map((source) => (
              <a key={source.id} className="answer-citation-chip" href={source.href}>
                <strong>{source.name}</strong>
                <small>{source.status === 'degraded' ? 'Needs review' : 'Ready to cite'}</small>
              </a>
            ))}
          </div>
          <div className="answer-points">
            {answerPoints(selectedTopic, selectedWorkflow, selectedSource).map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
          <div className="answer-trust-bar">
            <div>
              <span className="eyebrow">Trust guidance</span>
              <strong>{trustHeadline}</strong>
              <p>{trustDetail}</p>
            </div>
            <div className="answer-trust-actions">
              {artifactOptions.map((option) => (
                <a key={option.href} className="button secondary" href={option.href}>
                  {option.label}
                </a>
              ))}
            </div>
          </div>
          <div className="answer-actions">
            <a className="button primary" href={generateHref}>Generate {recommendedGeneratorTitle}</a>
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

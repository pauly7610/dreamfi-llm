import { useEffect, useMemo, useState } from 'react'

type ConsoleSummary = {
  skill_count: number
  active_prompt_count: number
  average_latest_score: number | null
  average_confidence: number | null
  average_export_readiness: number | null
  publish_success_rate: number | null
  hard_gate_pass_rate: number | null
  blocked_artifact_count: number
  publish_ready_count: number
  published_artifact_count: number
  needs_review_count: number
}

type RoundSummary = {
  round_id: string
  prompt_version_id: string
  score: number
  previous_score: number | null
  improvement: number | null
  completed_at: string | null
  artifacts_path: string
}

type SkillCard = {
  skill_id: string
  display_name: string
  description: string
  criteria_count: number
  active_prompt_version: number | null
  latest_round: RoundSummary | null
  recent_rounds: RoundSummary[]
}

type PublishActivity = {
  publish_id: string
  skill_id: string
  destination: string
  destination_ref: string | null
  decision: string
  reason: string | null
  created_at: string
}

type ArtifactRecord = {
  output_id: string
  skill_id: string | null
  skill_display_name: string | null
  round_id: string
  test_input_label: string
  attempt: number
  pass_fail: string
  confidence: number | null
  export_readiness: number | null
  created_at: string
  status: 'blocked' | 'publish_ready' | 'published' | 'needs_review'
  artifacts_path: string | null
  latest_publish: PublishActivity | null
}

type ConsolePayload = {
  headline: string
  summary: ConsoleSummary
  skills: SkillCard[]
  artifact_queue: ArtifactRecord[]
  publish_activity: PublishActivity[]
}

type ModuleCard = {
  title: string
  subtitle: string
  description: string
  operatorOutcome: string
}

const modules: ModuleCard[] = [
  {
    title: 'Product Knowledge Hub',
    subtitle: 'Source-of-truth retrieval',
    description: 'Answer product questions with citations, freshness, reusable context, and confidence that can be inspected later.',
    operatorOutcome: 'Grounded answers with reusable lineage.'
  },
  {
    title: 'Document Generators',
    subtitle: 'Governed artifact generation',
    description: 'Generate discovery docs, PRDs, risk docs, and adjacent product artifacts against explicit contracts and eval criteria.',
    operatorOutcome: 'Draft faster without losing control of quality.'
  },
  {
    title: 'Planning Trust',
    subtitle: 'Planning signal quality',
    description: 'Turn Jira and Dragonboat inputs into trusted planning briefs with explicit ambiguity, missing-data, and hygiene flags.',
    operatorOutcome: 'Know what the plan says and where the plan is weak.'
  },
  {
    title: 'Metric Trust',
    subtitle: 'Confidence-scored reporting',
    description: 'Turn Metabase, PostHog, and GA inputs into discrepancy-aware narratives and trusted performance reporting.',
    operatorOutcome: 'Publish metrics only when definitions and numbers hold together.'
  },
  {
    title: 'UI Project Support',
    subtitle: 'Structured intake and validation',
    description: 'Support UI and product work with structured intake, artifact validation, export readiness, and governed publishability.',
    operatorOutcome: 'Move interface work through a trusted operating workflow.'
  }
]

const trustControls = [
  'Grounding against source data and retrieval evidence',
  'Evaluation against explicit hard-gate criteria',
  'Trust and confidence scoring with decomposed signals',
  'Reconstruction of prompts, tool traces, and lineage',
  'Publish gating with policy checks and receipts',
  'Operator visibility with human review when needed'
]

const auditSurface = [
  'Prompt version, model version, and retrieval snapshot',
  'Claims, citations, and source-of-truth lineage',
  'Criteria-by-criteria eval outcomes',
  'Critic verdicts, revisions, and tool trace',
  'Approval record, publish receipt, and rollback handle'
]

const workflowStages = [
  'Ground source data',
  'Generate structured artifact',
  'Evaluate against locked checks',
  'Score trust and readiness',
  'Reconstruct and review',
  'Publish only if policy clears'
]

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return value.toFixed(3)
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return `${Math.round(value * 100)}%`
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'Pending'
  }
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  }).format(new Date(value))
}

function formatStatus(status: ArtifactRecord['status']): string {
  if (status === 'publish_ready') {
    return 'Publish ready'
  }
  if (status === 'needs_review') {
    return 'Needs review'
  }
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function TrustDashboard() {
  const [data, setData] = useState<ConsolePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadConsoleData() {
      try {
        setLoading(true)
        const response = await fetch('/api/console', { signal: controller.signal })
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`)
        }
        const payload = (await response.json()) as ConsolePayload
        setData(payload)
        setError(null)
      } catch (loadError) {
        if (controller.signal.aborted) {
          return
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load console data')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadConsoleData()

    return () => {
      controller.abort()
    }
  }, [])

  const topSkill = useMemo(() => {
    if (!data) {
      return null
    }
    return [...data.skills]
      .filter((skill) => skill.latest_round !== null)
      .sort((left, right) => (right.latest_round?.score ?? 0) - (left.latest_round?.score ?? 0))[0] ?? null
  }, [data])

  const priorityCards = useMemo(() => {
    const summary = data?.summary
    return [
      {
        title: 'Blocked by trust gates',
        value: summary?.blocked_artifact_count ?? 0,
        tone: 'blocked',
        body: 'Artifacts failing hard gates or otherwise unsafe to move forward.'
      },
      {
        title: 'Ready to publish',
        value: summary?.publish_ready_count ?? 0,
        tone: 'ready',
        body: 'Artifacts that appear to clear readiness policy and are candidates for release.'
      },
      {
        title: 'Need operator review',
        value: summary?.needs_review_count ?? 0,
        tone: 'review',
        body: 'Artifacts that passed enough checks to continue but still need a human or additional signal.'
      }
    ]
  }, [data])

  const connectionLabel = error
    ? 'API unavailable — showing dashboard shell'
    : loading
      ? 'Loading trust data'
      : 'Connected to live trust data'

  return (
    <div className="trust-app-shell">
      <header className="shell-header">
        <div className="brand-block">
          <span className="brand-chip">DreamFi</span>
          <div>
            <h1>Trust operations dashboard</h1>
            <p>{data?.headline ?? 'Trust, measured.'}</p>
          </div>
        </div>
        <nav className="shell-nav">
          <a href="#overview">Overview</a>
          <a href="#artifacts">Artifacts</a>
          <a href="#modules">Modules</a>
          <a href="#skills">Skills</a>
          <a href="#publish">Publish</a>
        </nav>
      </header>

      <main className="trust-page">
        <section id="overview" className="hero-panel panel">
          <div className="hero-copy">
            <span className="eyebrow">Internal trust engine for product work</span>
            <h2>Turn product context into trust-scored, reconstructible, publishable artifacts.</h2>
            <p>
              DreamFi governs product knowledge, planning, metrics, document generation, and UI work by grounding outputs,
              evaluating them explicitly, scoring trust, and gating publication behind policy.
            </p>
            <div className="status-inline">
              <span className={`status-dot ${error ? 'offline' : 'online'}`} />
              <span>{connectionLabel}</span>
            </div>
            <ul className="control-list">
              {trustControls.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="hero-side">
            <article className="spotlight-card">
              <span className="spotlight-label">Top skill right now</span>
              <h3>{topSkill?.display_name ?? 'No eval rounds yet'}</h3>
              <p className="spotlight-score">{formatScore(topSkill?.latest_round?.score)}</p>
              <p className="muted">
                {topSkill?.latest_round
                  ? `Latest round completed ${formatDate(topSkill.latest_round.completed_at)}`
                  : 'Run an eval round to populate live skill health.'}
              </p>
            </article>
            <article className="snapshot-card">
              <span className="spotlight-label">Operator snapshot</span>
              <dl>
                <div>
                  <dt>Active prompts</dt>
                  <dd>{data?.summary.active_prompt_count ?? '—'}</dd>
                </div>
                <div>
                  <dt>Artifacts published</dt>
                  <dd>{data?.summary.published_artifact_count ?? '—'}</dd>
                </div>
                <div>
                  <dt>Hard gate pass rate</dt>
                  <dd>{formatPercent(data?.summary.hard_gate_pass_rate)}</dd>
                </div>
              </dl>
            </article>
          </div>
        </section>

        <section className="overview-grid">
          <article className="metric-card panel alert">
            <span className="metric-label">Blocked artifacts</span>
            <strong>{data?.summary.blocked_artifact_count ?? '—'}</strong>
            <p>Needs intervention before the artifact can move forward.</p>
          </article>
          <article className="metric-card panel success">
            <span className="metric-label">Publish ready</span>
            <strong>{data?.summary.publish_ready_count ?? '—'}</strong>
            <p>Artifacts that appear safe to publish if operator intent is present.</p>
          </article>
          <article className="metric-card panel">
            <span className="metric-label">Hard gate pass rate</span>
            <strong>{formatPercent(data?.summary.hard_gate_pass_rate)}</strong>
            <p>Recent artifact pass rate across the latest output sample.</p>
          </article>
          <article className="metric-card panel">
            <span className="metric-label">Average export readiness</span>
            <strong>{formatScore(data?.summary.average_export_readiness)}</strong>
            <p>Composite publishability signal across recent outputs.</p>
          </article>
        </section>

        <section className="workspace-grid">
          <article id="artifacts" className="artifact-panel panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Artifact queue</span>
                <h3>What operators should inspect next</h3>
              </div>
              <span className="subtle-chip">Latest 12 outputs</span>
            </div>
            <div className="artifact-list">
              {data?.artifact_queue.length ? (
                data.artifact_queue.map((artifact) => (
                  <article key={artifact.output_id} className="artifact-row">
                    <div className="artifact-main">
                      <div className="artifact-heading">
                        <div>
                          <strong>{artifact.skill_display_name ?? artifact.skill_id ?? 'Unknown skill'}</strong>
                          <p>{artifact.test_input_label}</p>
                        </div>
                        <span className={`status-badge ${artifact.status}`}>{formatStatus(artifact.status)}</span>
                      </div>
                      <dl className="artifact-metrics">
                        <div>
                          <dt>Hard gate</dt>
                          <dd>{artifact.pass_fail}</dd>
                        </div>
                        <div>
                          <dt>Confidence</dt>
                          <dd>{formatScore(artifact.confidence)}</dd>
                        </div>
                        <div>
                          <dt>Readiness</dt>
                          <dd>{formatScore(artifact.export_readiness)}</dd>
                        </div>
                        <div>
                          <dt>Attempt</dt>
                          <dd>{artifact.attempt}</dd>
                        </div>
                      </dl>
                    </div>
                    <div className="artifact-meta">
                      <p>Created {formatDate(artifact.created_at)}</p>
                      <p>Round {artifact.round_id}</p>
                      <p>{artifact.artifacts_path ?? 'Artifacts path unavailable'}</p>
                      <p>
                        {artifact.latest_publish
                          ? `Latest publish: ${artifact.latest_publish.decision} to ${artifact.latest_publish.destination}`
                          : 'No publish receipt yet'}
                      </p>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-state">
                  <h4>No artifacts yet</h4>
                  <p>Run an eval round or generate outputs to populate the trust queue.</p>
                </div>
              )}
            </div>
          </article>

          <aside className="sidebar-stack">
            <article className="priority-panel panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">Operator priorities</span>
                  <h3>Trust work that needs action</h3>
                </div>
              </div>
              <div className="priority-grid">
                {priorityCards.map((item) => (
                  <article key={item.title} className={`priority-card ${item.tone}`}>
                    <strong>{item.value}</strong>
                    <h4>{item.title}</h4>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </article>

            <article id="modules" className="module-panel panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">Operating modules</span>
                  <h3>The five outcomes DreamFi is built around</h3>
                </div>
              </div>
              <div className="module-grid">
                {modules.map((module) => (
                  <article key={module.title} className="module-card">
                    <span className="module-subtitle">{module.subtitle}</span>
                    <h4>{module.title}</h4>
                    <p>{module.description}</p>
                    <small>{module.operatorOutcome}</small>
                  </article>
                ))}
              </div>
            </article>
          </aside>
        </section>

        <section className="detail-grid">
          <article id="skills" className="skills-panel panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Skill health</span>
                <h3>How governed generation is performing</h3>
              </div>
            </div>
            <div className="skills-grid">
              {data?.skills.length ? (
                data.skills.map((skill) => (
                  <article key={skill.skill_id} className="skill-card">
                    <div className="skill-title-row">
                      <div>
                        <h4>{skill.display_name}</h4>
                        <p>{skill.skill_id}</p>
                      </div>
                      <span className="subtle-chip">v{skill.active_prompt_version ?? '—'}</span>
                    </div>
                    <p className="skill-description">{skill.description}</p>
                    <dl className="skill-stats">
                      <div>
                        <dt>Criteria</dt>
                        <dd>{skill.criteria_count}</dd>
                      </div>
                      <div>
                        <dt>Latest score</dt>
                        <dd>{formatScore(skill.latest_round?.score)}</dd>
                      </div>
                      <div>
                        <dt>Improvement</dt>
                        <dd>{formatScore(skill.latest_round?.improvement)}</dd>
                      </div>
                      <div>
                        <dt>Completed</dt>
                        <dd>{formatDate(skill.latest_round?.completed_at ?? null)}</dd>
                      </div>
                    </dl>
                    <div className="history-row">
                      {skill.recent_rounds.length ? (
                        skill.recent_rounds.map((round) => (
                          <span key={round.round_id} className="history-chip">
                            {formatScore(round.score)}
                          </span>
                        ))
                      ) : (
                        <span className="muted">No rounds yet</span>
                      )}
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-state">
                  <h4>No skill data yet</h4>
                  <p>Seed the registry and run an eval round to start measuring skill trust.</p>
                </div>
              )}
            </div>
          </article>

          <article className="audit-panel panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Audit and reconstruction</span>
                <h3>What every trusted artifact should expose</h3>
              </div>
            </div>
            <ul className="audit-list">
              {auditSurface.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="workflow-strip">
              {workflowStages.map((item) => (
                <span key={item} className="workflow-chip">{item}</span>
              ))}
            </div>
          </article>
        </section>

        <section className="detail-grid">
          <article id="publish" className="publish-panel panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Publish receipts</span>
                <h3>Recent policy outcomes and receipts</h3>
              </div>
            </div>
            <div className="publish-list">
              {data?.publish_activity.length ? (
                data.publish_activity.map((activity) => (
                  <article key={activity.publish_id} className="publish-row">
                    <div>
                      <strong>{activity.skill_id}</strong>
                      <p>
                        {activity.destination}
                        {activity.destination_ref ? ` · ${activity.destination_ref}` : ''}
                      </p>
                    </div>
                    <div className="publish-row-meta">
                      <span className={`status-badge ${activity.decision === 'published' ? 'published' : 'blocked'}`}>
                        {activity.decision}
                      </span>
                      <time>{formatDate(activity.created_at)}</time>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-state compact">
                  <h4>No publish receipts yet</h4>
                  <p>Receipts appear here once outputs clear trust policy and move to a destination.</p>
                </div>
              )}
            </div>
          </article>

          <article className="thesis-panel panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Product thesis</span>
                <h3>What is on-thesis for DreamFi</h3>
              </div>
            </div>
            <div className="thesis-grid">
              <div>
                <span className="metric-label">Optimize for</span>
                <ul className="thesis-list">
                  <li>Better grounding</li>
                  <li>Better evaluation</li>
                  <li>Better trust visibility</li>
                  <li>Better reconstruction</li>
                  <li>Better publish safety</li>
                  <li>Better PM/operator workflow</li>
                </ul>
              </div>
              <div>
                <span className="metric-label">Current signals</span>
                <dl className="snapshot-stats">
                  <div>
                    <dt>Skills</dt>
                    <dd>{data?.summary.skill_count ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Avg confidence</dt>
                    <dd>{formatScore(data?.summary.average_confidence)}</dd>
                  </div>
                  <div>
                    <dt>Publish success</dt>
                    <dd>{formatPercent(data?.summary.publish_success_rate)}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </article>
        </section>
      </main>
    </div>
  )
}

export default TrustDashboard

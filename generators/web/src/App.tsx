import { useEffect, useMemo, useState } from 'react'

type ConsoleSummary = {
  skill_count: number
  active_prompt_count: number
  average_latest_score: number | null
  average_confidence: number | null
  average_export_readiness: number | null
  publish_success_rate: number | null
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

type ConsolePayload = {
  summary: ConsoleSummary
  skills: SkillCard[]
  publish_activity: PublishActivity[]
}

type DesignCard = {
  title: string
  body: string
}

const principles: DesignCard[] = [
  {
    title: 'Internal by design',
    body: 'This workspace exists for DreamFi’s product organization, not as an external customer-facing product.'
  },
  {
    title: 'Fragmented systems become one investigation surface',
    body: 'The platform joins product analytics, financial outcomes, fraud decisions, workflow state, and planning context in one place.'
  },
  {
    title: 'Grounding before publishing',
    body: 'Outputs must be inspectable, reconstructible, and safe before they are promoted as product artifacts.'
  },
  {
    title: 'Trust-scored operations',
    body: 'Product questions and generated deliverables carry freshness, discrepancy awareness, and confidence signals.'
  },
  {
    title: 'Governed artifact generation',
    body: 'Discovery docs, PRDs, briefs, and risk documentation should be structured, validated, and versioned.'
  },
  {
    title: 'Decision speed with traceability',
    body: 'The product team should move faster without losing the ability to explain why a decision was made.'
  }
]

const trustPillars = [
  {
    title: 'Product knowledge hub',
    phase: '01',
    status: 'Active',
    body: 'Ask cross-system product questions and get grounded answers with citations, freshness, discrepancy flags, and reusable context.'
  },
  {
    title: 'Governed document generation',
    phase: '02',
    status: 'Active',
    body: 'Produce structured discovery docs, technical and business PRDs, and risk artifacts that are validated and reconstructible.'
  },
  {
    title: 'Planning trust',
    phase: '03',
    status: 'In progress',
    body: 'Turn Jira and Dragonboat context into trusted briefs, roadmap visibility, and explicit hygiene and ambiguity flags.'
  },
  {
    title: 'Metric trust',
    phase: '04',
    status: 'In progress',
    body: 'Interpret Metabase, PostHog, and GA with source-aware trust, discrepancy visibility, and defensible narratives.'
  },
  {
    title: 'UI project support',
    phase: '05',
    status: 'In progress',
    body: 'Run governed design and execution support workflows with structured intake, validation, lineage, and publish safety.'
  }
]

const architectureSteps = [
  {
    step: '01',
    title: 'Request + tenancy',
    body: 'Workspace-scoped requests enter FastAPI, set request context, and enforce tenancy before anything else happens.'
  },
  {
    step: '02',
    title: 'Retrieval via Onyx',
    body: 'DreamFi queries Onyx for grounded context, with retrieval constrained by workspace and policy.'
  },
  {
    step: '03',
    title: 'Generation + critic loop',
    body: 'The model router creates structured output, calls bounded tools, and revises only when the critic says it should.'
  },
  {
    step: '04',
    title: 'Deterministic evaluation',
    body: 'Locked eval runners judge outputs as code, producing pass/fail gates and criteria matrices you can inspect.'
  },
  {
    step: '05',
    title: 'Grounding + confidence',
    body: 'Claim lineage, metric validity, freshness, and hard-gate outcomes become measurable trust signals.'
  },
  {
    step: '06',
    title: 'Persist + publish with receipt',
    body: 'Outputs, tool traces, approvals, destination receipts, and rollback handles are stored before anything ships.'
  }
]

const auditSurface = [
  'Exact prompt version, model identifier, and retrieval query',
  'Retrieved Onyx chunks in ranked order',
  'Tool calls with arguments and outputs',
  'Critic verdicts and revision history',
  'Eval criteria mapped to triggered output lines',
  'Reviewer signature, destination receipt, and rollback handle'
]

const receiptChecklist = [
  'Hard-gate verdict',
  'Export-readiness score and breakdown',
  'Claims and sources',
  'Tool trace and model lineage',
  'Approval record',
  'Destination receipt and rollback handle'
]

const useCases = [
  {
    title: 'KYC drop triage',
    body: 'Investigate whether conversion changes came from UX friction, fraud-rule shifts, or recent deployment changes.'
  },
  {
    title: 'Activation and funding outcomes',
    body: 'Connect onboarding friction steps to downstream activation, funding, and payment outcomes so root causes are clear.'
  },
  {
    title: 'Planning and usage drift',
    body: 'Compare what was shipped and planned against observed behavior to find roadmap ambiguity and low-adoption work.'
  }
]

const backgroundEvalLoop = [
  'Candidate prompt changes are evaluated in the background using locked eval runners.',
  'Promotion requires passing trust gates, so regressions are blocked before publish.',
  'Recent scores and improvement deltas stay visible so operators can inspect system drift.'
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

function formatDate(value: string | null): string {
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

function App() {
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

  const featuredSkill = useMemo(() => {
    if (!data) {
      return null
    }
    return [...data.skills]
      .filter((skill) => skill.latest_round !== null)
      .sort((left, right) => (right.latest_round?.score ?? 0) - (left.latest_round?.score ?? 0))[0] ?? null
  }, [data])

  const statusLabel = error
    ? 'Live API unavailable. Showing the DreamFi console shell.'
    : loading
      ? 'Loading live DreamFi data'
      : 'Connected to live DreamFi data'

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <span className="brand-mark">DreamFi</span>
          <p className="brand-subtitle">Trust, measured.</p>
        </div>
        <nav className="topnav">
          <a href="#trust">Outcomes</a>
          <a href="#skills">Modules</a>
          <a href="#architecture">Operating model</a>
          <a href="#audit">Audit trail</a>
        </nav>
      </header>

      <main className="page">
        <section className="hero panel">
          <div className="hero-copy">
            <span className="eyebrow">Internal trust workspace</span>
            <h1>DreamFi’s product intelligence and trust layer.</h1>
            <p>
              We are building an internal platform for DreamFi’s product department that turns fragmented product,
              planning, risk, and financial context into trust-scored answers, summaries, and artifacts the team can
              act on.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#trust">View trust outcomes</a>
              <a className="button secondary" href="#architecture">See operating model</a>
            </div>
            <div className="status-banner">
              <span className={`status-dot ${error ? 'offline' : 'online'}`} />
              <span>{statusLabel}</span>
            </div>
          </div>
          <div className="hero-spotlight">
            <div className="spotlight-card">
              <p className="spotlight-label">Featured skill</p>
              <h2>{featuredSkill?.display_name ?? 'Waiting for eval rounds'}</h2>
              <p className="spotlight-score">{formatScore(featuredSkill?.latest_round?.score)}</p>
              <p className="spotlight-footnote">
                Latest score {featuredSkill?.latest_round ? `recorded ${formatDate(featuredSkill.latest_round.completed_at)}` : 'will appear here once a round completes'}
              </p>
            </div>
          </div>
        </section>

        <section className="metrics-grid">
          <article className="metric panel">
            <span className="metric-label">Skills registered</span>
            <strong>{data?.summary.skill_count ?? '—'}</strong>
            <p>Named artifact types currently represented in the registry.</p>
          </article>
          <article className="metric panel">
            <span className="metric-label">Active prompts</span>
            <strong>{data?.summary.active_prompt_count ?? '—'}</strong>
            <p>Exactly one active prompt per skill is the intended operating model.</p>
          </article>
          <article className="metric panel">
            <span className="metric-label">Average latest score</span>
            <strong>{formatScore(data?.summary.average_latest_score)}</strong>
            <p>Composite pass rate across the most recent eval round per active skill.</p>
          </article>
          <article className="metric panel">
            <span className="metric-label">Publish success</span>
            <strong>{formatPercent(data?.summary.publish_success_rate)}</strong>
            <p>Recent publish decisions that cleared policy and guard rails.</p>
          </article>
        </section>

        <section id="trust" className="section">
          <div className="section-header">
            <span className="eyebrow">Purpose and outcomes</span>
            <h2>One platform for product investigation, trust, and governed execution.</h2>
            <p>
              The product department should not need to manually stitch analytics, payments and ledgers, fraud signals,
              Jira workflow state, and planning docs just to answer critical questions.
            </p>
          </div>
          <div className="pillar-grid">
            {trustPillars.map((pillar) => (
              <article key={pillar.title} className="pillar panel">
                <div className="pill-row">
                  <span className="phase-pill">{pillar.phase}</span>
                  <span className="status-pill">{pillar.status}</span>
                </div>
                <h3>{pillar.title}</h3>
                <p>{pillar.body}</p>
                {pillar.title === 'Governed document generation' ? (
                  <div className="pillar-metric">
                    <span>Live export readiness</span>
                    <strong>{formatScore(data?.summary.average_export_readiness)}</strong>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-header">
            <span className="eyebrow">What this is</span>
            <h2>An internal product operations and trust layer for DreamFi.</h2>
            <p>
              Built for Product Management, Product Operations, design support, risk-adjacent product work, and
              cross-functional decision making with engineering, ops, and leadership.
            </p>
          </div>
          <div className="principles-grid">
            {principles.map((principle) => (
              <article key={principle.title} className="principle panel">
                <h3>{principle.title}</h3>
                <p>{principle.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="skills" className="section">
          <div className="section-header">
            <span className="eyebrow">Live system state</span>
            <h2>Operational readiness across governed generation modules.</h2>
            <p>
              This section reads the backend registry and recent eval rounds so teams can inspect trust and publish
              readiness without dropping into raw tables.
            </p>
          </div>
          <div className="skills-grid">
            {data?.skills.length ? (
              data.skills.map((skill) => (
                <article key={skill.skill_id} className="skill-card panel">
                  <div className="skill-card-header">
                    <div>
                      <h3>{skill.display_name}</h3>
                      <p className="skill-id">{skill.skill_id}</p>
                    </div>
                    <span className="phase-pill">v{skill.active_prompt_version ?? '—'}</span>
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
                  <div className="history-strip">
                    {skill.recent_rounds.length ? (
                      skill.recent_rounds.map((round) => (
                        <span key={round.round_id} className="history-chip">
                          {formatScore(round.score)}
                        </span>
                      ))
                    ) : (
                      <span className="history-empty">No eval rounds yet</span>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <article className="panel empty-state">
                <h3>No skill data yet</h3>
                <p>Seed the registry and run an eval round to populate this console with live measurements.</p>
              </article>
            )}
          </div>
        </section>

        <section id="architecture" className="section">
          <div className="section-header">
            <span className="eyebrow">How it behaves</span>
            <h2>Pull-first investigation with governed push and mixed data cadence.</h2>
            <p>
              Operational sources can refresh faster while planning and documentation sync on slower cadence, with each
              domain treated according to where truth is authoritative.
            </p>
            <p>
              Evals run continuously in the background as a system-improvement loop: operators get the current trust
              state, while promotion logic quietly enforces quality behind the scenes.
            </p>
          </div>
          <div className="architecture-grid">
            {architectureSteps.map((step) => (
              <article key={step.step} className="architecture-card panel">
                <span className="architecture-step">{step.step}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </article>
            ))}
            <article className="architecture-card panel">
              <span className="architecture-step">07</span>
              <h3>Background eval improvement loop</h3>
              <ul className="receipt-list">
                {backgroundEvalLoop.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className="section two-column">
          <article className="panel receipt-panel">
            <div className="section-header compact">
              <span className="eyebrow">Publish receipts</span>
              <h2>Nothing leaves DreamFi without evidence.</h2>
            </div>
            <ul className="receipt-list">
              {receiptChecklist.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="publish-feed">
              <h3>Recent publish activity</h3>
              {data?.publish_activity.length ? (
                <div className="publish-items">
                  {data.publish_activity.map((activity) => (
                    <article key={activity.publish_id} className="publish-item">
                      <div>
                        <strong>{activity.skill_id}</strong>
                        <p>{activity.destination}{activity.destination_ref ? ` · ${activity.destination_ref}` : ''}</p>
                      </div>
                      <div className="publish-meta">
                        <span className={`status-pill ${activity.decision === 'published' ? 'success' : 'blocked'}`}>
                          {activity.decision}
                        </span>
                        <time>{formatDate(activity.created_at)}</time>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="muted">No publish receipts recorded yet.</p>
              )}
            </div>
          </article>

          <article id="audit" className="panel audit-panel">
            <div className="section-header compact">
              <span className="eyebrow">Audit view</span>
              <h2>Give skeptics the evidence trail in one click.</h2>
            </div>
            <ul className="audit-list">
              {auditSurface.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </section>

        <section className="section">
          <div className="section-header">
            <span className="eyebrow">Product questions this should answer</span>
            <h2>Make fragmented product context usable for high-stakes decisions.</h2>
            <p>
              The system should quickly reveal whether an issue is product friction, fraud policy, funding behavior, or
              operational follow-through.
            </p>
          </div>
          <div className="usecase-grid">
            {useCases.map((useCase) => (
              <article key={useCase.title} className="panel usecase-card">
                <h3>{useCase.title}</h3>
                <p>{useCase.body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App

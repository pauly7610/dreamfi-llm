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
  headline: string
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
    title: 'Trust is the product',
    body: 'Retrieval, generation, routing, and publishing exist to produce artifacts a human can stake their reputation on.'
  },
  {
    title: 'Binary gates beat fuzzy scores',
    body: 'DreamFi composes pass/fail checks into an interpretable trust verdict instead of hiding behind vague middle values.'
  },
  {
    title: 'Every claim is grounded',
    body: 'Claims must resolve to a source of truth, an Onyx citation, or both. Ungrounded output fails closed.'
  },
  {
    title: 'Evaluation is code',
    body: 'Prompts, gold examples, and eval rounds move through the same promote, test, and revert lifecycle as software.'
  },
  {
    title: 'Boundaries stay narrow',
    body: 'Retrieval, generation, evaluation, and publishing are independent layers that can be tested and replaced separately.'
  },
  {
    title: 'Nothing publishes without a receipt',
    body: 'Export readiness, claims, tool trace, approvals, receipts, and rollback handles are part of the product contract.'
  }
]

const trustPillars = [
  {
    title: 'Planning trust',
    phase: 'T1',
    status: 'Planned',
    body: 'Jira and Dragonboat hygiene checks surface stale work, missing owners, and broken planning taxonomies.'
  },
  {
    title: 'Metric trust',
    phase: 'T2',
    status: 'Planned',
    body: 'A metric catalog, snapshots, and discrepancy detection stop bad numbers from silently reaching executives.'
  },
  {
    title: 'Interpretation trust',
    phase: 'T3',
    status: 'Planned',
    body: 'Claims must map to the source-of-truth catalog or retrieval citations, with anomalies explicitly acknowledged.'
  },
  {
    title: 'Artifact trust',
    phase: 'T4',
    status: 'In progress',
    body: 'Export readiness becomes the final database-enforced verdict on whether an artifact can leave the system.'
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
    title: 'PM before exec review',
    body: 'Generate a weekly brief, explain every score, and publish a draft only when the artifact clears threshold.'
  },
  {
    title: 'Founder catching drift',
    body: 'Spot regressions, compare prompt behavior, and block overnight candidate prompts before customers ever see them.'
  },
  {
    title: 'Skeptic auditing output',
    body: 'Open any artifact, inspect the full chain of evidence, and decide in minutes whether it deserves trust.'
  }
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
          <a href="#trust">Trust fabric</a>
          <a href="#skills">Skills</a>
          <a href="#architecture">Architecture</a>
          <a href="#audit">Audit</a>
        </nav>
      </header>

      <main className="page">
        <section className="hero panel">
          <div className="hero-copy">
            <span className="eyebrow">Operator console</span>
            <h1>Build AI artifacts that refuse to be wrong in silence.</h1>
            <p>
              DreamFi turns evals, grounded claims, prompt promotion, and publish receipts into a single frontend
              for shipping product work with measurable trust.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#skills">View skill health</a>
              <a className="button secondary" href="#architecture">See the system</a>
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
            <span className="eyebrow">Trust fabric</span>
            <h2>Four parallel trust surfaces, one operator view.</h2>
            <p>
              DreamFi operates like a health console for product systems: less chat UI, more vital signs,
              boundaries, and reasons.
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
                {pillar.title === 'Artifact trust' ? (
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
            <span className="eyebrow">Platform principles</span>
            <h2>The product experience is organized around DreamFi&apos;s core guarantees.</h2>
            <p>Every major section exists to surface a trust decision, a boundary, or the evidence behind one.</p>
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
            <span className="eyebrow">Skill health</span>
            <h2>Live skill registry data rendered as a trust console.</h2>
            <p>
              This section reads the current backend registry and latest eval rounds so you can inspect readiness without
              dropping into raw database tables.
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
            <span className="eyebrow">System architecture</span>
            <h2>The frontend mirrors the operational boundaries of the DreamFi platform.</h2>
            <p>
              The operator experience is shaped around the lifecycle of one generation: request, retrieve, generate,
              evaluate, score, persist, and only then publish.
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
            <span className="eyebrow">Core workflows</span>
            <h2>DreamFi is built around the operator moments where trust matters most.</h2>
            <p>
              The frontend is built to support product briefs, drift reviews, and audit flows rather than a generic chat
              transcript.
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

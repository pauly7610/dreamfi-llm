import DomainHealthGrid from '../components/console/DomainHealthGrid'
import IntegrationsPanel from '../components/console/IntegrationsPanel'
import SkillSnapshot from '../components/console/SkillSnapshot'
import type { ConsolePayload } from '../types/console'

const methodologyPoints = [
  'Ground answers in real source data and retrieval evidence.',
  'Evaluate outputs against explicit hard-gate criteria.',
  'Keep trust readable through confidence, gaps, and freshness.',
  'Make generated work reconstructible from prompts, traces, and sources.',
  'Gate publish behind policy and operator review when needed.',
]

const operatingSurfaces = [
  {
    title: 'Ask',
    description: 'Start from a Product question and keep evidence receipts attached to the answer.',
  },
  {
    title: 'Topic rooms',
    description: 'Gather recurring questions, sources, and gaps around the decisions Product makes most often.',
  },
  {
    title: 'Source workspaces',
    description: 'Open Jira, PostHog, Metabase, Klaviyo, and the other connectors in their own familiar surface.',
  },
  {
    title: 'Generated artifacts',
    description: 'Turn grounded context into briefs, PRDs, and risk work once the answer is solid enough to reuse.',
  },
  {
    title: 'Trust review',
    description: 'See health, blocked work, and known limits without mixing those mechanics into the home page.',
  },
]

type TrustPageProps = {
  data: ConsolePayload | null
}

function TrustPage({ data }: TrustPageProps) {
  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Trust view</span>
        <h2>Why work is healthy vs risky</h2>
        <p>See the live trust surfaces and the system mechanics behind grounding, evaluation, reconstruction, and publish safety.</p>
      </section>
      <DomainHealthGrid items={data?.domain_health ?? []} />
      <IntegrationsPanel
        items={data?.integrations ?? []}
        title="Connected grounding sources"
        description="These are the systems DreamFi reads from and writes to when building trust-scored artifacts. Each PRD, brief, or BRD is reconstructible from the sources tagged below."
      />
      <section className="split-grid">
        <section className="panel methodology-panel">
          <div className="section-heading">
            <span className="eyebrow">Methodology</span>
            <h2>How DreamFi works</h2>
          </div>
          <ul className="detail-list">
            {methodologyPoints.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
        <section className="panel methodology-panel">
          <div className="section-heading">
            <span className="eyebrow">Current surfaces</span>
            <h2>How Product moves through DreamFi now</h2>
          </div>
          <div className="module-list">
            {operatingSurfaces.map((surface) => (
              <article key={surface.title} className="module-list-item">
                <strong>{surface.title}</strong>
                <p>{surface.description}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
      <SkillSnapshot skills={data?.skills ?? []} />
    </div>
  )
}

export default TrustPage

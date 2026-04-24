import DomainHealthGrid from '../components/console/DomainHealthGrid'
import LivePulsePanel from '../components/console/LivePulsePanel'
import IntegrationsPanel from '../components/console/IntegrationsPanel'
import SkillSnapshot from '../components/console/SkillSnapshot'
import TrustActionRail from '../components/console/TrustActionRail'
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
  const latestAlert = data?.alerts[0] ?? null
  const latestArtifact = data?.artifact_queue[0] ?? null
  const latestPublish = data?.publish_activity[0] ?? null
  const degradedSource = (data?.integrations ?? []).find((integration) => integration.status === 'degraded') ?? null
  const livePulseItems = [
    latestAlert
      ? {
          label: 'Alert',
          value: latestAlert.title,
          detail: latestAlert.message,
          href: latestAlert.href ?? '/console/trust',
          hrefLabel: latestAlert.href ? 'Open issue' : 'Stay here',
        }
      : null,
    latestArtifact
      ? {
          label: 'Draft state',
          value: latestArtifact.test_input_label,
          detail: `${latestArtifact.skill_display_name ?? 'Artifact'} is ${latestArtifact.status.replace('_', ' ')} with confidence ${latestArtifact.confidence ?? '--'}.`,
          href: '/console/review',
          hrefLabel: 'Open review',
        }
      : null,
    latestPublish
      ? {
          label: 'Latest publish',
          value: latestPublish.destination_ref ?? latestPublish.destination,
          detail: `DreamFi most recently ${latestPublish.decision} work into the shared product system.`,
          href: '/console/methodology',
          hrefLabel: 'Open methodology',
        }
      : null,
    degradedSource
      ? {
          label: 'Connector risk',
          value: degradedSource.name,
          detail: 'The current trust posture is being shaped by an unhealthy source connector.',
          href: degradedSource.href,
          hrefLabel: 'Inspect source',
        }
      : null,
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))
  const trustActions = [
    latestAlert?.href
      ? {
          title: latestAlert.title,
          detail: latestAlert.message,
          href: latestAlert.href,
          hrefLabel: 'Resolve from source',
          tone: (latestAlert.severity === 'warning' || latestAlert.severity === 'critical' ? 'warning' : 'info') as
            | 'warning'
            | 'info',
        }
      : null,
    degradedSource
      ? {
          title: `Inspect ${degradedSource.name}`,
          detail: 'The trust surface should link directly into the connector that is shaping the current caveat.',
          href: degradedSource.href,
          hrefLabel: 'Open connector',
          tone: 'warning' as const,
        }
      : null,
    latestArtifact
      ? {
          title: 'Review the latest governed draft',
          detail: 'Trust should point straight at the draft that most needs a decision, not just summarize the queue.',
          href: '/console/review',
          hrefLabel: 'Open review queue',
          tone: 'ready' as const,
        }
      : null,
  ].filter((item): item is NonNullable<typeof item> => Boolean(item))

  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Trust view</span>
        <h2>Why work is healthy vs risky</h2>
        <p>See the live trust surfaces and the system mechanics behind grounding, evaluation, reconstruction, and publish safety.</p>
      </section>
      <LivePulsePanel
        title="Trust should feel live, not archival"
        description="These signals tie the trust model back to the current product world so the page feels operational instead of purely descriptive."
        items={livePulseItems}
      />
      <TrustActionRail
        title="Act on the current trust posture"
        description="Use this page to move into the exact alert, source, or draft that is driving today's trust state."
        actions={trustActions}
      />
      <DomainHealthGrid items={data?.domain_health ?? []} />
      <IntegrationsPanel
        items={data?.integrations ?? []}
        title="Connected grounding sources"
        description="These are the systems DreamFi reads from and writes to when building trust-scored artifacts. Each PRD, brief, or BRD is reconstructible from the sources tagged below."
      />
      <section className="split-grid">
        <section className="panel methodology-panel">
          <div className="section-heading inline">
            <div>
              <span className="eyebrow">Methodology</span>
              <h2>How DreamFi works</h2>
            </div>
            <a className="text-link" href="/console/methodology">Open full methodology</a>
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

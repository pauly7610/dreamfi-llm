import type { ConsolePayload } from '../types/console'

type GeneratePageProps = {
  data: ConsolePayload | null
  templateName: string
}

function prettifyTemplateName(templateName: string): string {
  return templateName
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function GeneratePage({ data, templateName }: GeneratePageProps) {
  const pageTitle = prettifyTemplateName(templateName)

  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Generate</span>
        <h2>{pageTitle}</h2>
        <p>Start a governed generation workflow, then inspect the artifact, review trust results, and publish only if policy clears.</p>
      </section>
      <section className="action-center panel">
        <div className="section-heading">
          <span className="eyebrow">Available workflows</span>
          <h2>Choose the right generation path</h2>
        </div>
        <div className="action-grid">
          {(data?.quick_actions ?? []).map((action) => (
            <a key={action.id} className={`action-card ${action.kind}`} href={action.href}>
              <strong>{action.label}</strong>
              <span>{action.href.replace('/console/', '')}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

export default GeneratePage

import DomainHealthGrid from '../components/console/DomainHealthGrid'
import SkillSnapshot from '../components/console/SkillSnapshot'
import { methodologyPoints, coreModules } from '../config/dreamfiThesis'
import type { ConsolePayload } from '../types/console'

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
            <span className="eyebrow">Core modules</span>
            <h2>The five operating surfaces</h2>
          </div>
          <div className="module-list">
            {coreModules.map((module) => (
              <article key={module.title} className="module-list-item">
                <strong>{module.title}</strong>
                <p>{module.description}</p>
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

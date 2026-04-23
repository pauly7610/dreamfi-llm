const principles = [
  {
    title: 'Start with the question',
    body: 'Product should begin with the decision they are trying to make, not with a guess about which system might hold the answer.',
  },
  {
    title: 'Keep evidence attached',
    body: 'Answers, briefs, and generated artifacts should carry receipts back to the systems and slices they came from.',
  },
  {
    title: 'Make trust visible',
    body: 'Confidence, freshness, hard-gate status, and review gaps should stay legible instead of hiding behind a single polished answer.',
  },
  {
    title: 'Reuse grounded context',
    body: 'Once a question is well-scoped and sourced, DreamFi should help Product turn that same context into briefs, PRDs, and follow-up work.',
  },
]

const operatingModel = [
  {
    step: '01',
    title: 'Ask from the source room',
    body: 'Start with a Product question and let DreamFi pull evidence from the right connected systems instead of hopping tool to tool.',
  },
  {
    step: '02',
    title: 'Narrow with topic rooms',
    body: 'Recurring decisions like onboarding, KYC, funding, and lifecycle work should have their own rooms with shared sources, gaps, and starter prompts.',
  },
  {
    step: '03',
    title: 'Inspect source workspaces',
    body: 'When the answer depends on one system, Product should be able to open that connector workspace and see the relevant slice directly.',
  },
  {
    step: '04',
    title: 'Generate from grounded context',
    body: 'Once the evidence is good enough, DreamFi can turn it into a brief, PRD, or risk artifact without losing the source trail.',
  },
  {
    step: '05',
    title: 'Apply trust and publish rails',
    body: 'Hard gates, confidence, and review state should determine whether generated work is ready to move forward.',
  },
]

const technicalModel = [
  'Onyx handles retrieval, citations, and the connected knowledge substrate.',
  'FastAPI serves the console data, APIs, and the built operator shell.',
  'Locked eval runners score outputs so prompt changes can be improved without hand-wavy quality drift.',
  'Promotion and publish guards stop regressions from silently becoming production behavior.',
]

function MethodologyPage() {
  return (
    <div className="page-grid">
      <section className="panel page-intro">
        <span className="eyebrow">Methodology</span>
        <h2>How DreamFi should feel to Product and how it works underneath.</h2>
        <p>
          DreamFi is meant to be a calm product source room: start with the question, inspect evidence in the right
          systems, and only then turn that context into work Product can reuse or publish.
        </p>
      </section>

      <section className="split-grid">
        <section className="panel methodology-panel">
          <div className="section-heading">
            <span className="eyebrow">Principles</span>
            <h2>What the product experience optimizes for</h2>
          </div>
          <div className="module-list">
            {principles.map((principle) => (
              <article key={principle.title} className="module-list-item">
                <strong>{principle.title}</strong>
                <p>{principle.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel methodology-panel">
          <div className="section-heading">
            <span className="eyebrow">Technical model</span>
            <h2>What enforces trust behind the scenes</h2>
          </div>
          <ul className="detail-list">
            {technicalModel.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </section>

      <section className="panel methodology-panel">
        <div className="section-heading">
          <span className="eyebrow">Operating model</span>
          <h2>How Product should move through DreamFi</h2>
        </div>
        <div className="architecture-grid">
          {operatingModel.map((step) => (
            <article key={step.step} className="architecture-card panel">
              <span className="architecture-step">{step.step}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default MethodologyPage

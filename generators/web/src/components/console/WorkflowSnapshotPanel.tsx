import type { ProductWorkflowModel } from '../../content/productWorkflows'

function askHref(topicId: string, question: string): string {
  return `/console/knowledge/ask?topic=${topicId}&q=${encodeURIComponent(question)}`
}

type WorkflowSnapshotPanelProps = {
  workflow: ProductWorkflowModel
}

function WorkflowSnapshotPanel({ workflow }: WorkflowSnapshotPanelProps) {
  return (
    <section className="workflow-state-panel panel">
      <div className="section-heading inline workflow-heading">
        <div>
          <span className="eyebrow">Workflow state</span>
          <h2>Where this work stands</h2>
        </div>
        <span className={`workflow-readiness-pill ${workflow.currentState.tone}`}>{workflow.currentState.readiness}</span>
      </div>

      <div className="workflow-state-strip" aria-label="Workflow summary">
        <div className="workflow-state-card">
          <span>Phase</span>
          <strong>{workflow.currentState.phase}</strong>
          <small>Current product phase</small>
        </div>
        <div className="workflow-state-card">
          <span>Step</span>
          <strong>{workflow.currentState.step}</strong>
          <small>Critical gate or handoff</small>
        </div>
        <div className="workflow-state-card">
          <span>Jira state</span>
          <strong>{workflow.currentState.jiraState}</strong>
          <small>What delivery tools imply right now</small>
        </div>
      </div>

      <div className="workflow-decision-card">
        <span>Next decision</span>
        <strong>{workflow.nextDecision}</strong>
        <p>{workflow.recommendation}</p>
      </div>

      <div className="workflow-detail-grid">
        <div className="workflow-section-block">
          <div className="workflow-block-heading">
            <span className="eyebrow">Gate checks</span>
            <h3>Can this move forward?</h3>
          </div>
          <div className="workflow-gate-list">
            {workflow.gates.map((gate) => (
              <article key={gate.label} className={`workflow-gate-row ${gate.status}`}>
                <div>
                  <span>{gate.label}</span>
                  <strong>{gate.summary}</strong>
                </div>
                <p>{gate.detail}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="workflow-side-column">
          <div className="workflow-section-block">
            <div className="workflow-block-heading">
              <span className="eyebrow">Gap detection</span>
              <h3>What is missing?</h3>
            </div>
            <ul className="workflow-bullet-list">
              {workflow.missing.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="workflow-section-block">
            <div className="workflow-block-heading">
              <span className="eyebrow">Ownership clarity</span>
              <h3>Who needs to act next?</h3>
            </div>
            <div className="workflow-owner-list">
              {workflow.owners.map((owner) => (
                <article key={owner.role} className="workflow-owner-row">
                  <div>
                    <span>{owner.role}</span>
                    <strong>{owner.owner}</strong>
                  </div>
                  <p>{owner.nextAction}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="workflow-section-block workflow-risk-block">
        <div className="workflow-block-heading">
          <span className="eyebrow">Risk visibility</span>
          <h3>What could go wrong?</h3>
        </div>
        <div className="workflow-risk-list">
          {workflow.risks.map((risk) => (
            <article key={risk.label} className={`workflow-risk-row ${risk.level}`}>
              <div>
                <span>{risk.level} risk</span>
                <strong>{risk.label}</strong>
              </div>
              <p>{risk.detail}</p>
              <small>Owner: {risk.owner}</small>
            </article>
          ))}
        </div>
      </div>

      <div className="workflow-question-groups">
        {workflow.questionGroups.map((group) => (
          <div key={group.title} className="workflow-question-group">
            <span>{group.title}</span>
            <div className="prompt-chips">
              {group.questions.map((question) => (
                <a key={question} href={askHref(workflow.topicId, question)}>
                  {question}
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default WorkflowSnapshotPanel

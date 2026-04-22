import type { ProductWorkflowModel } from '../../content/productWorkflows'
import type { ConsoleIntegration } from '../../types/console'
import ConnectorLogo from './ConnectorLogo'

type ConnectorCoveragePanelProps = {
  workflow: ProductWorkflowModel
  integrations: ConsoleIntegration[]
}

function ConnectorCoveragePanel({ workflow, integrations }: ConnectorCoveragePanelProps) {
  return (
    <aside className="connector-coverage-panel panel">
      <span className="eyebrow">Connector responsibilities</span>
      <h2>What each system can tell us</h2>
      <div className="connector-coverage-list">
        {workflow.connectorCoverage.map((coverage) => {
          const source = integrations.find((integration) => integration.id === coverage.sourceId)
          const href = source?.href ?? `/console/integrations/${coverage.sourceId}`
          const name = source?.name ?? coverage.sourceId

          return (
            <a key={coverage.sourceId} className="connector-coverage-row" href={href}>
              <div className="connector-coverage-header">
                <div className="connector-coverage-title">
                  <ConnectorLogo id={coverage.sourceId} name={name} />
                  <div>
                    <strong>{name}</strong>
                    <small>{coverage.role}</small>
                  </div>
                </div>
                <span className="connector-coverage-badge">Best for</span>
              </div>
              <p>{coverage.bestFor}</p>
              <small>{coverage.detail}</small>
              <em>{coverage.driftNote}</em>
            </a>
          )
        })}
      </div>
    </aside>
  )
}

export default ConnectorCoveragePanel

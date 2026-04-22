import { renderGaWorkspace, renderKlaviyoWorkspace, renderMetabaseWorkspace, renderPosthogWorkspace } from './workspace/analyticsWorkspaces'
import { renderConfluenceWorkspace, renderGenericWorkspace } from './workspace/knowledgeWorkspaces'
import { renderDragonboatWorkspace, renderJiraWorkspace, renderNetxdWorkspace, renderSardineWorkspace } from './workspace/operationsWorkspaces'
import type { WorkspaceRendererProps } from './workspace/types'

function ConnectorWorkspace(props: WorkspaceRendererProps) {
  switch (props.workspace.connector.id) {
    case 'jira':
      return renderJiraWorkspace(props)
    case 'posthog':
      return renderPosthogWorkspace(props)
    case 'metabase':
      return renderMetabaseWorkspace(props)
    case 'klaviyo':
      return renderKlaviyoWorkspace(props)
    case 'confluence':
      return renderConfluenceWorkspace(props)
    case 'ga':
      return renderGaWorkspace(props)
    case 'dragonboat':
      return renderDragonboatWorkspace(props)
    case 'sardine':
      return renderSardineWorkspace(props)
    case 'netxd':
      return renderNetxdWorkspace(props)
    default:
      return renderGenericWorkspace(props)
  }
}

export default ConnectorWorkspace

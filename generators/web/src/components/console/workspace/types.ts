import type { ProductTopic } from '../../../content/productTopics'
import type { ConnectorWorkspacePayload } from '../../../types/connectorWorkspace'

export type WorkspaceRendererProps = {
  relatedTopics: ProductTopic[]
  workspace: ConnectorWorkspacePayload
}

import { analyticsSourcePreviews } from './analyticsSourcePreviews'
import { defaultSourcePreview } from './sourcePreviewDefaults'
import { workflowSourcePreviews } from './workflowSourcePreviews'
import type { ConsoleIntegration } from '../types/console'
import type { SourceDataPreview } from './sourcePreviewTypes'

export type {
  SourceDataPreview,
  SourceDataRow,
  SourceInspectItem,
  SourceReviewCase,
  SourceWorkflow,
} from './sourcePreviewTypes'

const sourceDataPreviews: Record<string, SourceDataPreview> = {
  ...analyticsSourcePreviews,
  ...workflowSourcePreviews,
}

export function getSourceDataPreview(source: ConsoleIntegration): SourceDataPreview {
  return sourceDataPreviews[source.id] ?? defaultSourcePreview(source)
}

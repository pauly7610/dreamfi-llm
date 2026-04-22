export type SourceDataRow = {
  label: string
  value: string
  detail: string
}

export type SourceInspectItem = {
  title: string
  detail: string
}

export type SourceWorkflow = {
  title: string
  detail: string
  href: string
}

export type SourceReviewCase = {
  id: string
  label: string
  status: 'questionable' | 'stepped_up' | 'cleared'
  stage: string
  signal: string
  detail: string
  nextStep: string
  updatedAt: string
}

export type SourceDataPreview = {
  headline: string
  description: string
  freshness: string
  primaryDataset: string
  rows: SourceDataRow[]
  inspect: SourceInspectItem[]
  workflows: SourceWorkflow[]
  views: string[]
  questions: string[]
  reviewCases?: SourceReviewCase[]
}

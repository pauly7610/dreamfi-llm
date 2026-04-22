export type ConsoleSummary = {
  skill_count: number
  active_prompt_count: number
  average_latest_score: number | null
  average_confidence: number | null
  average_export_readiness: number | null
  publish_success_rate: number | null
  hard_gate_pass_rate: number | null
  blocked_artifact_count: number
  publish_ready_count: number
  published_artifact_count: number
  needs_review_count: number
}

export type RoundSummary = {
  round_id: string
  prompt_version_id: string
  score: number
  previous_score: number | null
  improvement: number | null
  completed_at: string | null
  artifacts_path: string
}

export type SkillCard = {
  skill_id: string
  display_name: string
  description: string
  criteria_count: number
  active_prompt_version: number | null
  latest_round: RoundSummary | null
  recent_rounds: RoundSummary[]
}

export type PublishActivity = {
  publish_id: string
  skill_id: string
  destination: string
  destination_ref: string | null
  decision: string
  reason: string | null
  created_at: string
}

export type ArtifactRecord = {
  output_id: string
  skill_id: string | null
  skill_display_name: string | null
  round_id: string
  test_input_label: string
  attempt: number
  pass_fail: string
  confidence: number | null
  export_readiness: number | null
  created_at: string
  status: 'blocked' | 'publish_ready' | 'published' | 'needs_review'
  artifacts_path: string | null
  latest_publish: PublishActivity | null
}

export type ConsoleAlert = {
  id: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  href?: string | null
  created_at: string | null
}

export type QuickAction = {
  id: string
  label: string
  href: string
  kind: 'primary' | 'secondary'
}

export type ConsoleContextChange = {
  id: string
  title: string
  summary: string
  href: string
  changed_at: string
  tone: 'neutral' | 'watch' | 'critical'
}

export type ConsoleDomainHealth = {
  domain: 'planning' | 'metrics' | 'generation' | 'publish'
  trust_score: number | null
  pass_rate: number | null
  issue_count: number
}

export type IntegrationCategory =
  | 'planning'
  | 'docs'
  | 'metrics'
  | 'product_analytics'
  | 'marketing_analytics'
  | 'marketing'
  | 'payments'
  | 'risk'
  | 'identity'

export type IntegrationStatus = 'connected' | 'degraded' | 'available' | 'not_configured'

export type ConsoleIntegration = {
  id: string
  name: string
  category: IntegrationCategory
  purpose: string
  used_for: string[]
  status: IntegrationStatus
  href: string
}

export type ConsolePayload = {
  headline: string
  summary: ConsoleSummary
  context_changes?: ConsoleContextChange[]
  skills: SkillCard[]
  artifact_queue: ArtifactRecord[]
  publish_activity: PublishActivity[]
  alerts: ConsoleAlert[]
  quick_actions: QuickAction[]
  integrations: ConsoleIntegration[]
  domain_health: ConsoleDomainHealth[]
}

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
export type ConnectionMethod = 'onyx_native' | 'custom_ingestion'

export type ConsoleIntegration = {
  id: string
  name: string
  category: IntegrationCategory
  purpose: string
  used_for: string[]
  status: IntegrationStatus
  href: string
  connection_method: ConnectionMethod
  setup_method: string
  setup_detail: string
  requires_dreamfi_secret: boolean
  config_schema: SettingsConnectorConfigField[]
}

export type SourceInsightQuality = {
  score: number
  checks: Record<string, boolean>
  blockers: string[]
}

export type SourceProvenance = {
  kind: 'source_contract' | 'connector_document' | 'artifact' | 'demo_packet'
  connector_document_id: string | null
  sync_run_id: string | null
  output_id: string | null
}

export type SourceInsight = {
  insight_id: string
  source_id: string
  source_name: string
  title: string
  finding: string
  evidence: string
  decision_relevance: string
  gap: string | null
  metric: string | null
  updated_at: string | null
  topic_ids: string[]
  owner: string
  quality: SourceInsightQuality
  href: string
  source_status: IntegrationStatus
  method: ConnectionMethod
  source_url: string | null
  is_demo: boolean
  provenance: SourceProvenance
}

export type SourcePacketRecord = {
  packet_id: string
  source_id: string
  source_name: string
  title: string
  snippet: string
  metric: string
  source_url: string | null
  doc_updated_at: string | null
  persisted_at: string | null
  last_seen_at: string | null
  last_ingested_at: string | null
  connector_document_id: string | null
  sync_run_id: string | null
  onyx_document_id: string | null
  external_id: string | null
  topic_ids: string[]
  owner: string
  product_area: string
  sensitivity: string
  redaction_profile: string
  status: 'live' | 'stale' | 'not_ingested' | 'missing_freshness' | 'demo'
  source_status: IntegrationStatus
  method: ConnectionMethod
  stale: boolean
  changed_since_last_sync: boolean
  is_demo: boolean
  provenance: SourceProvenance
}

export type SourceContradiction = {
  contradiction_id: string
  topic_id: string
  title: string
  summary: string
  severity: 'info' | 'warning' | 'critical'
  source_ids: string[]
  packet_ids: string[]
  evidence: string[]
  recommended_action: string
  updated_at: string | null
  is_demo: boolean
}

export type SourceRefreshSummary = {
  configured: boolean
  schedule_id: string | null
  cadence_days: number | null
  next_run_at: string | null
  last_run_at: string | null
  active_source_count: number
  packet_count: number
  demo_packet_count: number
  failed_source_count: number
  stale_source_count: number
  latest_sync_status: string | null
  latest_sync_at: string | null
  href: string
}

export type EvidenceExportSummary = {
  href: string
  generated_at: string
  source_packet_count: number
  real_source_packet_count: number
  demo_source_packet_count: number
  contradiction_count: number
  refresh_configured: boolean
  contains_demo_data: boolean
}

export type ConsoleTopicRecord = {
  id: string
  title: string
  summary: string
  question: string
  source_ids: string[]
  default_generator_slug: string
  created_at: string
}

export type ConsolePayload = {
  headline: string
  summary: ConsoleSummary
  skills: SkillCard[]
  artifact_queue: ArtifactRecord[]
  publish_activity: PublishActivity[]
  alerts: ConsoleAlert[]
  quick_actions: QuickAction[]
  integrations: ConsoleIntegration[]
  source_insights: SourceInsight[]
  source_packets: SourcePacketRecord[]
  source_contradictions: SourceContradiction[]
  source_refresh: SourceRefreshSummary
  evidence_export_summary: EvidenceExportSummary
  custom_topics: ConsoleTopicRecord[]
  domain_health: ConsoleDomainHealth[]
}

export type SettingsCheck = {
  detail: string
  name: string
  passed?: boolean
  present?: boolean
  configured?: boolean
}

export type SettingsConnector = {
  connector_id: string
  name: string
  category: IntegrationCategory
  purpose: string
  used_for: string[]
  expected_document_set: string
  connection_method: ConnectionMethod
  setup_method: string
  setup_detail: string
  requires_dreamfi_secret: boolean
  config_schema: SettingsConnectorConfigField[]
  config: {
    values: Record<string, string>
    missing_keys: string[]
  }
  metadata_keys: string[]
  credential: {
    status: 'missing' | 'saved'
    masked: string | null
    label: string | null
    validated_at: string | null
    required: boolean
    storage: 'encrypted' | 'env' | 'metadata_only' | 'missing'
    usable: boolean
  }
  validation_status: 'not_validated' | 'validated' | 'validation_failed'
  validation_error: string | null
  document_set_present: boolean
  document_set_id: number | null
  document_set_name: string
  retrieval_status: 'not_checked' | 'fresh' | 'stale' | 'empty' | 'missing_freshness' | 'error'
  freshest_document_at: string | null
  last_probe_at: string | null
  activation_status: 'inactive' | 'active' | 'degraded'
  activated_at: string | null
  latest_sync: ConnectorSyncRun | null
  blockers: string[]
  can_activate: boolean
  href: string
}

export type SettingsConnectorConfigField = {
  key: string
  label: string
  required: boolean
  placeholder: string
  help_text: string
  default: string | null
}

export type ConnectorSyncRun = {
  sync_run_id: string
  connector_id?: string
  status: 'running' | 'success' | 'failed'
  trigger: string
  pulled_count: number
  persisted_count: number
  ingested_count: number
  skipped_count?: number
  error_count: number
  reason: string | null
  started_at: string
  completed_at: string | null
}

export type SettingsStatus = {
  status: 'ready' | 'blocked' | 'degraded'
  failures: string[]
  summary: {
    connector_count: number
    configured_connector_count: number
    active_connector_count: number
    blocked_connector_count: number
  }
  environment: {
    checks: SettingsCheck[]
    placeholder_values: string[]
    ready: boolean
  }
  persistence: {
    ready: boolean
    uses_sqlite: boolean
    alembic_version: string | null
    expected_alembic_head: string
    checks: SettingsCheck[]
    counts: Record<string, number>
    audit: Record<string, unknown>
  }
  jobs: {
    replay: {
      due_schedule_count: number
      error_count_24h: number
      latest_run: Record<string, unknown> | null
    }
    connector_health_checks: {
      configured: boolean
      active_connector_count: number
    }
  }
  connectors: SettingsConnector[]
}

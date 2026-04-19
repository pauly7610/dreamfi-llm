-- Test data seed for Phase 0 integration tests
-- Inserts minimal test data to verify retrieval, eval, and publishing workflows

BEGIN;

-- ============================================
-- 1. SEED SKILL REGISTRY (3 Tier-1 skills)
-- ============================================
INSERT INTO skill_registry (skill_name, skill_family, evaluation_file_path, primary_output_type, word_limit_rule, status, owner)
VALUES
  ('agent_system_prompt', 'response', '/evals/agent-system-prompt.md', 'text', 80, 'active', 'platform@dreamfi.com'),
  ('support_agent', 'response', '/evals/support-agent.md', 'text', 120, 'active', 'support@dreamfi.com'),
  ('meeting_summary', 'summary', '/evals/meeting-summary.md', 'text', 300, 'active', 'operations@dreamfi.com')
ON CONFLICT (skill_name) DO NOTHING;

-- ============================================
-- 2. SEED PROMPT VERSIONS (v1 for each skill)
-- ============================================
INSERT INTO prompt_versions (skill_id, prompt_text, change_summary, created_by, is_active)
SELECT 
  skill_id,
  'You are a helpful assistant. Answer the question directly.',
  'Initial prompt version',
  'platform@dreamfi.com',
  TRUE
FROM skill_registry
WHERE skill_name IN ('agent_system_prompt', 'support_agent', 'meeting_summary')
ON CONFLICT DO NOTHING;

-- ============================================
-- 3. SEED EVALUATION CRITERIA (hard gates for Tier-1 skills)
-- ============================================
-- agent_system_prompt criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight)
SELECT skill_id, 'word_limit_80', 'Output must be 80 words or less', 'hard_gate', TRUE, 0.25
FROM skill_registry WHERE skill_name = 'agent_system_prompt'
ON CONFLICT (skill_id, criterion_key) DO NOTHING;

INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight)
SELECT skill_id, 'specific_next_action', 'Response includes specific next action', 'hard_gate', TRUE, 0.25
FROM skill_registry WHERE skill_name = 'agent_system_prompt'
ON CONFLICT (skill_id, criterion_key) DO NOTHING;

-- support_agent criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight)
SELECT skill_id, 'word_limit_120', 'Output must be 120 words or less', 'hard_gate', TRUE, 0.33
FROM skill_registry WHERE skill_name = 'support_agent'
ON CONFLICT (skill_id, criterion_key) DO NOTHING;

INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight)
SELECT skill_id, 'kb_only', 'Response uses only knowledge base information', 'hard_gate', TRUE, 0.33
FROM skill_registry WHERE skill_name = 'support_agent'
ON CONFLICT (skill_id, criterion_key) DO NOTHING;

-- meeting_summary criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight)
SELECT skill_id, 'action_items_formatted', 'Action items include owner and deadline', 'hard_gate', TRUE, 0.33
FROM skill_registry WHERE skill_name = 'meeting_summary'
ON CONFLICT (skill_id, criterion_key) DO NOTHING;

-- ============================================
-- 4. SEED TEST INPUTS (for eval runners)
-- ============================================
INSERT INTO test_input_registry (skill_id, input_label, input_text, scenario_type, source_file_path)
SELECT 
  skill_id,
  'basic_question',
  'What is the current status of the Q2 roadmap?',
  'straightforward',
  '/evals/agent-system-prompt.md'
FROM skill_registry WHERE skill_name = 'agent_system_prompt'
ON CONFLICT DO NOTHING;

INSERT INTO test_input_registry (skill_id, input_label, input_text, scenario_type, source_file_path)
SELECT 
  skill_id,
  'basic_support',
  'User cannot login to their account',
  'support_issue',
  '/evals/support-agent.md'
FROM skill_registry WHERE skill_name = 'support_agent'
ON CONFLICT DO NOTHING;

INSERT INTO test_input_registry (skill_id, input_label, input_text, scenario_type, source_file_path)
SELECT 
  skill_id,
  'team_meeting',
  'Discussed Q2 planning, decided on priorities, action items assigned',
  'internal_meeting',
  '/evals/meeting-summary.md'
FROM skill_registry WHERE skill_name = 'meeting_summary'
ON CONFLICT DO NOTHING;

-- ============================================
-- 5. SEED CORE ENTITIES (sample data from connectors)
-- ============================================
INSERT INTO core_entities (entity_type, name, description, owner, status, source_system, source_object_id, source_url, freshness_score, confidence_score, eligible_skill_families_json)
VALUES
  ('jira_issue', 'DFI-100: Implement Knowledge Hub', 'Core infrastructure for product knowledge', 'platform@dreamfi.com', 'in_progress', 'jira', 'jira-100', 'https://dreamfi.atlassian.net/browse/DFI-100', 0.95, 0.90, '["response", "summary"]'),
  ('dragonboat_milestone', 'Q2 Phase 1 Delivery', 'Phase 1 Knowledge Hub delivery milestone', 'platform@dreamfi.com', 'active', 'dragonboat', 'db-milestone-001', 'https://api.dragonboat.app/milestones/001', 0.92, 0.85, '["summary"]'),
  ('confluence_doc', 'Product Knowledge Base', 'Central knowledge base for product decisions', 'product@dreamfi.com', 'published', 'confluence', 'conf-page-5001', 'https://dreamfi.atlassian.net/wiki/spaces/KB/pages/5001', 0.88, 0.82, '["response"]'),
  ('metabase_metric', 'Weekly Active Users', 'WAU tracking by cohort', 'analytics@dreamfi.com', 'active', 'metabase', 'mb-metric-42', 'https://metabase.dreamfi.com/metric/42', 0.99, 0.95, '["summary"]');

-- ============================================
-- 6. SEED CITATIONS (linking entities to sources)
-- ============================================
INSERT INTO citations (entity_id, source_system, source_object_id, source_snippet, source_url)
SELECT 
  e.entity_id,
  'jira',
  'jira-100',
  'Phase 1 covers Knowledge Hub retrieval, Skill Registry, and Evaluation infrastructure',
  'https://dreamfi.atlassian.net/browse/DFI-100'
FROM core_entities e
WHERE e.name = 'DFI-100: Implement Knowledge Hub'
LIMIT 1;

-- ============================================
-- 7. SEED WATERMARKS (for connector sync tracking)
-- ============================================
INSERT INTO connector_watermarks (connector_name, last_sync_time, status)
VALUES
  ('jira', NOW() - INTERVAL '1 hour', 'healthy'),
  ('dragonboat', NOW() - INTERVAL '2 hours', 'healthy'),
  ('confluence', NOW() - INTERVAL '30 minutes', 'healthy'),
  ('metabase', NOW() - INTERVAL '1 day', 'stale')
ON CONFLICT (connector_name) DO NOTHING;

COMMIT;

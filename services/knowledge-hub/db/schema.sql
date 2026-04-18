-- ============================================================
-- DreamFi Knowledge Hub - PostgreSQL Schema
-- Phase 1 Foundation
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- trigram index for full-text search

-- ============================================================
-- 1. core_entities
-- ============================================================
CREATE TABLE core_entities (
    entity_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type            VARCHAR(100)  NOT NULL,
    name                   VARCHAR(500)  NOT NULL,
    description            TEXT,
    owner                  VARCHAR(255),
    status                 VARCHAR(50)   DEFAULT 'active',
    source_system          VARCHAR(100),
    source_object_id       VARCHAR(500),
    source_url             TEXT,
    last_synced_at         TIMESTAMPTZ,
    freshness_score        DECIMAL(4,3)  DEFAULT 1.000 CHECK (freshness_score >= 0 AND freshness_score <= 1),
    confidence_score       DECIMAL(4,3)  DEFAULT 1.000 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    eligible_skill_families_json JSONB   DEFAULT '[]'::jsonb,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_core_entities_type ON core_entities(entity_type);
CREATE INDEX idx_core_entities_status ON core_entities(status);
CREATE INDEX idx_core_entities_source ON core_entities(source_system, source_object_id);
CREATE INDEX idx_core_entities_name_trgm ON core_entities USING gin(name gin_trgm_ops);
CREATE INDEX idx_core_entities_description_trgm ON core_entities USING gin(description gin_trgm_ops);
CREATE INDEX idx_core_entities_freshness ON core_entities(freshness_score);
CREATE INDEX idx_core_entities_updated ON core_entities(updated_at DESC);

-- ============================================================
-- 2. relationships
-- ============================================================
CREATE TABLE relationships (
    relationship_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_entity_id    UUID         NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    to_entity_id      UUID         NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    source_system     VARCHAR(100),
    evidence_ref      TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_relationships_from ON relationships(from_entity_id);
CREATE INDEX idx_relationships_to ON relationships(to_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- Prevent duplicate relationships
ALTER TABLE relationships
    ADD CONSTRAINT uq_relationship_pair
    UNIQUE (from_entity_id, relationship_type, to_entity_id);

-- ============================================================
-- 3. citations
-- ============================================================
CREATE TABLE citations (
    citation_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id         UUID         NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    source_system     VARCHAR(100) NOT NULL,
    source_object_id  VARCHAR(500),
    source_snippet    TEXT,
    source_url        TEXT,
    captured_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_citations_entity ON citations(entity_id);
CREATE INDEX idx_citations_source ON citations(source_system);

-- ============================================================
-- 4. skill_registry
-- ============================================================
CREATE TABLE skill_registry (
    skill_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name              VARCHAR(200) NOT NULL UNIQUE,
    skill_family            VARCHAR(100) NOT NULL,
    evaluation_file_path    VARCHAR(500),
    primary_output_type     VARCHAR(100),
    word_limit_rule         JSONB        DEFAULT '{}'::jsonb,
    active_prompt_version_id UUID,       -- FK added after prompt_versions table
    status                  VARCHAR(50)  NOT NULL DEFAULT 'active',
    owner                   VARCHAR(255),
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skill_registry_family ON skill_registry(skill_family);
CREATE INDEX idx_skill_registry_status ON skill_registry(status);

-- ============================================================
-- 5. prompt_versions
-- ============================================================
CREATE TABLE prompt_versions (
    prompt_version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id          UUID         NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    prompt_text       TEXT         NOT NULL,
    change_summary    TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by        VARCHAR(255),
    is_active         BOOLEAN      NOT NULL DEFAULT false
);

CREATE INDEX idx_prompt_versions_skill ON prompt_versions(skill_id);
CREATE INDEX idx_prompt_versions_active ON prompt_versions(skill_id, is_active) WHERE is_active = true;

-- Now add the FK from skill_registry -> prompt_versions
ALTER TABLE skill_registry
    ADD CONSTRAINT fk_skill_active_prompt
    FOREIGN KEY (active_prompt_version_id)
    REFERENCES prompt_versions(prompt_version_id)
    ON DELETE SET NULL;

-- ============================================================
-- 6. evaluation_criteria_catalog
-- ============================================================
CREATE TABLE evaluation_criteria_catalog (
    criterion_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id       UUID          NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    criterion_key  VARCHAR(200)  NOT NULL,
    criterion_text TEXT          NOT NULL,
    criterion_type VARCHAR(50)   NOT NULL DEFAULT 'binary',
    is_hard_gate   BOOLEAN       NOT NULL DEFAULT false,
    weight         DECIMAL(5,2)  NOT NULL DEFAULT 1.0 CHECK (weight > 0)
);

CREATE INDEX idx_eval_criteria_skill ON evaluation_criteria_catalog(skill_id);

ALTER TABLE evaluation_criteria_catalog
    ADD CONSTRAINT uq_criterion_per_skill
    UNIQUE (skill_id, criterion_key);

-- ============================================================
-- 7. test_input_registry
-- ============================================================
CREATE TABLE test_input_registry (
    test_input_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id         UUID         NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    input_label      VARCHAR(500) NOT NULL,
    input_text       TEXT         NOT NULL,
    scenario_type    VARCHAR(100),
    source_file_path VARCHAR(500)
);

CREATE INDEX idx_test_inputs_skill ON test_input_registry(skill_id);
CREATE INDEX idx_test_inputs_scenario ON test_input_registry(skill_id, scenario_type);

-- ============================================================
-- 8. evaluation_rounds
-- ============================================================
CREATE TABLE evaluation_rounds (
    round_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id               UUID          NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    prompt_version_id      UUID          NOT NULL REFERENCES prompt_versions(prompt_version_id) ON DELETE CASCADE,
    round_label            VARCHAR(200),
    total_outputs          INTEGER       NOT NULL DEFAULT 0 CHECK (total_outputs >= 0),
    passes                 INTEGER       NOT NULL DEFAULT 0 CHECK (passes >= 0),
    failures               INTEGER       NOT NULL DEFAULT 0 CHECK (failures >= 0),
    score_percent          DECIMAL(5,2)  CHECK (score_percent >= 0 AND score_percent <= 100),
    failure_breakdown_json JSONB         DEFAULT '{}'::jsonb,
    results_log_path       VARCHAR(500),
    analysis_path          VARCHAR(500),
    learnings_path         VARCHAR(500),
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_eval_rounds_skill ON evaluation_rounds(skill_id);
CREATE INDEX idx_eval_rounds_prompt ON evaluation_rounds(prompt_version_id);
CREATE INDEX idx_eval_rounds_created ON evaluation_rounds(created_at DESC);

-- ============================================================
-- 9. evaluation_outputs
-- ============================================================
CREATE TABLE evaluation_outputs (
    output_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id            UUID         NOT NULL REFERENCES evaluation_rounds(round_id) ON DELETE CASCADE,
    test_input_id       UUID         NOT NULL REFERENCES test_input_registry(test_input_id) ON DELETE CASCADE,
    generated_output    TEXT         NOT NULL,
    pass_fail           VARCHAR(10)  NOT NULL CHECK (pass_fail IN ('pass', 'fail')),
    failed_criteria_json JSONB       DEFAULT '[]'::jsonb,
    word_count          INTEGER      DEFAULT 0 CHECK (word_count >= 0)
);

CREATE INDEX idx_eval_outputs_round ON evaluation_outputs(round_id);
CREATE INDEX idx_eval_outputs_test_input ON evaluation_outputs(test_input_id);
CREATE INDEX idx_eval_outputs_pass_fail ON evaluation_outputs(pass_fail);

-- ============================================================
-- 10. gold_example_registry
-- ============================================================
CREATE TABLE gold_example_registry (
    example_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id            UUID          NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    scenario_type       VARCHAR(100),
    evaluation_round_id UUID          REFERENCES evaluation_rounds(round_id) ON DELETE SET NULL,
    output_text         TEXT          NOT NULL,
    score_percent       DECIMAL(5,2)  CHECK (score_percent >= 0 AND score_percent <= 100),
    passed_all_flag     BOOLEAN       NOT NULL DEFAULT false
);

CREATE INDEX idx_gold_examples_skill ON gold_example_registry(skill_id);
CREATE INDEX idx_gold_examples_scenario ON gold_example_registry(skill_id, scenario_type);
CREATE INDEX idx_gold_examples_passed ON gold_example_registry(passed_all_flag) WHERE passed_all_flag = true;

-- ============================================================
-- 11. skill_failure_patterns
-- ============================================================
CREATE TABLE skill_failure_patterns (
    failure_pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id           UUID         NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    criterion_key      VARCHAR(200) NOT NULL,
    scenario_type      VARCHAR(100),
    failure_count      INTEGER      NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    last_seen_at       TIMESTAMPTZ
);

CREATE INDEX idx_failure_patterns_skill ON skill_failure_patterns(skill_id);
CREATE INDEX idx_failure_patterns_count ON skill_failure_patterns(failure_count DESC);

ALTER TABLE skill_failure_patterns
    ADD CONSTRAINT uq_failure_pattern
    UNIQUE (skill_id, criterion_key, scenario_type);


-- ============================================================
-- SEED DATA: 9 Skills
-- ============================================================

INSERT INTO skill_registry (skill_id, skill_name, skill_family, evaluation_file_path, primary_output_type, word_limit_rule, status, owner)
VALUES
    ('a1000000-0000-0000-0000-000000000001', 'agent_system_prompt',   'agent',      'evals/agent_system_prompt.yaml',   'system_prompt',       '{"min": 200, "max": 800}',  'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000002', 'support_agent',         'agent',      'evals/support_agent.yaml',         'agent_response',      '{"min": 50, "max": 500}',   'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000003', 'meeting_summary',       'summarization', 'evals/meeting_summary.yaml',    'summary',             '{"min": 100, "max": 400}',  'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000004', 'cold_email',            'outreach',   'evals/cold_email.yaml',            'email',               '{"min": 50, "max": 250}',   'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000005', 'landing_page_copy',     'copywriting','evals/landing_page_copy.yaml',     'landing_page',        '{"min": 100, "max": 600}',  'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000006', 'newsletter_headline',   'copywriting','evals/newsletter_headline.yaml',   'headline',            '{"min": 5, "max": 20}',     'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000007', 'product_description',   'copywriting','evals/product_description.yaml',   'product_description', '{"min": 50, "max": 300}',   'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000008', 'resume_bullet',         'professional','evals/resume_bullet.yaml',        'bullet_point',        '{"min": 10, "max": 50}',    'active', 'platform-team'),
    ('a1000000-0000-0000-0000-000000000009', 'short_form_script',     'video',      'evals/short_form_script.yaml',     'video_script',        '{"min": 50, "max": 200}',   'active', 'platform-team');


-- ============================================================
-- SEED DATA: Evaluation Criteria (Hard Gates per Skill)
-- ============================================================

-- agent_system_prompt criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000001', 'role_definition',     'Prompt defines a clear agent role and persona',                      'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000001', 'guardrails',          'Prompt includes safety guardrails and boundaries',                   'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000001', 'output_format',       'Prompt specifies expected output format',                            'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000001', 'context_handling',    'Prompt instructs how to handle missing or ambiguous context',        'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000001', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- support_agent criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000002', 'empathy_tone',        'Response opens with empathy and acknowledges the customer issue',    'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000002', 'accurate_resolution', 'Resolution is factually correct and addresses the stated problem',   'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000002', 'no_hallucination',    'Response does not fabricate product features or policies',            'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000002', 'escalation_path',     'Response includes escalation path when unable to resolve',            'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000002', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- meeting_summary criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000003', 'key_decisions',       'Summary captures all key decisions made in the meeting',              'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000003', 'action_items',        'Summary lists action items with owners and deadlines',               'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000003', 'no_fabrication',      'Summary does not include topics not discussed in the meeting',        'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000003', 'conciseness',         'Summary is concise without losing critical information',              'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000003', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- cold_email criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000004', 'personalization',     'Email includes at least one personalized element about the recipient','binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000004', 'clear_cta',           'Email contains a clear and single call-to-action',                   'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000004', 'no_spam_triggers',    'Email avoids spam trigger words and excessive punctuation',           'binary', true,  1.0),
    ('a1000000-0000-0000-0000-000000000004', 'value_proposition',   'Email communicates a compelling value proposition',                   'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000004', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- landing_page_copy criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000005', 'headline_hook',       'Copy leads with a compelling headline that captures attention',       'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000005', 'benefit_focused',     'Copy focuses on benefits rather than features',                      'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000005', 'social_proof',        'Copy includes or references social proof elements',                  'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000005', 'clear_cta',           'Copy ends with a clear call-to-action',                              'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000005', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- newsletter_headline criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000006', 'curiosity_gap',       'Headline creates a curiosity gap that compels opening',              'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000006', 'no_clickbait',        'Headline is not misleading clickbait',                               'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000006', 'topic_relevance',     'Headline accurately reflects the newsletter content',                'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000006', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- product_description criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000007', 'accuracy',            'Description accurately represents the product without exaggeration', 'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000007', 'target_audience',     'Description speaks to the target audience in appropriate language',   'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000007', 'key_features',        'Description covers the most important product features',             'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000007', 'seo_keywords',        'Description naturally incorporates relevant keywords',               'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000007', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- resume_bullet criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000008', 'action_verb',         'Bullet starts with a strong action verb',                            'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000008', 'quantified_impact',   'Bullet includes a quantified impact or measurable result',           'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000008', 'no_first_person',     'Bullet does not use first-person pronouns',                          'binary', true,  1.0),
    ('a1000000-0000-0000-0000-000000000008', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);

-- short_form_script criteria
INSERT INTO evaluation_criteria_catalog (skill_id, criterion_key, criterion_text, criterion_type, is_hard_gate, weight) VALUES
    ('a1000000-0000-0000-0000-000000000009', 'hook_first_3s',       'Script opens with an attention-grabbing hook in the first line',     'binary', true,  2.0),
    ('a1000000-0000-0000-0000-000000000009', 'conversational_tone', 'Script uses natural, conversational language',                       'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000009', 'single_message',      'Script conveys one clear message or takeaway',                       'binary', true,  1.5),
    ('a1000000-0000-0000-0000-000000000009', 'cta_or_punchline',    'Script ends with a CTA or memorable punchline',                      'binary', false, 1.0),
    ('a1000000-0000-0000-0000-000000000009', 'word_limit',          'Output is within the word limit range',                              'binary', true,  1.0);


-- ============================================================
-- Trigger: auto-update updated_at on core_entities
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_core_entities_updated_at
    BEFORE UPDATE ON core_entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

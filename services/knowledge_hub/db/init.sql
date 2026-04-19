-- DreamFi Canonical Database Initialization
-- PostgreSQL 15+
-- Initializes empty schema with 11 core tables

BEGIN;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- ============================================
-- 1. CORE ENTITIES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS core_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner VARCHAR(255),
    status VARCHAR(50),
    source_system VARCHAR(50) NOT NULL,
    source_object_id VARCHAR(255) NOT NULL,
    source_url TEXT,
    last_synced_at TIMESTAMP,
    freshness_score NUMERIC(3,2) CHECK (freshness_score >= 0 AND freshness_score <= 1),
    confidence_score NUMERIC(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    eligible_skill_families_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT eligible_skills_not_null CHECK (eligible_skill_families_json IS NOT NULL),
    UNIQUE(source_system, source_object_id)
);

CREATE INDEX idx_core_entities_source ON core_entities(source_system, source_object_id);
CREATE INDEX idx_core_entities_type ON core_entities(entity_type);
CREATE INDEX idx_core_entities_freshness ON core_entities(freshness_score DESC);
CREATE INDEX idx_core_entities_confidence ON core_entities(confidence_score DESC);
CREATE INDEX idx_core_entities_name_trgm ON core_entities USING GIST (name gist_trgm_ops);

-- ============================================
-- 2. RELATIONSHIPS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    to_entity_id UUID NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    source_system VARCHAR(50) NOT NULL,
    evidence_ref TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_entity_id, relationship_type, to_entity_id)
);

CREATE INDEX idx_relationships_from ON relationships(from_entity_id);
CREATE INDEX idx_relationships_to ON relationships(to_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- ============================================
-- 3. CITATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS citations (
    citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES core_entities(entity_id) ON DELETE CASCADE,
    source_system VARCHAR(50) NOT NULL,
    source_object_id VARCHAR(255) NOT NULL,
    source_snippet TEXT,
    source_url TEXT,
    captured_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_citations_entity ON citations(entity_id);
CREATE INDEX idx_citations_source ON citations(source_system, source_object_id);

-- ============================================
-- 4. SKILL REGISTRY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS skill_registry (
    skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name VARCHAR(255) NOT NULL UNIQUE,
    skill_family VARCHAR(50) NOT NULL,
    evaluation_file_path VARCHAR(255),
    primary_output_type VARCHAR(50),
    word_limit_rule INTEGER,
    active_prompt_version_id UUID,
    status VARCHAR(50),
    owner VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_skill_registry_family ON skill_registry(skill_family);
CREATE INDEX idx_skill_registry_status ON skill_registry(status);

-- ============================================
-- 5. PROMPT VERSIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    prompt_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    change_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_prompt_versions_skill ON prompt_versions(skill_id);
CREATE INDEX idx_prompt_versions_active ON prompt_versions(skill_id, is_active);

-- ============================================
-- 6. EVALUATION CRITERIA CATALOG
-- ============================================
CREATE TABLE IF NOT EXISTS evaluation_criteria_catalog (
    criterion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    criterion_key VARCHAR(255) NOT NULL,
    criterion_text TEXT NOT NULL,
    criterion_type VARCHAR(50),
    is_hard_gate BOOLEAN DEFAULT FALSE,
    weight NUMERIC(3,2) CHECK (weight >= 0 AND weight <= 1),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(skill_id, criterion_key)
);

CREATE INDEX idx_criteria_skill ON evaluation_criteria_catalog(skill_id);
CREATE INDEX idx_criteria_hard_gate ON evaluation_criteria_catalog(is_hard_gate);

-- ============================================
-- 7. TEST INPUT REGISTRY
-- ============================================
CREATE TABLE IF NOT EXISTS test_input_registry (
    test_input_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    input_label VARCHAR(255),
    input_text TEXT NOT NULL,
    scenario_type VARCHAR(50),
    source_file_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_test_input_skill ON test_input_registry(skill_id);
CREATE INDEX idx_test_input_scenario ON test_input_registry(scenario_type);

-- ============================================
-- 8. EVALUATION ROUNDS
-- ============================================
CREATE TABLE IF NOT EXISTS evaluation_rounds (
    round_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(prompt_version_id) ON DELETE SET NULL,
    round_label VARCHAR(255),
    total_outputs INTEGER,
    passes INTEGER,
    failures INTEGER,
    score_percent NUMERIC(5,2),
    failure_breakdown_json JSONB,
    results_log_path VARCHAR(255),
    analysis_path VARCHAR(255),
    learnings_path VARCHAR(255),
    changelog_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_eval_rounds_skill ON evaluation_rounds(skill_id);
CREATE INDEX idx_eval_rounds_prompt ON evaluation_rounds(prompt_version_id);
CREATE INDEX idx_eval_rounds_score ON evaluation_rounds(score_percent DESC);

-- ============================================
-- 9. EVALUATION OUTPUTS
-- ============================================
CREATE TABLE IF NOT EXISTS evaluation_outputs (
    output_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES evaluation_rounds(round_id) ON DELETE CASCADE,
    test_input_id UUID NOT NULL REFERENCES test_input_registry(test_input_id) ON DELETE SET NULL,
    generated_output TEXT NOT NULL,
    pass_fail BOOLEAN,
    failed_criteria_json JSONB,
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_eval_outputs_round ON evaluation_outputs(round_id);
CREATE INDEX idx_eval_outputs_test_input ON evaluation_outputs(test_input_id);
CREATE INDEX idx_eval_outputs_pass_fail ON evaluation_outputs(pass_fail);

-- ============================================
-- 10. GOLD EXAMPLE REGISTRY
-- ============================================
CREATE TABLE IF NOT EXISTS gold_example_registry (
    example_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    scenario_type VARCHAR(50),
    evaluation_round_id UUID REFERENCES evaluation_rounds(round_id) ON DELETE SET NULL,
    output_text TEXT NOT NULL,
    score_percent NUMERIC(5,2),
    passed_all_flag BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gold_example_skill ON gold_example_registry(skill_id);
CREATE INDEX idx_gold_example_scenario ON gold_example_registry(scenario_type);
CREATE INDEX idx_gold_example_score ON gold_example_registry(score_percent DESC);

-- ============================================
-- 11. SKILL FAILURE PATTERNS
-- ============================================
CREATE TABLE IF NOT EXISTS skill_failure_patterns (
    failure_pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skill_registry(skill_id) ON DELETE CASCADE,
    criterion_key VARCHAR(255),
    scenario_type VARCHAR(50),
    failure_count INTEGER DEFAULT 1,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(skill_id, criterion_key, scenario_type)
);

CREATE INDEX idx_failure_patterns_skill ON skill_failure_patterns(skill_id);
CREATE INDEX idx_failure_patterns_scenario ON skill_failure_patterns(scenario_type);

-- ============================================
-- 12. WATERMARKS (for incremental sync)
-- ============================================
CREATE TABLE IF NOT EXISTS connector_watermarks (
    watermark_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_name VARCHAR(50) NOT NULL UNIQUE,
    last_sync_time TIMESTAMP,
    last_checkpoint VARCHAR(255),
    object_count INTEGER,
    error_count INTEGER,
    status VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_watermarks_connector ON connector_watermarks(connector_name);

-- ============================================
-- TRIGGERS & FUNCTIONS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_core_entities_updated_at
BEFORE UPDATE ON core_entities
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_skill_registry_updated_at
BEFORE UPDATE ON skill_registry
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_gold_example_updated_at
BEFORE UPDATE ON gold_example_registry
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_failure_patterns_updated_at
BEFORE UPDATE ON skill_failure_patterns
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- INITIAL LOGGING
-- ============================================
CREATE TABLE IF NOT EXISTS schema_init_log (
    id SERIAL PRIMARY KEY,
    init_timestamp TIMESTAMP DEFAULT NOW(),
    description VARCHAR(255)
);

INSERT INTO schema_init_log (description)
VALUES ('DreamFi canonical schema initialized - 11 core tables, indexes, triggers');

COMMIT;

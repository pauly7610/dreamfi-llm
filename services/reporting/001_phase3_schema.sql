CREATE TABLE IF NOT EXISTS dragonboat_jira_mappings (
    id UUID PRIMARY KEY,
    dragonboat_initiative_id TEXT NOT NULL,
    jira_epic_key TEXT NOT NULL,
    last_synced_at TIMESTAMP,
    sync_direction TEXT DEFAULT 'bidir',
    conflict_status TEXT DEFAULT 'in_sync',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(dragonboat_initiative_id, jira_epic_key)
);

CREATE TABLE IF NOT EXISTS reporting_metrics (
    id UUID PRIMARY KEY,
    initiative_id TEXT NOT NULL,
    week_of DATE,
    velocity_points INT,
    cycle_time_days FLOAT,
    bug_escape_rate FLOAT,
    defect_density FLOAT,
    on_schedule INT DEFAULT 0,
    blocked_count INT DEFAULT 0,
    health_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(initiative_id, week_of)
);

CREATE TABLE IF NOT EXISTS reporting_alerts (
    id UUID PRIMARY KEY,
    initiative_id TEXT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    first_detected_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_dead_letter (
    id UUID PRIMARY KEY,
    dragonboat_id TEXT,
    jira_key TEXT,
    error_message TEXT,
    sync_attempt_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dragonboat_jira_mappings_dragonboat_id 
    ON dragonboat_jira_mappings(dragonboat_initiative_id);

CREATE INDEX IF NOT EXISTS idx_dragonboat_jira_mappings_jira_key 
    ON dragonboat_jira_mappings(jira_epic_key);

CREATE INDEX IF NOT EXISTS idx_reporting_metrics_initiative_id 
    ON reporting_metrics(initiative_id);

CREATE INDEX IF NOT EXISTS idx_reporting_metrics_week_of 
    ON reporting_metrics(week_of);

CREATE INDEX IF NOT EXISTS idx_reporting_alerts_initiative_id 
    ON reporting_alerts(initiative_id);

CREATE INDEX IF NOT EXISTS idx_reporting_alerts_status 
    ON reporting_alerts(status);

CREATE INDEX IF NOT EXISTS idx_reporting_alerts_alert_type 
    ON reporting_alerts(alert_type);

CREATE INDEX IF NOT EXISTS idx_sync_dead_letter_dragonboat_id 
    ON sync_dead_letter(dragonboat_id);

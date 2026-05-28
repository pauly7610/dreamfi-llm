package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/url"
	"testing"
	"time"

	_ "modernc.org/sqlite"
)

func TestPromptVersionActivationKeepsOneActivePromptPerSkill(t *testing.T) {
	ctx := context.Background()
	db := openTestDB(t)
	repo := New(db, DialectSQLite)
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)

	seedSkill(t, ctx, repo, now)
	if err := repo.CreatePromptVersion(ctx, PromptVersion{
		PromptVersionID: "pv-1",
		SkillID:         "meeting_summary",
		Version:         1,
		Template:        "old",
		SystemPrompt:    "system",
		IsActive:        true,
		CreatedAt:       now,
		ActivatedAt:     &now,
	}); err != nil {
		t.Fatalf("CreatePromptVersion old error = %v", err)
	}
	if err := repo.CreatePromptVersion(ctx, PromptVersion{
		PromptVersionID: "pv-2",
		SkillID:         "meeting_summary",
		Version:         2,
		Template:        "new",
		SystemPrompt:    "system",
		CreatedAt:       now,
	}); err != nil {
		t.Fatalf("CreatePromptVersion new error = %v", err)
	}

	if err := repo.ActivatePromptVersion(ctx, "pv-2", now.Add(time.Hour)); err != nil {
		t.Fatalf("ActivatePromptVersion error = %v", err)
	}

	active, err := repo.ActivePromptVersion(ctx, "meeting_summary")
	if err != nil {
		t.Fatalf("ActivePromptVersion error = %v", err)
	}
	if active.PromptVersionID != "pv-2" {
		t.Fatalf("active prompt = %q, want pv-2", active.PromptVersionID)
	}

	var activeCount int
	if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM prompt_versions WHERE skill_id = ? AND is_active = true", "meeting_summary").Scan(&activeCount); err != nil {
		t.Fatalf("count active error = %v", err)
	}
	if activeCount != 1 {
		t.Fatalf("activeCount = %d, want 1", activeCount)
	}
}

func TestEvalOutputAndPublishLogPersistTrueRoundPath(t *testing.T) {
	ctx := context.Background()
	db := openTestDB(t)
	repo := New(db, DialectSQLite)
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
	score := 0.91
	confidence := 0.82
	ref := "artifact://weekly-brief"

	seedSkillAndPrompt(t, ctx, repo, now)
	if err := repo.CreateEvalRound(ctx, EvalRound{
		RoundID:          "round-1",
		SkillID:          "meeting_summary",
		PromptVersionID:  "pv-1",
		NInputs:          1,
		NOutputsPerInput: 1,
		TotalOutputs:     1,
		TotalPasses:      1,
		Score:            score,
		StartedAt:        now,
		ArtifactsPath:    "evals/results/meeting_summary/rounds/round-1",
	}); err != nil {
		t.Fatalf("CreateEvalRound error = %v", err)
	}
	if err := repo.CreateEvalOutput(ctx, EvalOutput{
		OutputID:        "output-1",
		RoundID:         "round-1",
		TestInputLabel:  "input-a",
		Attempt:         1,
		GeneratedText:   "Grounded answer",
		Criteria:        map[string]any{"grounded": true},
		PassFail:        "pass",
		OnyxCitations:   map[string]string{"1": "doc-1"},
		FreshnessScore:  &score,
		Confidence:      &confidence,
		ExportReadiness: &confidence,
		ExportBreakdown: map[string]float64{"confidence": confidence},
		CreatedAt:       now,
	}); err != nil {
		t.Fatalf("CreateEvalOutput error = %v", err)
	}
	if err := repo.CreatePublishLog(ctx, PublishLog{
		PublishID:       "publish-1",
		SkillID:         "meeting_summary",
		PromptVersionID: "pv-1",
		OutputID:        "output-1",
		Destination:     "return-only",
		DestinationRef:  &ref,
		Decision:        "allowed",
		CreatedAt:       now,
	}); err != nil {
		t.Fatalf("CreatePublishLog error = %v", err)
	}

	var citationsRaw string
	if err := db.QueryRowContext(ctx, "SELECT onyx_citations_json FROM eval_outputs WHERE output_id = ?", "output-1").Scan(&citationsRaw); err != nil {
		t.Fatalf("select output error = %v", err)
	}
	var citations map[string]string
	if err := json.Unmarshal([]byte(citationsRaw), &citations); err != nil {
		t.Fatalf("citations JSON error = %v", err)
	}
	if citations["1"] != "doc-1" {
		t.Fatalf("citations = %#v", citations)
	}

	var decision string
	if err := db.QueryRowContext(ctx, "SELECT decision FROM publish_log WHERE publish_id = ?", "publish-1").Scan(&decision); err != nil {
		t.Fatalf("select publish error = %v", err)
	}
	if decision != "allowed" {
		t.Fatalf("decision = %q", decision)
	}
}

func TestConnectorAuditAndLearningTablesPersistReviewLoop(t *testing.T) {
	ctx := context.Background()
	db := openTestDB(t)
	repo := New(db, DialectSQLite)
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
	docSetID := int64(77)
	docSetName := "dreamfi-source-metabase"
	status := "fresh"
	actor := "reviewer@dreamfi.com"

	seedSkillAndPrompt(t, ctx, repo, now)
	seedRoundAndOutput(t, ctx, repo, now)

	if err := repo.UpsertConnectorSetting(ctx, ConnectorSetting{
		ConnectorID:        "metabase",
		Provider:           "metabase",
		CredentialStatus:   "present",
		ValidationStatus:   "valid",
		ActivationStatus:   "active",
		DocumentSetID:      &docSetID,
		DocumentSetName:    &docSetName,
		RetrievalStatus:    &status,
		FreshestDocumentAt: &now,
		Config:             map[string]any{"base_url": "http://metabase.test"},
		Metadata:           map[string]any{"owner": "analytics"},
		CreatedAt:          now,
		UpdatedAt:          now,
	}); err != nil {
		t.Fatalf("UpsertConnectorSetting error = %v", err)
	}
	if err := repo.CreateAuditEvent(ctx, AuditEvent{
		EventID:   "audit-1",
		EventHash: "hash",
		EventType: "access.onyx_search",
		Category:  "access",
		Action:    "onyx_search",
		Outcome:   "success",
		Severity:  "info",
		ActorID:   &actor,
		ActorType: "user",
		Metadata:  map[string]any{"query_hash": "abc"},
		CreatedAt: now,
	}); err != nil {
		t.Fatalf("CreateAuditEvent error = %v", err)
	}
	if err := repo.CreateArtifactFeedback(ctx, ArtifactFeedback{
		FeedbackID:    "feedback-1",
		OutputID:      "output-1",
		ReviewerID:    actor,
		Outcome:       "approved",
		FinalTextHash: "final-hash",
		Metadata:      map[string]any{"workflow_slug": "weekly-brief"},
		CreatedAt:     now,
	}); err != nil {
		t.Fatalf("CreateArtifactFeedback error = %v", err)
	}
	if err := repo.CreateLearningProposal(ctx, LearningProposal{
		ProposalID:          "proposal-1",
		SkillID:             "meeting_summary",
		PromptVersionID:     ptr("pv-1"),
		ClusterKey:          "workflow:weekly-brief",
		Title:               "Tighten evidence",
		Rationale:           "Repeated review feedback",
		ProposedPromptPatch: "Add stronger source requirements",
		Status:              "draft",
		SourceFailureCount:  2,
		Evidence:            map[string]any{"feedback_ids": []string{"feedback-1"}},
		CreatedAt:           now,
	}); err != nil {
		t.Fatalf("CreateLearningProposal error = %v", err)
	}
	if err := repo.CreateReplaySchedule(ctx, ReplaySchedule{
		ScheduleID:  "schedule-1",
		ReplayType:  "gold",
		SkillID:     ptr("meeting_summary"),
		CadenceDays: 7,
		NextRunAt:   now.Add(24 * time.Hour),
		IsActive:    true,
		CreatedBy:   &actor,
		Payload:     map[string]any{"limit": 10},
		CreatedAt:   now,
	}); err != nil {
		t.Fatalf("CreateReplaySchedule error = %v", err)
	}

	for _, table := range []string{"connector_settings", "audit_events", "artifact_feedback", "learning_proposals", "replay_schedules"} {
		var count int
		if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM "+table).Scan(&count); err != nil {
			t.Fatalf("count %s error = %v", table, err)
		}
		if count != 1 {
			t.Fatalf("%s count = %d, want 1", table, count)
		}
	}
}

func TestConnectorSyncRunAndDocumentPersistenceTrackChangedContent(t *testing.T) {
	ctx := context.Background()
	db := openTestDB(t)
	repo := New(db, DialectSQLite)
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
	sourceURL := "http://metabase.test/card/10"
	syncRunID := "sync-1"
	onyxID := "onyx-doc-1"

	if err := repo.UpsertConnectorSetting(ctx, ConnectorSetting{
		ConnectorID:      "metabase",
		Provider:         "metabase",
		CredentialStatus: "present",
		ValidationStatus: "valid",
		ActivationStatus: "active",
		Config:           map[string]any{"base_url": "http://metabase.test"},
		Metadata:         map[string]any{},
		CreatedAt:        now,
		UpdatedAt:        now,
	}); err != nil {
		t.Fatalf("UpsertConnectorSetting error = %v", err)
	}
	if err := repo.CreateConnectorSyncRun(ctx, ConnectorSyncRun{
		SyncRunID:   syncRunID,
		ConnectorID: "metabase",
		Status:      "running",
		Trigger:     "manual",
		StartedAt:   now,
	}); err != nil {
		t.Fatalf("CreateConnectorSyncRun error = %v", err)
	}

	changed, err := repo.UpsertConnectorDocument(ctx, ConnectorDocument{
		ConnectorDocumentID: "doc-row-1",
		ConnectorID:         "metabase",
		ExternalID:          "card:10",
		Title:               "KYC conversion",
		BodyText:            "KYC conversion dashboard",
		SourceURL:           &sourceURL,
		DocUpdatedAt:        now,
		ContentHash:         "hash-a",
		Metadata:            map[string]any{"dreamfi_scope": map[string]any{"source_ids": []string{"metabase"}}},
		SyncRunID:           &syncRunID,
		OnyxDocumentID:      &onyxID,
		LastSeenAt:          now,
		CreatedAt:           now,
		UpdatedAt:           now,
	})
	if err != nil {
		t.Fatalf("UpsertConnectorDocument insert error = %v", err)
	}
	if !changed {
		t.Fatalf("first connector document upsert should be changed")
	}
	if err := repo.MarkConnectorDocumentIngested(ctx, "metabase", "card:10", onyxID, now); err != nil {
		t.Fatalf("MarkConnectorDocumentIngested error = %v", err)
	}

	changed, err = repo.UpsertConnectorDocument(ctx, ConnectorDocument{
		ConnectorDocumentID: "doc-row-1",
		ConnectorID:         "metabase",
		ExternalID:          "card:10",
		Title:               "KYC conversion",
		BodyText:            "KYC conversion dashboard",
		SourceURL:           &sourceURL,
		DocUpdatedAt:        now,
		ContentHash:         "hash-a",
		Metadata:            map[string]any{},
		SyncRunID:           &syncRunID,
		LastSeenAt:          now,
		CreatedAt:           now,
		UpdatedAt:           now,
	})
	if err != nil {
		t.Fatalf("UpsertConnectorDocument unchanged error = %v", err)
	}
	if changed {
		t.Fatalf("same content hash should not require ingestion")
	}

	completed := now.Add(time.Minute)
	if err := repo.FinishConnectorSyncRun(ctx, ConnectorSyncRun{
		SyncRunID:      syncRunID,
		ConnectorID:    "metabase",
		Status:         "success",
		Trigger:        "manual",
		PulledCount:    1,
		PersistedCount: 1,
		IngestedCount:  1,
		StartedAt:      now,
		CompletedAt:    &completed,
	}); err != nil {
		t.Fatalf("FinishConnectorSyncRun error = %v", err)
	}

	var status string
	var ingestedCount int
	if err := db.QueryRowContext(ctx, "SELECT status, ingested_count FROM connector_sync_runs WHERE sync_run_id = ?", syncRunID).Scan(&status, &ingestedCount); err != nil {
		t.Fatalf("select sync run error = %v", err)
	}
	if status != "success" || ingestedCount != 1 {
		t.Fatalf("sync run = (%s, %d), want success/1", status, ingestedCount)
	}
}

func openTestDB(t *testing.T) *sql.DB {
	t.Helper()
	dsn := "file:" + url.QueryEscape(t.Name()) + "?mode=memory&cache=shared"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		t.Fatalf("sql.Open error = %v", err)
	}
	t.Cleanup(func() {
		_ = db.Close()
	})
	for _, stmt := range testSchema {
		if _, err := db.Exec(stmt); err != nil {
			t.Fatalf("schema error: %v\n%s", err, stmt)
		}
	}
	return db
}

func seedSkill(t *testing.T, ctx context.Context, repo *Store, now time.Time) {
	t.Helper()
	if err := repo.UpsertSkill(ctx, Skill{
		SkillID:          "meeting_summary",
		DisplayName:      "Meeting Summary",
		Description:      "Summarize meetings",
		EvalTemplatePath: "evals/meeting_summary.md",
		EvalRunnerPath:   "evals/runners/run_meeting_summary_eval.py",
		Criteria:         map[string]string{"grounded": "required"},
		CreatedAt:        now,
	}); err != nil {
		t.Fatalf("UpsertSkill error = %v", err)
	}
}

func seedSkillAndPrompt(t *testing.T, ctx context.Context, repo *Store, now time.Time) {
	t.Helper()
	seedSkill(t, ctx, repo, now)
	if err := repo.CreatePromptVersion(ctx, PromptVersion{
		PromptVersionID: "pv-1",
		SkillID:         "meeting_summary",
		Version:         1,
		Template:        "template",
		SystemPrompt:    "system",
		IsActive:        true,
		CreatedAt:       now,
		ActivatedAt:     &now,
	}); err != nil {
		t.Fatalf("CreatePromptVersion error = %v", err)
	}
}

func seedRoundAndOutput(t *testing.T, ctx context.Context, repo *Store, now time.Time) {
	t.Helper()
	if err := repo.CreateEvalRound(ctx, EvalRound{
		RoundID:          "round-1",
		SkillID:          "meeting_summary",
		PromptVersionID:  "pv-1",
		NInputs:          1,
		NOutputsPerInput: 1,
		TotalOutputs:     1,
		TotalPasses:      1,
		Score:            1,
		StartedAt:        now,
		ArtifactsPath:    "evals/results/meeting_summary/rounds/round-1",
	}); err != nil {
		t.Fatalf("CreateEvalRound error = %v", err)
	}
	if err := repo.CreateEvalOutput(ctx, EvalOutput{
		OutputID:       "output-1",
		RoundID:        "round-1",
		TestInputLabel: "input-a",
		Attempt:        1,
		GeneratedText:  "Grounded answer",
		Criteria:       map[string]any{"grounded": true},
		PassFail:       "pass",
		OnyxCitations:  map[string]string{"1": "doc-1"},
		CreatedAt:      now,
	}); err != nil {
		t.Fatalf("CreateEvalOutput error = %v", err)
	}
}

func ptr(value string) *string {
	return &value
}

var testSchema = []string{
	`CREATE TABLE skills (
		skill_id TEXT PRIMARY KEY,
		display_name TEXT NOT NULL,
		description TEXT NOT NULL,
		eval_template_path TEXT NOT NULL,
		eval_runner_path TEXT NOT NULL,
		criteria_json TEXT NOT NULL,
		onyx_persona_id INTEGER,
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE prompt_versions (
		prompt_version_id TEXT PRIMARY KEY,
		skill_id TEXT NOT NULL REFERENCES skills(skill_id),
		version INTEGER NOT NULL,
		template TEXT NOT NULL,
		system_prompt TEXT NOT NULL,
		is_active BOOLEAN NOT NULL DEFAULT false,
		parent_version_id TEXT,
		created_at DATETIME NOT NULL,
		activated_at DATETIME,
		deactivated_at DATETIME,
		UNIQUE(skill_id, version)
	)`,
	`CREATE UNIQUE INDEX ix_prompt_versions_one_active_per_skill
		ON prompt_versions(skill_id)
		WHERE is_active = true`,
	`CREATE TABLE eval_rounds (
		round_id TEXT PRIMARY KEY,
		skill_id TEXT NOT NULL REFERENCES skills(skill_id),
		prompt_version_id TEXT NOT NULL REFERENCES prompt_versions(prompt_version_id),
		n_inputs INTEGER NOT NULL,
		n_outputs_per_input INTEGER NOT NULL,
		total_outputs INTEGER NOT NULL,
		total_passes INTEGER NOT NULL,
		score REAL NOT NULL,
		previous_score REAL,
		improvement REAL,
		started_at DATETIME NOT NULL,
		completed_at DATETIME,
		artifacts_path TEXT NOT NULL
	)`,
	`CREATE TABLE eval_outputs (
		output_id TEXT PRIMARY KEY,
		round_id TEXT NOT NULL REFERENCES eval_rounds(round_id),
		test_input_label TEXT NOT NULL,
		attempt INTEGER NOT NULL,
		generated_text TEXT NOT NULL,
		criteria_json TEXT NOT NULL,
		pass_fail TEXT NOT NULL,
		onyx_chat_session_id TEXT,
		onyx_message_id INTEGER,
		onyx_citations_json TEXT,
		freshness_score REAL,
		confidence REAL,
		export_readiness REAL,
		export_breakdown_json TEXT,
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE publish_log (
		publish_id TEXT PRIMARY KEY,
		skill_id TEXT NOT NULL REFERENCES skills(skill_id),
		prompt_version_id TEXT NOT NULL REFERENCES prompt_versions(prompt_version_id),
		output_id TEXT NOT NULL REFERENCES eval_outputs(output_id),
		destination TEXT NOT NULL,
		destination_ref TEXT,
		decision TEXT NOT NULL,
		reason TEXT,
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE connector_settings (
		connector_id TEXT PRIMARY KEY,
		provider TEXT NOT NULL,
		credential_status TEXT NOT NULL DEFAULT 'missing',
		config_json TEXT NOT NULL DEFAULT '{}',
		validation_status TEXT NOT NULL DEFAULT 'not_validated',
		document_set_id INTEGER,
		document_set_name TEXT,
		retrieval_status TEXT,
		freshest_document_at DATETIME,
		activation_status TEXT NOT NULL DEFAULT 'inactive',
		metadata_json TEXT NOT NULL DEFAULT '{}',
		created_at DATETIME NOT NULL,
		updated_at DATETIME NOT NULL
	)`,
	`CREATE TABLE connector_sync_runs (
		sync_run_id TEXT PRIMARY KEY,
		connector_id TEXT NOT NULL REFERENCES connector_settings(connector_id),
		status TEXT NOT NULL,
		trigger TEXT NOT NULL DEFAULT 'manual',
		pulled_count INTEGER NOT NULL DEFAULT 0,
		persisted_count INTEGER NOT NULL DEFAULT 0,
		ingested_count INTEGER NOT NULL DEFAULT 0,
		skipped_count INTEGER NOT NULL DEFAULT 0,
		error_count INTEGER NOT NULL DEFAULT 0,
		cursor_json TEXT NOT NULL DEFAULT '{}',
		metadata_json TEXT NOT NULL DEFAULT '{}',
		reason TEXT,
		started_at DATETIME NOT NULL,
		completed_at DATETIME
	)`,
	`CREATE TABLE connector_documents (
		connector_document_id TEXT PRIMARY KEY,
		connector_id TEXT NOT NULL REFERENCES connector_settings(connector_id),
		external_id TEXT NOT NULL,
		title TEXT NOT NULL,
		body_text TEXT NOT NULL,
		source_url TEXT,
		doc_updated_at DATETIME NOT NULL,
		content_hash TEXT NOT NULL,
		metadata_json TEXT NOT NULL DEFAULT '{}',
		sync_run_id TEXT,
		onyx_document_id TEXT,
		last_seen_at DATETIME NOT NULL,
		last_ingested_at DATETIME,
		created_at DATETIME NOT NULL,
		updated_at DATETIME NOT NULL,
		UNIQUE(connector_id, external_id)
	)`,
	`CREATE TABLE audit_events (
		event_id TEXT PRIMARY KEY,
		event_hash TEXT NOT NULL,
		event_type TEXT NOT NULL,
		category TEXT NOT NULL,
		action TEXT NOT NULL,
		outcome TEXT NOT NULL,
		severity TEXT NOT NULL DEFAULT 'info',
		actor_id TEXT,
		actor_type TEXT NOT NULL DEFAULT 'anonymous',
		auth_method TEXT,
		request_id TEXT,
		http_method TEXT,
		path TEXT,
		status_code INTEGER,
		target_type TEXT,
		target_id TEXT,
		reason TEXT,
		metadata_json TEXT NOT NULL DEFAULT '{}',
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE artifact_feedback (
		feedback_id TEXT PRIMARY KEY,
		output_id TEXT NOT NULL REFERENCES eval_outputs(output_id),
		reviewer_id TEXT NOT NULL,
		outcome TEXT NOT NULL,
		reason TEXT,
		notes TEXT,
		final_text_hash TEXT NOT NULL,
		metadata_json TEXT NOT NULL DEFAULT '{}',
		gold_id TEXT,
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE learning_proposals (
		proposal_id TEXT PRIMARY KEY,
		skill_id TEXT NOT NULL REFERENCES skills(skill_id),
		prompt_version_id TEXT,
		cluster_key TEXT NOT NULL,
		title TEXT NOT NULL,
		rationale TEXT NOT NULL,
		proposed_prompt_patch TEXT NOT NULL,
		status TEXT NOT NULL DEFAULT 'draft',
		source_failure_count INTEGER NOT NULL DEFAULT 0,
		evidence_json TEXT NOT NULL DEFAULT '{}',
		reviewer_id TEXT,
		review_notes TEXT,
		reviewed_at DATETIME,
		created_prompt_version_id TEXT,
		created_at DATETIME NOT NULL
	)`,
	`CREATE TABLE replay_schedules (
		schedule_id TEXT PRIMARY KEY,
		replay_type TEXT NOT NULL,
		skill_id TEXT,
		prompt_version_id TEXT,
		cadence_days INTEGER NOT NULL,
		next_run_at DATETIME NOT NULL,
		last_run_at DATETIME,
		is_active BOOLEAN NOT NULL DEFAULT true,
		created_by TEXT,
		payload_json TEXT NOT NULL DEFAULT '{}',
		created_at DATETIME NOT NULL
	)`,
}

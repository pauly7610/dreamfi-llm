package httpapi

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
	_ "modernc.org/sqlite"
)

func TestAskSearchesOnyxWithScopeAndAudits(t *testing.T) {
	ctx := context.Background()
	db := openWorkflowTestDB(t)
	repo := store.New(db, store.DialectSQLite)

	var searchPayload map[string]any
	onyxServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/admin/search" {
			t.Fatalf("unexpected Onyx path %s", r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&searchPayload); err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		writeWorkflowJSON(t, w, map[string]any{
			"documents": []map[string]any{
				{
					"document_id":         "doc-1",
					"semantic_identifier": "KYC funnel report",
					"blurb":               "KYC completion moved after retry policy changes.",
					"score":               0.92,
					"link":                "https://dreamfi.test/doc-1",
					"updated_at":          "2026-04-28T00:00:00Z",
				},
			},
		})
	}))
	defer onyxServer.Close()

	router := NewRouter(
		workflowTestSettings(),
		onyx.NewClient(onyxServer.URL, "k", onyx.WithRetryWait(0)),
		WithStore(repo),
		WithNow(fixedWorkflowNow),
	)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/ask", strings.NewReader(`{
		"question": "Why did KYC conversion move?",
		"topic_id": "kyc-conversion",
		"source_id": "socure"
	}`))
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var body askResponse
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if body.Confidence <= 0 {
		t.Fatalf("confidence = %f", body.Confidence)
	}
	if len(body.Citations) != 1 || body.Citations[0].DocumentID != "doc-1" {
		t.Fatalf("citations = %#v", body.Citations)
	}
	if !strings.Contains(body.Answer, "KYC funnel report") {
		t.Fatalf("answer = %q", body.Answer)
	}
	scope := searchPayload["filters"].(map[string]any)["dreamfi_scope"].(map[string]any)
	if scope["topic_id"] != "kyc-conversion" {
		t.Fatalf("topic scope = %#v", scope)
	}
	sourceIDs := scope["source_ids"].([]any)
	if len(sourceIDs) != 1 || sourceIDs[0] != "socure" {
		t.Fatalf("source scope = %#v", sourceIDs)
	}

	var auditCount int
	if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM audit_events WHERE action = 'onyx_search' AND outcome = 'success'").Scan(&auditCount); err != nil {
		t.Fatalf("audit count error = %v", err)
	}
	if auditCount != 1 {
		t.Fatalf("auditCount = %d, want 1", auditCount)
	}
}

func TestGenerateWorkflowPersistsArtifactWithReadiness(t *testing.T) {
	db := openWorkflowTestDB(t)
	repo := store.New(db, store.DialectSQLite)
	seedWorkflowSkill(t, context.Background(), repo, "support_agent", 100)

	stream := `{"answer_piece":"# Risk context\nKYC retry risk increased.\n# Evidence\nSocure retry logs cite elevated queue risk.\n# Policy decision\nHold launch until monitored controls pass.\n# Controls\nKeep manual review and escalation controls active.\n# Open questions\nNone for this scoped artifact.\n# Review checklist\n- Source claims checked against cited evidence.\n- Scope matches the requested Socure policy question.\n"}
{"citations":{"1":"doc-1","2":"doc-2","3":"doc-3"}}
{"documents":[{"id":"d1","updated_at":"2026-04-28T00:00:00Z"}]}
{"message_id":77}
`
	router := workflowGenerationRouter(t, repo, stream)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/workflows/generate", strings.NewReader(`{
		"workflow_slug": "risk-brd",
		"question": "Should we change KYC retry policy?",
		"topic_id": "kyc-conversion",
		"source_id": "socure"
	}`))
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var body generateArtifactResponse
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if body.PassFail != "pass" {
		t.Fatalf("pass_fail = %q", body.PassFail)
	}
	if body.ExportReadiness <= 0 {
		t.Fatalf("export_readiness = %f", body.ExportReadiness)
	}
	if body.DestinationHref != "/console/review?focus="+body.OutputID {
		t.Fatalf("destination_href = %q", body.DestinationHref)
	}

	var passFail string
	var criteriaRaw string
	var readiness float64
	if err := db.QueryRow("SELECT pass_fail, criteria_json, export_readiness FROM eval_outputs WHERE output_id = ?", body.OutputID).Scan(&passFail, &criteriaRaw, &readiness); err != nil {
		t.Fatalf("select output error = %v", err)
	}
	if passFail != "pass" || readiness <= 0 {
		t.Fatalf("persisted output = (%s, %f)", passFail, readiness)
	}
	var criteria map[string]any
	if err := json.Unmarshal([]byte(criteriaRaw), &criteria); err != nil {
		t.Fatalf("criteria JSON error = %v", err)
	}
	if criteria["workflow_title"] != "Risk BRD" || criteria["has_required_sections"] != true {
		t.Fatalf("criteria = %#v", criteria)
	}

	var promptCount int
	if err := db.QueryRow("SELECT COUNT(*) FROM prompt_versions WHERE skill_id = 'support_agent' AND is_active = true").Scan(&promptCount); err != nil {
		t.Fatalf("prompt count error = %v", err)
	}
	if promptCount != 1 {
		t.Fatalf("promptCount = %d, want 1", promptCount)
	}
}

func TestGenerateWorkflowBlocksThinArtifact(t *testing.T) {
	db := openWorkflowTestDB(t)
	repo := store.New(db, store.DialectSQLite)
	seedWorkflowSkill(t, context.Background(), repo, "support_agent", 100)

	stream := `{"answer_piece":"# Risk context\nKYC moved.\n# Evidence\nSocure retry logs.\n# Policy decision\nHold launch.\n"}
{"citations":{"1":"doc-1"}}
{"documents":[{"id":"d1","updated_at":"2026-04-28T00:00:00Z"}]}
{"message_id":78}
`
	router := workflowGenerationRouter(t, repo, stream)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/workflows/generate", strings.NewReader(`{
		"workflow_slug": "risk-brd",
		"question": "Should we change KYC retry policy?",
		"topic_id": "kyc-conversion",
		"source_id": "socure"
	}`))
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var body generateArtifactResponse
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if body.PassFail != "fail" || body.ExportReadiness != 0 {
		t.Fatalf("body = %#v", body)
	}
	var criteriaRaw string
	if err := db.QueryRow("SELECT criteria_json FROM eval_outputs WHERE output_id = ?", body.OutputID).Scan(&criteriaRaw); err != nil {
		t.Fatalf("select output error = %v", err)
	}
	var criteria map[string]any
	if err := json.Unmarshal([]byte(criteriaRaw), &criteria); err != nil {
		t.Fatalf("criteria JSON error = %v", err)
	}
	if criteria["has_required_sections"] != false || criteria["has_review_checklist"] != false {
		t.Fatalf("criteria = %#v", criteria)
	}
}

func workflowGenerationRouter(t *testing.T, repo *store.Store, stream string) http.Handler {
	t.Helper()
	onyxServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/chat/create-chat-session":
			var payload map[string]any
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				t.Fatalf("Decode session payload error = %v", err)
			}
			if payload["persona_id"] != float64(100) {
				t.Fatalf("persona_id = %#v", payload["persona_id"])
			}
			writeWorkflowJSON(t, w, map[string]string{"chat_session_id": "sess-1"})
		case "/api/chat/send-chat-message":
			var payload map[string]any
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				t.Fatalf("Decode message payload error = %v", err)
			}
			message := payload["message"].(string)
			if !strings.Contains(message, "Risk BRD") || !strings.Contains(message, "topic_id=kyc-conversion") {
				t.Fatalf("message = %q", message)
			}
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(stream))
		default:
			t.Fatalf("unexpected Onyx path %s", r.URL.Path)
		}
	}))
	t.Cleanup(onyxServer.Close)

	return NewRouter(
		workflowTestSettings(),
		onyx.NewClient(onyxServer.URL, "k", onyx.WithRetryWait(0)),
		WithStore(repo),
		WithNow(fixedWorkflowNow),
	)
}

func workflowTestSettings() config.Settings {
	return config.Settings{
		AuthEnabled:                 false,
		AuditEnabled:                true,
		AskSearchLimit:              5,
		FreshnessHalflifeDays:       14,
		ClaimLineageTargetCitations: 3,
		WorkflowMinCitations:        1,
		WorkflowMinSectionWords:     3,
		WorkflowRequireScope:        true,
	}
}

func fixedWorkflowNow() time.Time {
	return time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
}

func openWorkflowTestDB(t *testing.T) *sql.DB {
	t.Helper()
	dsn := "file:" + url.QueryEscape(t.Name()) + "?mode=memory&cache=shared"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		t.Fatalf("sql.Open error = %v", err)
	}
	t.Cleanup(func() {
		_ = db.Close()
	})
	for _, stmt := range workflowTestSchema {
		if _, err := db.Exec(stmt); err != nil {
			t.Fatalf("schema error: %v\n%s", err, stmt)
		}
	}
	return db
}

func seedWorkflowSkill(t *testing.T, ctx context.Context, repo *store.Store, skillID string, personaID int64) {
	t.Helper()
	if err := repo.UpsertSkill(ctx, store.Skill{
		SkillID:          skillID,
		DisplayName:      "Support Agent",
		Description:      "Generates support-agent replies with empathy + resolution.",
		EvalTemplatePath: "evals/support-agent.md",
		EvalRunnerPath:   "evals/runners/run_support_agent_eval.py",
		Criteria:         map[string]string{"grounded": "required"},
		OnyxPersonaID:    &personaID,
		CreatedAt:        fixedWorkflowNow(),
	}); err != nil {
		t.Fatalf("UpsertSkill error = %v", err)
	}
}

func writeWorkflowJSON(t *testing.T, w http.ResponseWriter, value any) {
	t.Helper()
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(value); err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
}

var workflowTestSchema = []string{
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
}

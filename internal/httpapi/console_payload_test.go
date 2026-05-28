package httpapi

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/store"
)

func TestConsolePayloadAndTemplUseStoreBackedSummary(t *testing.T) {
	ctx := context.Background()
	db := openWorkflowTestDB(t)
	repo := store.New(db, store.DialectSQLite)
	now := fixedWorkflowNow()
	seedWorkflowSkill(t, ctx, repo, "meeting_summary", 100)
	if err := repo.CreatePromptVersion(ctx, store.PromptVersion{
		PromptVersionID: "pv-1",
		SkillID:         "meeting_summary",
		Version:         1,
		Template:        "meeting_summary.jinja",
		SystemPrompt:    "You write meeting summaries.",
		IsActive:        true,
		CreatedAt:       now,
		ActivatedAt:     &now,
	}); err != nil {
		t.Fatalf("CreatePromptVersion error = %v", err)
	}
	completedAt := now
	if err := repo.CreateEvalRound(ctx, store.EvalRound{
		RoundID:          "round-1",
		SkillID:          "meeting_summary",
		PromptVersionID:  "pv-1",
		NInputs:          2,
		NOutputsPerInput: 1,
		TotalOutputs:     2,
		TotalPasses:      1,
		Score:            0.5,
		StartedAt:        now,
		CompletedAt:      &completedAt,
		ArtifactsPath:    "evals/results/meeting-summary/rounds/round-1",
	}); err != nil {
		t.Fatalf("CreateEvalRound error = %v", err)
	}
	publishedConfidence := 0.91
	publishedReadiness := 0.87
	if err := repo.CreateEvalOutput(ctx, store.EvalOutput{
		OutputID:        "output-published",
		RoundID:         "round-1",
		TestInputLabel:  "weekly-eng-standup",
		Attempt:         1,
		GeneratedText:   "Grounded output",
		Criteria:        map[string]any{"workflow_title": "Weekly PM Brief"},
		PassFail:        "pass",
		Confidence:      &publishedConfidence,
		ExportReadiness: &publishedReadiness,
		CreatedAt:       now,
	}); err != nil {
		t.Fatalf("CreateEvalOutput pass error = %v", err)
	}
	blockedConfidence := 0.42
	blockedReadiness := 0.25
	if err := repo.CreateEvalOutput(ctx, store.EvalOutput{
		OutputID:        "output-blocked",
		RoundID:         "round-1",
		TestInputLabel:  "missing-owner-followup",
		Attempt:         1,
		GeneratedText:   "Ungrounded output",
		Criteria:        map[string]any{"workflow_title": "Weekly PM Brief"},
		PassFail:        "fail",
		Confidence:      &blockedConfidence,
		ExportReadiness: &blockedReadiness,
		CreatedAt:       now.Add(time.Minute),
	}); err != nil {
		t.Fatalf("CreateEvalOutput fail error = %v", err)
	}
	destinationRef := "exec-review"
	if err := repo.CreatePublishLog(ctx, store.PublishLog{
		PublishID:       "publish-1",
		SkillID:         "meeting_summary",
		PromptVersionID: "pv-1",
		OutputID:        "output-published",
		Destination:     "confluence",
		DestinationRef:  &destinationRef,
		Decision:        "published",
		CreatedAt:       now,
	}); err != nil {
		t.Fatalf("CreatePublishLog error = %v", err)
	}

	router := NewRouter(
		config.Settings{AuthEnabled: false},
		nil,
		WithStore(repo),
		WithNow(fixedWorkflowNow),
	)

	apiRec := httptest.NewRecorder()
	router.ServeHTTP(apiRec, httptest.NewRequest(http.MethodGet, "/api/console", nil))
	if apiRec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", apiRec.Code, apiRec.Body.String())
	}
	var payload consolePayload
	if err := json.NewDecoder(apiRec.Body).Decode(&payload); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if payload.Summary.SkillCount != 1 || payload.Summary.ActivePromptCount != 1 {
		t.Fatalf("summary = %#v", payload.Summary)
	}
	if payload.Summary.BlockedArtifactCount != 1 || payload.Summary.PublishedArtifactCount != 1 {
		t.Fatalf("artifact counts = %#v", payload.Summary)
	}
	if payload.Summary.HardGatePassRate == nil || *payload.Summary.HardGatePassRate != 0.5 {
		t.Fatalf("hard gate pass rate = %#v", payload.Summary.HardGatePassRate)
	}

	htmlRec := httptest.NewRecorder()
	router.ServeHTTP(htmlRec, httptest.NewRequest(http.MethodGet, "/console", nil))
	if htmlRec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", htmlRec.Code, htmlRec.Body.String())
	}
	html := htmlRec.Body.String()
	for _, want := range []string{"Trust, measured.", "missing-owner-followup", "weekly-eng-standup", "Run weekly PM brief"} {
		if !strings.Contains(html, want) {
			t.Fatalf("console HTML missing %q: %s", want, html)
		}
	}
}

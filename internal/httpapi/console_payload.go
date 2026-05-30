package httpapi

import (
	"context"
	"database/sql"
	"fmt"
	"math"
	"strconv"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/connectors"
	"github.com/pauly7610/dreamfi-llm/web/templates"
)

type consolePayload struct {
	Status        string               `json:"status"`
	Onyx          string               `json:"onyx"`
	Nav           []templates.NavItem  `json:"nav"`
	Headline      string               `json:"headline"`
	Summary       consoleSummary       `json:"summary"`
	ArtifactQueue []consoleArtifact    `json:"artifact_queue"`
	QuickActions  []consoleQuickAction `json:"quick_actions"`
}

type consoleSummary struct {
	SkillCount             int      `json:"skill_count"`
	ActivePromptCount      int      `json:"active_prompt_count"`
	AverageConfidence      *float64 `json:"average_confidence"`
	AverageExportReadiness *float64 `json:"average_export_readiness"`
	HardGatePassRate       *float64 `json:"hard_gate_pass_rate"`
	BlockedArtifactCount   int      `json:"blocked_artifact_count"`
	PublishReadyCount      int      `json:"publish_ready_count"`
	PublishedArtifactCount int      `json:"published_artifact_count"`
	NeedsReviewCount       int      `json:"needs_review_count"`
}

type consoleArtifact struct {
	OutputID        string   `json:"output_id"`
	RoundID         string   `json:"round_id"`
	TestInputLabel  string   `json:"test_input_label"`
	PassFail        string   `json:"pass_fail"`
	Confidence      *float64 `json:"confidence"`
	ExportReadiness *float64 `json:"export_readiness"`
	Status          string   `json:"status"`
	CreatedAt       string   `json:"created_at"`
}

type consoleQuickAction struct {
	ID    string `json:"id"`
	Label string `json:"label"`
	Href  string `json:"href"`
	Kind  string `json:"kind"`
}

func (s *Server) consolePayload(ctx context.Context, onyxStatus string) (consolePayload, error) {
	payload := consolePayload{
		Status:       "ok",
		Onyx:         onyxStatus,
		Nav:          primaryNav(),
		Headline:     "Trust, measured.",
		QuickActions: consoleQuickActions(),
	}
	if s.store == nil {
		return payload, nil
	}

	db := s.store.DB()
	if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM skills").Scan(&payload.Summary.SkillCount); err != nil {
		return consolePayload{}, err
	}
	if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM prompt_versions WHERE is_active = true").Scan(&payload.Summary.ActivePromptCount); err != nil {
		return consolePayload{}, err
	}
	latestPublish, err := latestPublishDecisions(ctx, db)
	if err != nil {
		return consolePayload{}, err
	}
	artifacts, err := recentConsoleArtifacts(ctx, db, latestPublish)
	if err != nil {
		return consolePayload{}, err
	}
	payload.ArtifactQueue = artifacts
	payload.Summary = summarizeConsoleArtifacts(payload.Summary, artifacts)
	return payload, nil
}

func latestPublishDecisions(ctx context.Context, db *sql.DB) (map[string]string, error) {
	rows, err := db.QueryContext(ctx, `SELECT output_id, decision FROM publish_log ORDER BY created_at DESC LIMIT 100`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	decisions := map[string]string{}
	for rows.Next() {
		var outputID string
		var decision string
		if err := rows.Scan(&outputID, &decision); err != nil {
			return nil, err
		}
		if _, ok := decisions[outputID]; !ok {
			decisions[outputID] = decision
		}
	}
	return decisions, rows.Err()
}

func recentConsoleArtifacts(ctx context.Context, db *sql.DB, latestPublish map[string]string) ([]consoleArtifact, error) {
	rows, err := db.QueryContext(
		ctx,
		`SELECT output_id, round_id, test_input_label, pass_fail, confidence, export_readiness, created_at
		 FROM eval_outputs
		 ORDER BY created_at DESC
		 LIMIT 20`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	artifacts := []consoleArtifact{}
	for rows.Next() {
		var artifact consoleArtifact
		var confidence sql.NullFloat64
		var readiness sql.NullFloat64
		var createdAt time.Time
		if err := rows.Scan(
			&artifact.OutputID,
			&artifact.RoundID,
			&artifact.TestInputLabel,
			&artifact.PassFail,
			&confidence,
			&readiness,
			&createdAt,
		); err != nil {
			return nil, err
		}
		artifact.Confidence = nullableFloat(confidence)
		artifact.ExportReadiness = nullableFloat(readiness)
		artifact.Status = classifyConsoleArtifact(artifact, latestPublish[artifact.OutputID])
		artifact.CreatedAt = createdAt.UTC().Format(time.RFC3339)
		artifacts = append(artifacts, artifact)
	}
	return artifacts, rows.Err()
}

func summarizeConsoleArtifacts(summary consoleSummary, artifacts []consoleArtifact) consoleSummary {
	confidenceValues := []float64{}
	readinessValues := []float64{}
	passCount := 0
	for _, artifact := range artifacts {
		if artifact.Confidence != nil {
			confidenceValues = append(confidenceValues, *artifact.Confidence)
		}
		if artifact.ExportReadiness != nil {
			readinessValues = append(readinessValues, *artifact.ExportReadiness)
		}
		if artifact.PassFail == "pass" {
			passCount++
		}
		switch artifact.Status {
		case "blocked":
			summary.BlockedArtifactCount++
		case "publish_ready":
			summary.PublishReadyCount++
		case "published":
			summary.PublishedArtifactCount++
		case "needs_review":
			summary.NeedsReviewCount++
		}
	}
	summary.AverageConfidence = averageOrNil(confidenceValues)
	summary.AverageExportReadiness = averageOrNil(readinessValues)
	if len(artifacts) > 0 {
		value := round3(float64(passCount) / float64(len(artifacts)))
		summary.HardGatePassRate = &value
	}
	return summary
}

func classifyConsoleArtifact(artifact consoleArtifact, latestPublishDecision string) string {
	if latestPublishDecision == "published" {
		return "published"
	}
	if artifact.PassFail != "pass" {
		return "blocked"
	}
	if artifact.ExportReadiness != nil && *artifact.ExportReadiness >= 0.8 {
		return "publish_ready"
	}
	return "needs_review"
}

func consoleTemplateData(payload consolePayload, currentPath string) templates.ConsoleData {
	queue := consoleTemplateQueue(payload.ArtifactQueue)
	return templates.ConsoleData{
		ProductName: "DreamFi ProductOS",
		Version:     "v0.4",
		CurrentPath: currentPath,
		Headline:    payload.Headline,
		Status:      payload.Onyx,
		PrimaryNav:  payload.Nav,
		TopicRooms:  consoleTemplateTopics(),
		Sources:     consoleTemplateSources(),
		Metrics: []templates.ConsoleMetric{
			{Label: "Skills", Value: strconv.Itoa(payload.Summary.SkillCount), Detail: fmt.Sprintf("%d active prompts", payload.Summary.ActivePromptCount), Tone: "neutral"},
			{Label: "Blocked", Value: strconv.Itoa(payload.Summary.BlockedArtifactCount), Detail: "Hard gates need review", Tone: "warning"},
			{Label: "Ready", Value: strconv.Itoa(payload.Summary.PublishReadyCount), Detail: "Artifacts near publish", Tone: "success"},
			{Label: "Confidence", Value: formatPercent(payload.Summary.AverageConfidence), Detail: "Recent artifacts", Tone: "neutral"},
			{Label: "Export", Value: formatPercent(payload.Summary.AverageExportReadiness), Detail: "Readiness average", Tone: "neutral"},
			{Label: "Hard Gate", Value: formatPercent(payload.Summary.HardGatePassRate), Detail: "Pass rate", Tone: "neutral"},
		},
		Queue:       queue,
		Actions:     consoleTemplateActions(payload.QuickActions),
		PromptChips: consolePromptChips(),
		Threads:     consoleTemplateThreads(queue),
		TopicPulse:  consoleTopicPulse(),
	}
}

func consoleTemplateQueue(artifacts []consoleArtifact) []templates.ConsoleQueueItem {
	queue := make([]templates.ConsoleQueueItem, 0, minInt(len(artifacts), 6))
	for _, artifact := range artifacts {
		if len(queue) == 6 {
			break
		}
		queue = append(queue, templates.ConsoleQueueItem{
			Title:  artifact.TestInputLabel,
			Detail: fmt.Sprintf("confidence %s, export %s", formatPercent(artifact.Confidence), formatPercent(artifact.ExportReadiness)),
			Status: artifact.Status,
			Href:   "/console/review?focus=" + artifact.OutputID,
		})
	}
	return queue
}

func consoleTemplateActions(actions []consoleQuickAction) []templates.ConsoleAction {
	out := make([]templates.ConsoleAction, 0, len(actions))
	for _, action := range actions {
		out = append(out, templates.ConsoleAction{
			Label: action.Label,
			Href:  action.Href,
			Kind:  action.Kind,
		})
	}
	return out
}

func consoleQuickActions() []consoleQuickAction {
	return []consoleQuickAction{
		{ID: "weekly-brief", Label: "Run weekly PM brief", Href: "/console/generate/weekly-brief", Kind: "primary"},
		{ID: "technical-prd", Label: "Create Technical PRD", Href: "/console/generate/technical-prd", Kind: "secondary"},
		{ID: "business-prd", Label: "Create Business PRD", Href: "/console/generate/business-prd", Kind: "secondary"},
		{ID: "risk-brd", Label: "Create Risk BRD", Href: "/console/generate/risk-brd", Kind: "secondary"},
		{ID: "review-blocked", Label: "Review blocked artifacts", Href: "/console/review?status=blocked", Kind: "secondary"},
		{ID: "trust-dashboard", Label: "Open trust dashboard", Href: "/console/trust", Kind: "secondary"},
	}
}

func consoleTemplateTopics() []templates.ConsoleTopic {
	return []templates.ConsoleTopic{
		{ID: "kyc-conversion", Title: "KYC conversion", Question: "Why did KYC conversion drop 4.2 pts?", Status: "Decision pending", Freshness: "4m", Dot: "warn", Change: "-4.2 pts"},
		{ID: "onboarding", Title: "Onboarding", Question: "Where is onboarding completion weakest?", Status: "Ready to publish", Freshness: "1h", Dot: "good", Change: "-3.8 pts"},
		{ID: "first-funding", Title: "First funding", Question: "Funding-day-1 retention by cohort", Status: "Needs review", Freshness: "1h", Dot: "neutral", Change: "+10.6 pts"},
		{ID: "lifecycle-messaging", Title: "Lifecycle messaging", Question: "Lifecycle re-engage uplift", Status: "Drafting", Freshness: "3h", Dot: "neutral", Change: "+1.1 pts"},
		{ID: "risk-and-fraud", Title: "Risk & fraud", Question: "Sardine rule efficacy review", Status: "Blocked - gap", Freshness: "5h", Dot: "bad", Change: "8.9 pts"},
	}
}

func consoleTemplateSources() []templates.ConsoleSource {
	displayOrder := []string{"jira", "posthog", "metabase", "confluence", "socure", "klaviyo", "sardine", "ga", "dragonboat", "netxd"}
	details := map[string]string{
		"jira":       "14 open - KYC, Risk",
		"posthog":    "1.2M events/day",
		"metabase":   "38 verified Q",
		"confluence": "142 specs",
		"socure":     "retry logs stale",
		"klaviyo":    "12 flows",
		"sardine":    "8 rules",
		"ga":         "web marketing",
		"dragonboat": "Q2 portfolio",
		"netxd":      "settlement ops",
	}
	catalog := make(map[string]connectors.ConnectorSpec, len(connectors.Catalog))
	for _, connector := range connectors.Catalog {
		catalog[connector.ConnectorID] = connector
	}
	sources := make([]templates.ConsoleSource, 0, len(connectors.Catalog))
	for _, connectorID := range displayOrder {
		connector, ok := catalog[connectorID]
		if !ok {
			continue
		}
		method := "custom ingestion"
		if connector.ConnectionMethod == connectors.ConnectionMethodOnyxNative {
			method = "Onyx native"
		}
		detail := details[connector.ConnectorID]
		if detail == "" {
			detail = connector.DocumentSetName
		}
		status := "connected"
		dot := "good"
		if connector.ConnectorID == "socure" {
			status = "degraded"
			dot = "warn"
		}
		sources = append(sources, templates.ConsoleSource{
			ID:       connector.ConnectorID,
			Name:     connector.DisplayName,
			Category: connector.Provider,
			Status:   status,
			Detail:   detail,
			Method:   method,
			Dot:      dot,
			Href:     "/console/integrations/" + connector.ConnectorID,
		})
	}
	return sources
}

func consolePromptChips() []templates.ConsoleAction {
	return []templates.ConsoleAction{
		{Label: "What's changed in onboarding since last review?", Href: "/console/knowledge/ask", Kind: "secondary"},
		{Label: "Which lifecycle email is converting best?", Href: "/console/knowledge/ask", Kind: "secondary"},
		{Label: "Show open risk work blocking publish.", Href: "/console/knowledge/ask", Kind: "secondary"},
		{Label: "Run weekly PM brief", Href: "/console/generate/weekly-brief", Kind: "secondary"},
	}
}

func consoleTemplateThreads(queue []templates.ConsoleQueueItem) []templates.ConsoleThread {
	threads := make([]templates.ConsoleThread, 0, 6)
	for _, item := range queue {
		if len(threads) == 2 {
			break
		}
		threads = append(threads, templates.ConsoleThread{
			Title:  item.Title,
			Topic:  "Artifact review",
			Status: item.Status,
			Source: "Eval output",
			Age:    "now",
			Href:   item.Href,
		})
	}
	defaults := []templates.ConsoleThread{
		{Title: "Why did KYC conversion drop 4.2 pts?", Topic: "KYC conversion", Status: "Decision pending", Source: "3 sources - 8 citations", Age: "4m", Href: "/console/topics/kyc-conversion"},
		{Title: "Funding-day-1 retention by cohort", Topic: "First funding", Status: "Ready to publish", Source: "3 sources - 5 citations", Age: "1h", Href: "/console/topics/first-funding"},
		{Title: "Lifecycle re-engage uplift", Topic: "Lifecycle messaging", Status: "Drafting", Source: "2 sources - 4 citations", Age: "3h", Href: "/console/topics/lifecycle-messaging"},
		{Title: "Sardine rule efficacy review", Topic: "Risk & fraud", Status: "Blocked - gap", Source: "3 sources - 6 citations", Age: "5h", Href: "/console/topics/risk-and-fraud"},
		{Title: "Onboarding v3.3 scoping", Topic: "Onboarding", Status: "Needs review", Source: "5 sources - 1 ticket", Age: "1d", Href: "/console/topics/onboarding"},
	}
	for _, item := range defaults {
		if len(threads) == 6 {
			break
		}
		threads = append(threads, item)
	}
	return threads
}

func consoleTopicPulse() []templates.ConsoleTopicPulse {
	return []templates.ConsoleTopicPulse{
		{Label: "KYC conversion", Delta: "-4.2 pts", Value: "73.2%", Tone: "bad"},
		{Label: "Onboarding completion", Delta: "-3.8 pts", Value: "68.4%", Tone: "bad"},
		{Label: "First funding D1", Delta: "+10.6 pts", Value: "41.0%", Tone: "good"},
		{Label: "Lifecycle CTR", Delta: "+1.1 pts", Value: "12.8%", Tone: "good"},
		{Label: "Risk auto-decision", Delta: "8.9 pts", Value: "94.1%", Tone: "neutral"},
	}
}

func nullableFloat(value sql.NullFloat64) *float64 {
	if !value.Valid {
		return nil
	}
	return &value.Float64
}

func averageOrNil(values []float64) *float64 {
	if len(values) == 0 {
		return nil
	}
	sum := 0.0
	for _, value := range values {
		sum += value
	}
	average := round3(sum / float64(len(values)))
	return &average
}

func formatPercent(value *float64) string {
	if value == nil {
		return "n/a"
	}
	return strconv.Itoa(int(math.Round(*value*100))) + "%"
}

func minInt(left int, right int) int {
	if left < right {
		return left
	}
	return right
}

package httpapi

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/governance"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
)

type workflowSpec struct {
	Slug     string
	Title    string
	SkillID  string
	Sections []string
}

var workflowOrder = []string{"weekly-brief", "technical-prd", "risk-brd"}

var workflowSpecs = map[string]workflowSpec{
	"weekly-brief": {
		Slug:     "weekly-brief",
		Title:    "Weekly PM Brief",
		SkillID:  "meeting_summary",
		Sections: []string{"Summary", "What changed", "Decisions", "Risks", "Next actions"},
	},
	"technical-prd": {
		Slug:     "technical-prd",
		Title:    "Technical PRD",
		SkillID:  "agent_system_prompt",
		Sections: []string{"Problem", "Requirements", "Technical approach", "Dependencies", "Rollout"},
	},
	"risk-brd": {
		Slug:     "risk-brd",
		Title:    "Risk BRD",
		SkillID:  "support_agent",
		Sections: []string{"Risk context", "Evidence", "Policy decision", "Controls", "Open questions"},
	},
}

var publishReadyCriteria = []string{
	"has_output",
	"meets_min_citations",
	"has_required_sections",
	"scope_declared",
	"has_review_checklist",
	"review_checklist_resolved",
}

type askRequest struct {
	Question  string   `json:"question"`
	TopicID   string   `json:"topic_id"`
	SourceID  string   `json:"source_id"`
	SourceIDs []string `json:"source_ids"`
}

type askCitation struct {
	DocumentID string  `json:"document_id"`
	Title      string  `json:"title"`
	Blurb      string  `json:"blurb"`
	Score      float64 `json:"score"`
	Link       *string `json:"link"`
	UpdatedAt  *string `json:"updated_at"`
}

type askResponse struct {
	Question   string        `json:"question"`
	Answer     string        `json:"answer"`
	Confidence float64       `json:"confidence"`
	Citations  []askCitation `json:"citations"`
	Followups  []string      `json:"followups"`
	SourcePlan askSourcePlan `json:"source_plan"`
}

type askSourcePlan struct {
	Scope                string   `json:"scope"`
	AuthoritativeSources []string `json:"authoritative_sources"`
	RequiresFreshness    bool     `json:"requires_freshness"`
	Blockers             []string `json:"blockers"`
}

type generateArtifactRequest struct {
	WorkflowSlug           string `json:"workflow_slug"`
	Question               string `json:"question"`
	TopicID                string `json:"topic_id"`
	SourceID               string `json:"source_id"`
	RegenerateFromOutputID string `json:"regenerate_from_output_id"`
}

type generateArtifactResponse struct {
	RoundID         string  `json:"round_id"`
	OutputID        string  `json:"output_id"`
	WorkflowSlug    string  `json:"workflow_slug"`
	WorkflowTitle   string  `json:"workflow_title"`
	SkillID         string  `json:"skill_id"`
	PassFail        string  `json:"pass_fail"`
	Confidence      float64 `json:"confidence"`
	ExportReadiness float64 `json:"export_readiness"`
	DestinationHref string  `json:"destination_href"`
}

type exportReadinessInput struct {
	HardGatePass           bool
	Confidence             float64
	GoldRegressionPassRate float64
	ClaimLineageRate       float64
	MetricFreshness        float64
	PlanningHygieneScore   float64
}

type exportReadinessScore struct {
	Value     float64
	Breakdown map[string]float64
}

func (s *Server) workflowCatalog(w http.ResponseWriter, _ *http.Request) {
	workflows := make([]map[string]string, 0, len(workflowOrder))
	for _, slug := range workflowOrder {
		spec := workflowSpecs[slug]
		workflows = append(workflows, map[string]string{
			"slug":     spec.Slug,
			"title":    spec.Title,
			"skill_id": spec.SkillID,
		})
	}
	writeJSONResponse(w, http.StatusOK, map[string]any{"workflows": workflows})
}

func (s *Server) ask(w http.ResponseWriter, r *http.Request) {
	if s.onyx == nil {
		writeError(w, http.StatusServiceUnavailable, "Onyx client is not configured")
		return
	}

	var body askRequest
	if !decodeJSONRequest(w, r, &body) {
		return
	}
	body.Question = strings.TrimSpace(body.Question)
	if body.Question == "" {
		writeError(w, http.StatusUnprocessableEntity, "question is required")
		return
	}

	sourceIDs := scopedSourceIDs(body.SourceID, body.SourceIDs)
	limit := s.settings.AskSearchLimit
	if limit <= 0 {
		limit = 1
	}
	hits, err := s.onyx.AdminSearch(
		r.Context(),
		body.Question,
		scopeFilters(body.TopicID, body.SourceID, body.SourceIDs),
		limit,
	)
	if err != nil {
		s.writeAuditEvent(r.Context(), r, auditEvent{
			Category:   "access",
			Action:     "onyx_search",
			Outcome:    "error",
			Severity:   "error",
			TargetType: "onyx_search",
			TargetID:   firstNonEmpty(body.TopicID, body.SourceID),
			Reason:     fmt.Sprintf("%T", err),
			StatusCode: http.StatusServiceUnavailable,
			Metadata: map[string]any{
				"question_sha256": hashText(body.Question),
				"topic_id":        emptyToNil(body.TopicID),
				"source_ids":      sourceIDs,
			},
		})
		writeError(w, http.StatusServiceUnavailable, "Onyx search failed: "+err.Error())
		return
	}

	confidence := round3(math.Min(1, float64(len(hits))/float64(limit)))
	s.writeAuditEvent(r.Context(), r, auditEvent{
		Category:   "access",
		Action:     "onyx_search",
		Outcome:    "success",
		Severity:   "info",
		TargetType: "onyx_search",
		TargetID:   firstNonEmpty(body.TopicID, body.SourceID),
		StatusCode: http.StatusOK,
		Metadata: map[string]any{
			"question_sha256": hashText(body.Question),
			"topic_id":        emptyToNil(body.TopicID),
			"source_ids":      sourceIDs,
			"hit_count":       len(hits),
			"confidence":      confidence,
		},
	})

	writeJSONResponse(w, http.StatusOK, askResponse{
		Question:   body.Question,
		Answer:     composeAnswer(body.Question, hits),
		Confidence: confidence,
		Citations:  serializeHits(hits),
		Followups:  followups(body.Question, body.TopicID, sourceIDs),
		SourcePlan: sourcePlanForAsk(body, hits, sourceIDs),
	})
}

func (s *Server) generateWorkflow(w http.ResponseWriter, r *http.Request) {
	if s.store == nil {
		writeError(w, http.StatusServiceUnavailable, "database store is not configured")
		return
	}
	if s.onyx == nil {
		writeError(w, http.StatusServiceUnavailable, "Onyx client is not configured")
		return
	}

	var body generateArtifactRequest
	if !decodeJSONRequest(w, r, &body) {
		return
	}
	spec, ok := workflowSpecs[body.WorkflowSlug]
	if !ok {
		writeError(w, http.StatusUnprocessableEntity, "unknown workflow_slug")
		return
	}

	skill, err := s.store.Skill(r.Context(), spec.SkillID)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusConflict, "DreamFi skills are not seeded")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "skill lookup failed: "+err.Error())
		return
	}
	if skill.OnyxPersonaID == nil {
		writeError(w, http.StatusConflict, "Onyx personas are not seeded")
		return
	}

	promptVersion, err := s.activePromptVersion(r.Context(), spec.SkillID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "prompt version lookup failed: "+err.Error())
		return
	}

	question := strings.TrimSpace(body.Question)
	if question == "" {
		question = fmt.Sprintf("Draft a %s from the current DreamFi product context.", spec.Title)
	}
	if strings.TrimSpace(body.RegenerateFromOutputID) != "" {
		exists, err := s.store.EvalOutputExists(r.Context(), body.RegenerateFromOutputID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "artifact lookup failed: "+err.Error())
			return
		}
		if exists {
			question = fmt.Sprintf("%s\n\nRegenerate from artifact %s.", question, body.RegenerateFromOutputID)
		}
	}

	chatSession, err := s.onyx.CreateChatSession(
		r.Context(),
		int(*skill.OnyxPersonaID),
		fmt.Sprintf("dreamfi-workflow:%s:%s", spec.Slug, truncateString(question, 80)),
	)
	if err == nil {
		var chat onyx.ChatResult
		chat, err = s.onyx.SendMessageSync(
			r.Context(),
			chatSession.ID,
			nil,
			workflowPrompt(spec, question, body.TopicID, body.SourceID),
			nil,
		)
		if err == nil {
			output, err := s.createArtifactRound(r.Context(), spec, promptVersion, question, body.TopicID, body.SourceID, chatSession.ID, chat)
			if err != nil {
				writeError(w, http.StatusInternalServerError, "artifact persistence failed: "+err.Error())
				return
			}

			s.writeAuditEvent(r.Context(), r, auditEvent{
				Category:   "generation",
				Action:     "workflow_generate",
				Outcome:    outcomeForPassFail(output.PassFail),
				Severity:   severityForPassFail(output.PassFail),
				TargetType: "eval_output",
				TargetID:   output.OutputID,
				StatusCode: http.StatusOK,
				Metadata: map[string]any{
					"workflow_slug":             spec.Slug,
					"workflow_title":            spec.Title,
					"skill_id":                  spec.SkillID,
					"round_id":                  output.RoundID,
					"question_sha256":           hashText(question),
					"topic_id":                  emptyToNil(body.TopicID),
					"source_id":                 emptyToNil(body.SourceID),
					"regenerate_from_output_id": emptyToNil(body.RegenerateFromOutputID),
					"pass_fail":                 output.PassFail,
					"confidence":                derefFloat(output.Confidence),
					"export_readiness":          derefFloat(output.ExportReadiness),
					"citation_count":            len(chat.Citations),
					"criteria":                  output.Criteria,
				},
			})

			writeJSONResponse(w, http.StatusOK, generateArtifactResponse{
				RoundID:         output.RoundID,
				OutputID:        output.OutputID,
				WorkflowSlug:    spec.Slug,
				WorkflowTitle:   spec.Title,
				SkillID:         spec.SkillID,
				PassFail:        output.PassFail,
				Confidence:      derefFloat(output.Confidence),
				ExportReadiness: derefFloat(output.ExportReadiness),
				DestinationHref: "/console/review?focus=" + output.OutputID,
			})
			return
		}
	}

	s.writeAuditEvent(r.Context(), r, auditEvent{
		Category:   "generation",
		Action:     "workflow_generate",
		Outcome:    "error",
		Severity:   "error",
		TargetType: "workflow",
		TargetID:   spec.Slug,
		Reason:     fmt.Sprintf("%T", err),
		StatusCode: http.StatusServiceUnavailable,
		Metadata: map[string]any{
			"workflow_slug":             spec.Slug,
			"skill_id":                  spec.SkillID,
			"question_sha256":           hashText(question),
			"topic_id":                  emptyToNil(body.TopicID),
			"source_id":                 emptyToNil(body.SourceID),
			"regenerate_from_output_id": emptyToNil(body.RegenerateFromOutputID),
		},
	})
	writeError(w, http.StatusServiceUnavailable, "Onyx generation failed: "+err.Error())
}

func (s *Server) activePromptVersion(ctx context.Context, skillID string) (store.PromptVersion, error) {
	active, err := s.store.ActivePromptVersion(ctx, skillID)
	if err == nil {
		return active, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return store.PromptVersion{}, err
	}

	latest, err := s.store.LatestPromptVersionNumber(ctx, skillID)
	if err != nil {
		return store.PromptVersion{}, err
	}
	now := s.currentTime()
	active = store.PromptVersion{
		PromptVersionID: newEntityID("prompt"),
		SkillID:         skillID,
		Version:         latest + 1,
		Template:        "console_workflow",
		SystemPrompt:    "DreamFi console workflow bootstrap.",
		IsActive:        true,
		CreatedAt:       now,
		ActivatedAt:     &now,
	}
	if err := s.store.CreatePromptVersion(ctx, active); err != nil {
		return store.PromptVersion{}, err
	}
	return active, nil
}

func (s *Server) createArtifactRound(
	ctx context.Context,
	spec workflowSpec,
	promptVersion store.PromptVersion,
	question string,
	topicID string,
	sourceID string,
	chatSessionID string,
	chat onyx.ChatResult,
) (store.EvalOutput, error) {
	criteria := criteriaForWorkflow(s.settings, spec, question, topicID, sourceID, chat)
	evalScore := criteriaScore(criteria)
	passFail := "fail"
	if workflowHardGatePasses(criteria) {
		passFail = "pass"
	}

	scorer := governance.NewConfidenceScorer(s.settings.FreshnessHalflifeDays)
	freshness := freshnessFromChat(chat, scorer, s.currentTime())
	confidence := scorer.Score(evalScore, freshness, len(chat.Citations), passFail == "pass")
	targetCitations := s.settings.ClaimLineageTargetCitations
	if targetCitations <= 0 {
		targetCitations = 1
	}
	exportReadiness := computeExportReadiness(exportReadinessInput{
		HardGatePass:           passFail == "pass",
		Confidence:             confidence.Confidence,
		GoldRegressionPassRate: 1,
		ClaimLineageRate:       math.Min(float64(len(chat.Citations)), float64(targetCitations)) / float64(targetCitations),
		MetricFreshness:        confidence.FreshnessScore,
		PlanningHygieneScore:   sourceHygiene(topicID, sourceID),
	})

	now := s.currentTime()
	completedAt := now
	roundID := newEntityID("round")
	outputID := newEntityID("output")
	if err := s.store.CreateEvalRound(ctx, store.EvalRound{
		RoundID:          roundID,
		SkillID:          spec.SkillID,
		PromptVersionID:  promptVersion.PromptVersionID,
		NInputs:          1,
		NOutputsPerInput: 1,
		TotalOutputs:     1,
		TotalPasses:      boolToInt(passFail == "pass"),
		Score:            round4(evalScore),
		StartedAt:        now,
		CompletedAt:      &completedAt,
		ArtifactsPath:    fmt.Sprintf("evals/results/%s/rounds/%s", spec.Slug, roundID),
	}); err != nil {
		return store.EvalOutput{}, err
	}

	var messageID *int64
	if chat.MessageID != nil {
		value := int64(*chat.MessageID)
		messageID = &value
	}
	output := store.EvalOutput{
		OutputID:          outputID,
		RoundID:           roundID,
		TestInputLabel:    truncateString(question, 160),
		Attempt:           1,
		GeneratedText:     chat.Text,
		Criteria:          criteria,
		PassFail:          passFail,
		OnyxChatSessionID: &chatSessionID,
		OnyxMessageID:     messageID,
		OnyxCitations:     stringifyCitations(chat.Citations),
		FreshnessScore:    &confidence.FreshnessScore,
		Confidence:        &confidence.Confidence,
		ExportReadiness:   &exportReadiness.Value,
		ExportBreakdown:   exportReadiness.Breakdown,
		CreatedAt:         now,
	}
	if err := s.store.CreateEvalOutput(ctx, output); err != nil {
		return store.EvalOutput{}, err
	}
	return output, nil
}

func decodeJSONRequest(w http.ResponseWriter, r *http.Request, out any) bool {
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(out); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return false
	}
	return true
}

func writeError(w http.ResponseWriter, statusCode int, detail string) {
	writeJSONResponse(w, statusCode, map[string]string{"detail": detail})
}

func scopeFilters(topicID string, sourceID string, sourceIDs []string) map[string]any {
	scope := map[string]any{}
	if strings.TrimSpace(topicID) != "" {
		scope["topic_id"] = strings.TrimSpace(topicID)
	}
	sources := scopedSourceIDs(sourceID, sourceIDs)
	if len(sources) > 0 {
		scope["source_ids"] = sources
	}
	if len(scope) == 0 {
		return map[string]any{}
	}
	return map[string]any{"dreamfi_scope": scope}
}

func scopedSourceIDs(sourceID string, sourceIDs []string) []string {
	seen := map[string]struct{}{}
	for _, value := range append([]string{sourceID}, sourceIDs...) {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		seen[trimmed] = struct{}{}
	}
	sources := make([]string, 0, len(seen))
	for value := range seen {
		sources = append(sources, value)
	}
	sort.Strings(sources)
	return sources
}

func serializeHits(hits []onyx.SearchHit) []askCitation {
	citations := make([]askCitation, 0, len(hits))
	for _, hit := range hits {
		citations = append(citations, askCitation{
			DocumentID: hit.DocumentID,
			Title:      hit.SemanticIdentifier,
			Blurb:      hit.Blurb,
			Score:      hit.Score,
			Link:       stringPtrIfNotEmpty(hit.Link),
			UpdatedAt:  stringPtrIfNotEmpty(hit.UpdatedAt),
		})
	}
	return citations
}

func composeAnswer(question string, hits []onyx.SearchHit) string {
	if len(hits) == 0 {
		return "Onyx did not return matching evidence for this ask. Keep the question in review and narrow it to a source or topic before generating an artifact."
	}

	lead := hits[0]
	supportText := ""
	if len(hits) > 1 {
		end := len(hits)
		if end > 3 {
			end = 3
		}
		titles := make([]string, 0, end-1)
		for _, hit := range hits[1:end] {
			titles = append(titles, hit.SemanticIdentifier)
		}
		supportText = " Supporting evidence also came from " + strings.Join(titles, ", ") + "."
	}
	return fmt.Sprintf(
		"Onyx found %d evidence item(s) for: %s. The strongest source is %s: %s%s",
		len(hits),
		question,
		lead.SemanticIdentifier,
		lead.Blurb,
		supportText,
	)
}

func followups(question string, topicID string, sourceIDs []string) []string {
	items := []string{
		"What evidence would change the answer to: " + question,
		"Which artifact should Product generate from this answer?",
	}
	if strings.TrimSpace(topicID) != "" {
		items = append(items, "What is still missing from the "+strings.TrimSpace(topicID)+" topic room?")
	}
	if len(sourceIDs) > 0 {
		items = append(items, "What changed in "+sourceIDs[0]+" since the last decision?")
	}
	if len(items) > 4 {
		return items[:4]
	}
	return items
}

func sourcePlanForAsk(body askRequest, hits []onyx.SearchHit, sourceIDs []string) askSourcePlan {
	authoritativeSources := append([]string{}, sourceIDs...)
	if len(authoritativeSources) == 0 {
		authoritativeSources = sourceIDsFromQuestion(body.Question)
	}
	blockers := []string{}
	requiresFreshness := asksForFreshness(body.Question)
	if requiresFreshness {
		if len(authoritativeSources) == 0 && strings.TrimSpace(body.TopicID) == "" {
			blockers = append(blockers, "Pick a topic or source before treating this as current operational evidence.")
		}
		for _, hit := range hits {
			if strings.TrimSpace(hit.UpdatedAt) == "" {
				blockers = append(blockers, "Freshness-sensitive ask returned evidence without updated_at; verify before publishing.")
				break
			}
		}
	}
	scope := "indexed"
	if strings.TrimSpace(body.TopicID) != "" || len(authoritativeSources) > 0 {
		scope = "scoped"
	}
	if requiresFreshness {
		scope = "freshness-sensitive"
	}
	return askSourcePlan{
		Scope:                scope,
		AuthoritativeSources: authoritativeSources,
		RequiresFreshness:    requiresFreshness,
		Blockers:             blockers,
	}
}

func sourceIDsFromQuestion(question string) []string {
	normalized := strings.ToLower(question)
	candidates := []string{"jira", "confluence", "metabase", "posthog", "socure", "sardine", "netxd", "dragonboat", "klaviyo"}
	out := []string{}
	for _, candidate := range candidates {
		if strings.Contains(normalized, candidate) {
			out = append(out, candidate)
		}
	}
	return out
}

func asksForFreshness(question string) bool {
	normalized := strings.ToLower(question)
	for _, marker := range []string{"latest", "current", "today", "as of", "since", "changed", "change", "now", "fresh"} {
		if strings.Contains(normalized, marker) {
			return true
		}
	}
	return false
}

func workflowPrompt(spec workflowSpec, question string, topicID string, sourceID string) string {
	scope := []string{}
	if strings.TrimSpace(topicID) != "" {
		scope = append(scope, "topic_id="+strings.TrimSpace(topicID))
	}
	if strings.TrimSpace(sourceID) != "" {
		scope = append(scope, "source_id="+strings.TrimSpace(sourceID))
	}
	scopeText := "all available DreamFi product context"
	if len(scope) > 0 {
		scopeText = strings.Join(scope, ", ")
	}
	sections := make([]string, 0, len(spec.Sections))
	for _, section := range spec.Sections {
		sections = append(sections, "- "+section)
	}
	return fmt.Sprintf(
		"You are drafting a %s for DreamFi's product team.\n"+
			"Use Onyx retrieval evidence and include citation markers where available.\n"+
			"Do not invent metrics, owners, dates, or policy claims that are not supported.\n"+
			"Scope: %s\n"+
			"Product question: %s\n\n"+
			"Return Markdown with these sections:\n"+
			"%s\n\n"+
			"End with a short review checklist for anything that still needs human confirmation.",
		spec.Title,
		scopeText,
		question,
		strings.Join(sections, "\n"),
	)
}

func criteriaForWorkflow(settings config.Settings, spec workflowSpec, question string, topicID string, sourceID string, chat onyx.ChatResult) map[string]any {
	text := strings.TrimSpace(chat.Text)
	hasReviewChecklist, reviewChecklistResolved := reviewChecklistStatus(text)
	citationCount := len(chat.Citations)
	return map[string]any{
		"workflow_slug":             spec.Slug,
		"workflow_title":            spec.Title,
		"question":                  question,
		"topic_id":                  emptyToNil(topicID),
		"source_id":                 emptyToNil(sourceID),
		"has_output":                text != "",
		"citation_count":            citationCount,
		"meets_min_citations":       citationCount >= settings.WorkflowMinCitations,
		"has_required_sections":     hasRequiredSectionContent(settings, text, spec.Sections),
		"scope_declared":            strings.TrimSpace(topicID) != "" || strings.TrimSpace(sourceID) != "" || !settings.WorkflowRequireScope,
		"has_review_checklist":      hasReviewChecklist,
		"review_checklist_resolved": reviewChecklistResolved,
	}
}

func hasRequiredSectionContent(settings config.Settings, markdown string, sections []string) bool {
	minWords := settings.WorkflowMinSectionWords
	if minWords <= 0 {
		minWords = 1
	}
	for _, section := range sections {
		if len(strings.Fields(sectionText(markdown, section))) < minWords {
			return false
		}
	}
	return true
}

func sectionText(markdown string, section string) string {
	lines := strings.Split(markdown, "\n")
	found := false
	collected := []string{}
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "#") {
			heading := strings.TrimSpace(strings.TrimLeft(trimmed, "#"))
			if found {
				break
			}
			if headingMatches(heading, section) {
				found = true
				continue
			}
		}
		if found {
			collected = append(collected, line)
		}
	}
	return strings.TrimSpace(strings.Join(collected, "\n"))
}

func headingMatches(heading string, section string) bool {
	normalizedHeading := strings.ToLower(strings.TrimSpace(heading))
	normalizedSection := strings.ToLower(strings.TrimSpace(section))
	return normalizedHeading == normalizedSection ||
		strings.HasPrefix(normalizedHeading, normalizedSection+" ") ||
		strings.HasPrefix(normalizedHeading, normalizedSection+":") ||
		strings.HasPrefix(normalizedHeading, normalizedSection+"-")
}

func reviewChecklistStatus(markdown string) (bool, bool) {
	tail := sectionText(markdown, "Review checklist")
	if tail == "" {
		return false, false
	}
	normalized := strings.ToLower(tail)
	for _, marker := range []string{
		"no open review items",
		"no unresolved review items",
		"all review items resolved",
	} {
		if strings.Contains(normalized, marker) {
			return true, true
		}
	}
	for _, marker := range []string{
		"[ ]",
		"confirm ",
		"missing",
		"needs confirmation",
		"needs human",
		"open item",
		"tbd",
		"unknown",
		"unresolved",
		"verify ",
	} {
		if strings.Contains(normalized, marker) {
			return true, false
		}
	}
	return true, true
}

func criteriaScore(criteria map[string]any) float64 {
	passed := 0
	for _, key := range publishReadyCriteria {
		if value, ok := criteria[key].(bool); ok && value {
			passed++
		}
	}
	return float64(passed) / float64(len(publishReadyCriteria))
}

func workflowHardGatePasses(criteria map[string]any) bool {
	for _, key := range publishReadyCriteria {
		value, ok := criteria[key].(bool)
		if !ok || !value {
			return false
		}
	}
	return true
}

func freshnessFromChat(chat onyx.ChatResult, scorer governance.ConfidenceScorer, now time.Time) float64 {
	updatedAts := []time.Time{}
	for _, document := range chat.Documents {
		updatedAt, ok := parseDocumentUpdatedAt(document["updated_at"])
		if ok {
			updatedAts = append(updatedAts, updatedAt)
		}
	}
	return scorer.FreshnessFromUpdatedAt(updatedAts, now)
}

func parseDocumentUpdatedAt(value any) (time.Time, bool) {
	switch typed := value.(type) {
	case time.Time:
		return typed, !typed.IsZero()
	case string:
		if strings.TrimSpace(typed) == "" {
			return time.Time{}, false
		}
		parsed, err := time.Parse(time.RFC3339, strings.ReplaceAll(typed, "Z", "+00:00"))
		if err != nil {
			return time.Time{}, false
		}
		return parsed, true
	default:
		return time.Time{}, false
	}
}

func sourceHygiene(topicID string, sourceID string) float64 {
	hasTopic := strings.TrimSpace(topicID) != ""
	hasSource := strings.TrimSpace(sourceID) != ""
	if hasTopic && hasSource {
		return 1
	}
	if hasTopic || hasSource {
		return 0.85
	}
	return 0.65
}

func computeExportReadiness(input exportReadinessInput) exportReadinessScore {
	breakdown := map[string]float64{
		"hard_gate":        boolFloat(input.HardGatePass),
		"confidence":       clamp01(input.Confidence),
		"gold_regression":  clamp01(input.GoldRegressionPassRate),
		"claim_lineage":    clamp01(input.ClaimLineageRate),
		"metric_freshness": clamp01(input.MetricFreshness),
		"planning_hygiene": clamp01(input.PlanningHygieneScore),
	}
	if !input.HardGatePass {
		return exportReadinessScore{Value: 0, Breakdown: breakdown}
	}
	value := 0.20 +
		0.15*breakdown["confidence"] +
		0.25*breakdown["gold_regression"] +
		0.20*breakdown["claim_lineage"] +
		0.10*breakdown["metric_freshness"] +
		0.10*breakdown["planning_hygiene"]
	return exportReadinessScore{Value: round3(clamp01(value)), Breakdown: breakdown}
}

func stringifyCitations(citations map[int]string) map[string]string {
	out := make(map[string]string, len(citations))
	for key, value := range citations {
		out[strconv.Itoa(key)] = value
	}
	return out
}

type auditEvent struct {
	Category   string
	Action     string
	Outcome    string
	Severity   string
	TargetType string
	TargetID   string
	Reason     string
	StatusCode int
	Metadata   map[string]any
}

func (s *Server) writeAuditEvent(ctx context.Context, r *http.Request, event auditEvent) {
	if s.store == nil || !s.settings.AuditEnabled {
		return
	}
	now := s.currentTime()
	method := r.Method
	path := r.URL.Path
	statusCode := event.StatusCode
	requestID := strings.TrimSpace(r.Header.Get("X-Request-ID"))
	record := store.AuditEvent{
		EventID:    newEntityID("audit"),
		EventHash:  hashText(fmt.Sprintf("%s|%s|%s|%s|%d|%s", event.Category, event.Action, event.Outcome, path, statusCode, now.Format(time.RFC3339Nano))),
		EventType:  event.Category + "." + event.Action,
		Category:   event.Category,
		Action:     event.Action,
		Outcome:    event.Outcome,
		Severity:   event.Severity,
		ActorType:  "anonymous",
		RequestID:  stringPtrIfNotEmpty(requestID),
		HTTPMethod: &method,
		Path:       &path,
		StatusCode: &statusCode,
		TargetType: stringPtrIfNotEmpty(event.TargetType),
		TargetID:   stringPtrIfNotEmpty(event.TargetID),
		Reason:     stringPtrIfNotEmpty(event.Reason),
		Metadata:   event.Metadata,
		CreatedAt:  now,
	}
	_ = s.store.CreateAuditEvent(ctx, record)
}

func hashText(value string) string {
	sum := sha256.Sum256([]byte(value))
	return hex.EncodeToString(sum[:])
}

func outcomeForPassFail(passFail string) string {
	if passFail == "pass" {
		return "success"
	}
	return "blocked"
}

func severityForPassFail(passFail string) string {
	if passFail == "pass" {
		return "info"
	}
	return "warning"
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func emptyToNil(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return strings.TrimSpace(value)
}

func stringPtrIfNotEmpty(value string) *string {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	trimmed := strings.TrimSpace(value)
	return &trimmed
}

func truncateString(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[:limit]
}

func derefFloat(value *float64) float64 {
	if value == nil {
		return 0
	}
	return *value
}

func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func boolFloat(value bool) float64 {
	if value {
		return 1
	}
	return 0
}

func clamp01(value float64) float64 {
	return math.Max(0, math.Min(1, value))
}

func round3(value float64) float64 {
	return math.Round(value*1000) / 1000
}

func round4(value float64) float64 {
	return math.Round(value*10000) / 10000
}

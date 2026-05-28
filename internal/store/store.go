package store

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
)

type Dialect string

const (
	DialectPostgres Dialect = "postgres"
	DialectSQLite   Dialect = "sqlite"
)

type Store struct {
	db      *sql.DB
	dialect Dialect
}

func New(db *sql.DB, dialect Dialect) *Store {
	return &Store{db: db, dialect: dialect}
}

func (s *Store) DB() *sql.DB {
	return s.db
}

func (s *Store) placeholder(index int) string {
	if s.dialect == DialectPostgres {
		return fmt.Sprintf("$%d", index)
	}
	return "?"
}

func (s *Store) placeholders(count int) string {
	parts := make([]string, count)
	for i := range count {
		parts[i] = s.placeholder(i + 1)
	}
	return strings.Join(parts, ", ")
}

func (s *Store) UpsertSkill(ctx context.Context, skill Skill) error {
	criteria, err := jsonText(skill.Criteria)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO skills (
			skill_id, display_name, description, eval_template_path,
			eval_runner_path, criteria_json, onyx_persona_id, created_at
		) VALUES (`+s.placeholders(8)+`)
		ON CONFLICT(skill_id) DO UPDATE SET
			display_name = excluded.display_name,
			description = excluded.description,
			eval_template_path = excluded.eval_template_path,
			eval_runner_path = excluded.eval_runner_path,
			criteria_json = excluded.criteria_json,
			onyx_persona_id = excluded.onyx_persona_id`,
		skill.SkillID,
		skill.DisplayName,
		skill.Description,
		skill.EvalTemplatePath,
		skill.EvalRunnerPath,
		criteria,
		nullable(skill.OnyxPersonaID),
		skill.CreatedAt,
	)
	return err
}

func (s *Store) CreatePromptVersion(ctx context.Context, prompt PromptVersion) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO prompt_versions (
			prompt_version_id, skill_id, version, template, system_prompt,
			is_active, parent_version_id, created_at, activated_at, deactivated_at
		) VALUES (`+s.placeholders(10)+`)`,
		prompt.PromptVersionID,
		prompt.SkillID,
		prompt.Version,
		prompt.Template,
		prompt.SystemPrompt,
		prompt.IsActive,
		nullable(prompt.ParentVersionID),
		prompt.CreatedAt,
		nullable(prompt.ActivatedAt),
		nullable(prompt.DeactivatedAt),
	)
	return err
}

func (s *Store) ActivatePromptVersion(ctx context.Context, promptVersionID string, activatedAt any) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			_ = tx.Rollback()
		}
	}()

	var skillID string
	err = tx.QueryRowContext(
		ctx,
		`SELECT skill_id FROM prompt_versions WHERE prompt_version_id = `+s.placeholder(1),
		promptVersionID,
	).Scan(&skillID)
	if err != nil {
		return err
	}

	_, err = tx.ExecContext(
		ctx,
		`UPDATE prompt_versions
		 SET is_active = false, deactivated_at = `+s.placeholder(1)+`
		 WHERE skill_id = `+s.placeholder(2)+` AND is_active = true`,
		activatedAt,
		skillID,
	)
	if err != nil {
		return err
	}

	_, err = tx.ExecContext(
		ctx,
		`UPDATE prompt_versions
		 SET is_active = true, activated_at = `+s.placeholder(1)+`, deactivated_at = NULL
		 WHERE prompt_version_id = `+s.placeholder(2),
		activatedAt,
		promptVersionID,
	)
	if err != nil {
		return err
	}

	err = tx.Commit()
	return err
}

func (s *Store) ActivePromptVersion(ctx context.Context, skillID string) (PromptVersion, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT prompt_version_id, skill_id, version, template, system_prompt, is_active,
		        parent_version_id, created_at, activated_at, deactivated_at
		 FROM prompt_versions
		 WHERE skill_id = `+s.placeholder(1)+` AND is_active = true
		 LIMIT 1`,
		skillID,
	)

	var prompt PromptVersion
	var parent sql.NullString
	var activated sql.NullTime
	var deactivated sql.NullTime
	err := row.Scan(
		&prompt.PromptVersionID,
		&prompt.SkillID,
		&prompt.Version,
		&prompt.Template,
		&prompt.SystemPrompt,
		&prompt.IsActive,
		&parent,
		&prompt.CreatedAt,
		&activated,
		&deactivated,
	)
	if err != nil {
		return PromptVersion{}, err
	}
	if parent.Valid {
		prompt.ParentVersionID = &parent.String
	}
	if activated.Valid {
		prompt.ActivatedAt = &activated.Time
	}
	if deactivated.Valid {
		prompt.DeactivatedAt = &deactivated.Time
	}
	return prompt, nil
}

func (s *Store) CreateEvalRound(ctx context.Context, round EvalRound) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO eval_rounds (
			round_id, skill_id, prompt_version_id, n_inputs, n_outputs_per_input,
			total_outputs, total_passes, score, previous_score, improvement,
			started_at, completed_at, artifacts_path
		) VALUES (`+s.placeholders(13)+`)`,
		round.RoundID,
		round.SkillID,
		round.PromptVersionID,
		round.NInputs,
		round.NOutputsPerInput,
		round.TotalOutputs,
		round.TotalPasses,
		round.Score,
		nullable(round.PreviousScore),
		nullable(round.Improvement),
		round.StartedAt,
		nullable(round.CompletedAt),
		round.ArtifactsPath,
	)
	return err
}

func (s *Store) CreateEvalOutput(ctx context.Context, output EvalOutput) error {
	criteria, err := jsonText(output.Criteria)
	if err != nil {
		return err
	}
	citations, err := jsonText(output.OnyxCitations)
	if err != nil {
		return err
	}
	breakdown, err := jsonText(output.ExportBreakdown)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO eval_outputs (
			output_id, round_id, test_input_label, attempt, generated_text,
			criteria_json, pass_fail, onyx_chat_session_id, onyx_message_id,
			onyx_citations_json, freshness_score, confidence, export_readiness,
			export_breakdown_json, created_at
		) VALUES (`+s.placeholders(15)+`)`,
		output.OutputID,
		output.RoundID,
		output.TestInputLabel,
		output.Attempt,
		output.GeneratedText,
		criteria,
		output.PassFail,
		nullable(output.OnyxChatSessionID),
		nullable(output.OnyxMessageID),
		citations,
		nullable(output.FreshnessScore),
		nullable(output.Confidence),
		nullable(output.ExportReadiness),
		breakdown,
		output.CreatedAt,
	)
	return err
}

func (s *Store) CreatePublishLog(ctx context.Context, log PublishLog) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO publish_log (
			publish_id, skill_id, prompt_version_id, output_id, destination,
			destination_ref, decision, reason, created_at
		) VALUES (`+s.placeholders(9)+`)`,
		log.PublishID,
		log.SkillID,
		log.PromptVersionID,
		log.OutputID,
		log.Destination,
		nullable(log.DestinationRef),
		log.Decision,
		nullable(log.Reason),
		log.CreatedAt,
	)
	return err
}

func (s *Store) UpsertConnectorSetting(ctx context.Context, setting ConnectorSetting) error {
	configJSON, err := jsonText(setting.Config)
	if err != nil {
		return err
	}
	metadataJSON, err := jsonText(setting.Metadata)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO connector_settings (
			connector_id, provider, credential_status, config_json,
			validation_status, document_set_id, document_set_name,
			retrieval_status, freshest_document_at, activation_status,
			metadata_json, created_at, updated_at
		) VALUES (`+s.placeholders(13)+`)
		ON CONFLICT(connector_id) DO UPDATE SET
			provider = excluded.provider,
			credential_status = excluded.credential_status,
			config_json = excluded.config_json,
			validation_status = excluded.validation_status,
			document_set_id = excluded.document_set_id,
			document_set_name = excluded.document_set_name,
			retrieval_status = excluded.retrieval_status,
			freshest_document_at = excluded.freshest_document_at,
			activation_status = excluded.activation_status,
			metadata_json = excluded.metadata_json,
			updated_at = excluded.updated_at`,
		setting.ConnectorID,
		setting.Provider,
		setting.CredentialStatus,
		configJSON,
		setting.ValidationStatus,
		nullable(setting.DocumentSetID),
		nullable(setting.DocumentSetName),
		nullable(setting.RetrievalStatus),
		nullable(setting.FreshestDocumentAt),
		setting.ActivationStatus,
		metadataJSON,
		setting.CreatedAt,
		setting.UpdatedAt,
	)
	return err
}

func (s *Store) CreateAuditEvent(ctx context.Context, event AuditEvent) error {
	metadata, err := jsonText(event.Metadata)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO audit_events (
			event_id, event_hash, event_type, category, action, outcome,
			severity, actor_id, actor_type, auth_method, request_id,
			http_method, path, status_code, target_type, target_id,
			reason, metadata_json, created_at
		) VALUES (`+s.placeholders(19)+`)`,
		event.EventID,
		event.EventHash,
		event.EventType,
		event.Category,
		event.Action,
		event.Outcome,
		event.Severity,
		nullable(event.ActorID),
		event.ActorType,
		nullable(event.AuthMethod),
		nullable(event.RequestID),
		nullable(event.HTTPMethod),
		nullable(event.Path),
		nullable(event.StatusCode),
		nullable(event.TargetType),
		nullable(event.TargetID),
		nullable(event.Reason),
		metadata,
		event.CreatedAt,
	)
	return err
}

func (s *Store) CreateArtifactFeedback(ctx context.Context, feedback ArtifactFeedback) error {
	metadata, err := jsonText(feedback.Metadata)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO artifact_feedback (
			feedback_id, output_id, reviewer_id, outcome, reason, notes,
			final_text_hash, metadata_json, gold_id, created_at
		) VALUES (`+s.placeholders(10)+`)`,
		feedback.FeedbackID,
		feedback.OutputID,
		feedback.ReviewerID,
		feedback.Outcome,
		nullable(feedback.Reason),
		nullable(feedback.Notes),
		feedback.FinalTextHash,
		metadata,
		nullable(feedback.GoldID),
		feedback.CreatedAt,
	)
	return err
}

func (s *Store) CreateLearningProposal(ctx context.Context, proposal LearningProposal) error {
	evidence, err := jsonText(proposal.Evidence)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO learning_proposals (
			proposal_id, skill_id, prompt_version_id, cluster_key, title,
			rationale, proposed_prompt_patch, status, source_failure_count,
			evidence_json, reviewer_id, review_notes, reviewed_at,
			created_prompt_version_id, created_at
		) VALUES (`+s.placeholders(15)+`)`,
		proposal.ProposalID,
		proposal.SkillID,
		nullable(proposal.PromptVersionID),
		proposal.ClusterKey,
		proposal.Title,
		proposal.Rationale,
		proposal.ProposedPromptPatch,
		proposal.Status,
		proposal.SourceFailureCount,
		evidence,
		nullable(proposal.ReviewerID),
		nullable(proposal.ReviewNotes),
		nullable(proposal.ReviewedAt),
		nullable(proposal.CreatedPromptVersionID),
		proposal.CreatedAt,
	)
	return err
}

func (s *Store) CreateReplaySchedule(ctx context.Context, schedule ReplaySchedule) error {
	payload, err := jsonText(schedule.Payload)
	if err != nil {
		return err
	}
	_, err = s.db.ExecContext(
		ctx,
		`INSERT INTO replay_schedules (
			schedule_id, replay_type, skill_id, prompt_version_id,
			cadence_days, next_run_at, last_run_at, is_active,
			created_by, payload_json, created_at
		) VALUES (`+s.placeholders(11)+`)`,
		schedule.ScheduleID,
		schedule.ReplayType,
		nullable(schedule.SkillID),
		nullable(schedule.PromptVersionID),
		schedule.CadenceDays,
		schedule.NextRunAt,
		nullable(schedule.LastRunAt),
		schedule.IsActive,
		nullable(schedule.CreatedBy),
		payload,
		schedule.CreatedAt,
	)
	return err
}

package store

import (
	"encoding/json"
	"time"
)

type Skill struct {
	SkillID          string
	DisplayName      string
	Description      string
	EvalTemplatePath string
	EvalRunnerPath   string
	Criteria         map[string]string
	OnyxPersonaID    *int64
	CreatedAt        time.Time
}

type PromptVersion struct {
	PromptVersionID string
	SkillID         string
	Version         int
	Template        string
	SystemPrompt    string
	IsActive        bool
	ParentVersionID *string
	CreatedAt       time.Time
	ActivatedAt     *time.Time
	DeactivatedAt   *time.Time
}

type EvalRound struct {
	RoundID          string
	SkillID          string
	PromptVersionID  string
	NInputs          int
	NOutputsPerInput int
	TotalOutputs     int
	TotalPasses      int
	Score            float64
	PreviousScore    *float64
	Improvement      *float64
	StartedAt        time.Time
	CompletedAt      *time.Time
	ArtifactsPath    string
}

type EvalOutput struct {
	OutputID          string
	RoundID           string
	TestInputLabel    string
	Attempt           int
	GeneratedText     string
	Criteria          map[string]any
	PassFail          string
	OnyxChatSessionID *string
	OnyxMessageID     *int64
	OnyxCitations     map[string]string
	FreshnessScore    *float64
	Confidence        *float64
	ExportReadiness   *float64
	ExportBreakdown   map[string]float64
	CreatedAt         time.Time
}

type PublishLog struct {
	PublishID       string
	SkillID         string
	PromptVersionID string
	OutputID        string
	Destination     string
	DestinationRef  *string
	Decision        string
	Reason          *string
	CreatedAt       time.Time
}

type ConnectorSetting struct {
	ConnectorID        string
	Provider           string
	CredentialStatus   string
	ValidationStatus   string
	ActivationStatus   string
	DocumentSetID      *int64
	DocumentSetName    *string
	RetrievalStatus    *string
	FreshestDocumentAt *time.Time
	Config             map[string]any
	Metadata           map[string]any
	CreatedAt          time.Time
	UpdatedAt          time.Time
}

type ConnectorSyncRun struct {
	SyncRunID      string
	ConnectorID    string
	Status         string
	Trigger        string
	PulledCount    int
	PersistedCount int
	IngestedCount  int
	SkippedCount   int
	ErrorCount     int
	Cursor         map[string]any
	Metadata       map[string]any
	Reason         *string
	StartedAt      time.Time
	CompletedAt    *time.Time
}

type ConnectorDocument struct {
	ConnectorDocumentID string
	ConnectorID         string
	ExternalID          string
	Title               string
	BodyText            string
	SourceURL           *string
	DocUpdatedAt        time.Time
	ContentHash         string
	Metadata            map[string]any
	SyncRunID           *string
	OnyxDocumentID      *string
	LastSeenAt          time.Time
	LastIngestedAt      *time.Time
	CreatedAt           time.Time
	UpdatedAt           time.Time
}

type AuditEvent struct {
	EventID    string
	EventHash  string
	EventType  string
	Category   string
	Action     string
	Outcome    string
	Severity   string
	ActorID    *string
	ActorType  string
	AuthMethod *string
	RequestID  *string
	HTTPMethod *string
	Path       *string
	StatusCode *int
	TargetType *string
	TargetID   *string
	Reason     *string
	Metadata   map[string]any
	CreatedAt  time.Time
}

type ArtifactFeedback struct {
	FeedbackID    string
	OutputID      string
	ReviewerID    string
	Outcome       string
	Reason        *string
	Notes         *string
	FinalTextHash string
	Metadata      map[string]any
	GoldID        *string
	CreatedAt     time.Time
}

type LearningProposal struct {
	ProposalID             string
	SkillID                string
	PromptVersionID        *string
	ClusterKey             string
	Title                  string
	Rationale              string
	ProposedPromptPatch    string
	Status                 string
	SourceFailureCount     int
	Evidence               map[string]any
	ReviewerID             *string
	ReviewNotes            *string
	ReviewedAt             *time.Time
	CreatedPromptVersionID *string
	CreatedAt              time.Time
}

type ReplaySchedule struct {
	ScheduleID      string
	ReplayType      string
	SkillID         *string
	PromptVersionID *string
	CadenceDays     int
	NextRunAt       time.Time
	LastRunAt       *time.Time
	IsActive        bool
	CreatedBy       *string
	Payload         map[string]any
	CreatedAt       time.Time
}

func jsonText(value any) (string, error) {
	if value == nil {
		return "{}", nil
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

func nullable[T any](value *T) any {
	if value == nil {
		return nil
	}
	return *value
}

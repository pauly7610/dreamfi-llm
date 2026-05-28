package connectors

import (
	"context"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
)

type SyncService struct {
	Store *store.Store
	Onyx  *onyx.Client
	Now   func() time.Time
}

type SyncRequest struct {
	Connector ConnectorSpec
	Config    map[string]string
	Secret    string
	ActorID   string
	Trigger   string
	Limit     int
	RunID     string
	Adapter   Adapter
}

type SyncResult struct {
	Run store.ConnectorSyncRun
}

func (s SyncService) SyncConnector(ctx context.Context, request SyncRequest) (SyncResult, error) {
	now := s.now()
	trigger := request.Trigger
	if trigger == "" {
		trigger = "manual"
	}
	run := store.ConnectorSyncRun{
		SyncRunID:   request.RunID,
		ConnectorID: request.Connector.ConnectorID,
		Status:      "running",
		Trigger:     trigger,
		StartedAt:   now,
		Metadata:    map[string]any{"actor_id": request.ActorID},
	}
	if err := s.Store.CreateConnectorSyncRun(ctx, run); err != nil {
		return SyncResult{}, err
	}

	adapter := request.Adapter
	if adapter == nil {
		var ok bool
		adapter, ok = AdapterFor(request.Connector.ConnectorID)
		if !ok {
			reason := "adapter_not_registered"
			run.Status = "error"
			run.Reason = &reason
			completed := s.now()
			run.CompletedAt = &completed
			_ = s.Store.FinishConnectorSyncRun(ctx, run)
			return SyncResult{Run: run}, nil
		}
	}

	documents, err := adapter.FetchDocuments(ctx, request.Connector, request.Config, request.Secret, request.Limit)
	if err != nil {
		reason := err.Error()
		run.Status = "error"
		run.Reason = &reason
		run.ErrorCount = 1
		completed := s.now()
		run.CompletedAt = &completed
		_ = s.Store.FinishConnectorSyncRun(ctx, run)
		return SyncResult{Run: run}, err
	}

	run.PulledCount = len(documents)
	for _, document := range documents {
		sourceURL := stringPtrIfNotEmpty(document.SourceURL)
		onyxID := document.OnyxDocumentID()
		row := store.ConnectorDocument{
			ConnectorDocumentID: document.ConnectorID + ":" + document.ExternalID,
			ConnectorID:         document.ConnectorID,
			ExternalID:          document.ExternalID,
			Title:               document.Title,
			BodyText:            document.BodyText,
			SourceURL:           sourceURL,
			DocUpdatedAt:        document.UpdatedAt,
			ContentHash:         document.ContentHash(),
			Metadata:            document.OnyxMetadata(),
			SyncRunID:           &run.SyncRunID,
			OnyxDocumentID:      &onyxID,
			LastSeenAt:          s.now(),
			CreatedAt:           s.now(),
			UpdatedAt:           s.now(),
		}
		changed, err := s.Store.UpsertConnectorDocument(ctx, row)
		if err != nil {
			run.ErrorCount++
			continue
		}
		run.PersistedCount++
		if !changed {
			run.SkippedCount++
			continue
		}
		if s.Onyx != nil {
			result, err := s.Onyx.IngestDocument(ctx, onyx.IngestDocumentRequest{
				DocID:              onyxID,
				Text:               document.BodyText,
				SemanticIdentifier: document.Title,
				Metadata:           document.OnyxMetadata(),
				SourceURL:          document.SourceURL,
				DocUpdatedAt:       document.UpdatedAt.Format(time.RFC3339),
				Title:              document.Title,
			})
			if err != nil {
				run.ErrorCount++
				continue
			}
			onyxID = result.DocumentID
		}
		if err := s.Store.MarkConnectorDocumentIngested(ctx, document.ConnectorID, document.ExternalID, onyxID, s.now()); err != nil {
			run.ErrorCount++
			continue
		}
		run.IngestedCount++
	}

	completed := s.now()
	run.CompletedAt = &completed
	if run.ErrorCount > 0 {
		run.Status = "error"
	} else {
		run.Status = "success"
	}
	if err := s.Store.FinishConnectorSyncRun(ctx, run); err != nil {
		return SyncResult{}, err
	}
	return SyncResult{Run: run}, nil
}

func (s SyncService) now() time.Time {
	if s.Now != nil {
		return s.Now().UTC()
	}
	return time.Now().UTC()
}

func stringPtrIfNotEmpty(value string) *string {
	if value == "" {
		return nil
	}
	return &value
}

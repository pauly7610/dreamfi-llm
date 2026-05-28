package connectors

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
	_ "modernc.org/sqlite"
)

func TestSyncConnectorPersistsAndIngestsChangedDocumentsThroughOnyxClient(t *testing.T) {
	ctx := context.Background()
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
	db := openConnectorTestDB(t)
	repo := store.New(db, store.DialectSQLite)
	connector, _ := ByID("metabase")

	if err := repo.UpsertConnectorSetting(ctx, store.ConnectorSetting{
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

	onyxServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/onyx-api/ingestion" {
			t.Fatalf("path = %s", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer onyx-token" {
			t.Fatalf("authorization = %q", got)
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatalf("decode Onyx body error = %v", err)
		}
		document := body["document"].(map[string]any)
		metadata := document["metadata"].(map[string]any)
		scope := metadata["dreamfi_scope"].(map[string]any)
		sourceIDs := scope["source_ids"].([]any)
		if sourceIDs[0] != "metabase" {
			t.Fatalf("metadata scope = %#v", metadata)
		}
		writeJSON(t, w, map[string]any{"document_id": "onyx-doc-1", "already_existed": false})
	}))
	defer onyxServer.Close()

	service := SyncService{
		Store: repo,
		Onyx:  onyx.NewClient(onyxServer.URL, "onyx-token", onyx.WithRetryWait(0)),
		Now:   func() time.Time { return now },
	}
	result, err := service.SyncConnector(ctx, SyncRequest{
		Connector: connector,
		Config:    map[string]string{"base_url": "http://metabase.test"},
		Secret:    "metabase-token",
		ActorID:   "tester",
		RunID:     "sync-1",
		Adapter: StaticAdapter{Documents: []SourceDocument{{
			ConnectorID: "metabase",
			ExternalID:  "card:10",
			Title:       "KYC conversion",
			BodyText:    "KYC conversion dashboard",
			UpdatedAt:   now,
			Metadata:    map[string]any{"owner": "analytics"},
		}}},
	})
	if err != nil {
		t.Fatalf("SyncConnector error = %v", err)
	}
	if result.Run.Status != "success" || result.Run.PersistedCount != 1 || result.Run.IngestedCount != 1 {
		t.Fatalf("run = %#v", result.Run)
	}

	var onyxDocumentID string
	if err := db.QueryRowContext(ctx, "SELECT onyx_document_id FROM connector_documents WHERE connector_id = ? AND external_id = ?", "metabase", "card:10").Scan(&onyxDocumentID); err != nil {
		t.Fatalf("select connector document error = %v", err)
	}
	if onyxDocumentID != "onyx-doc-1" {
		t.Fatalf("onyxDocumentID = %q", onyxDocumentID)
	}
}

type StaticAdapter struct {
	Documents []SourceDocument
	Err       error
}

func (a StaticAdapter) FetchDocuments(context.Context, ConnectorSpec, map[string]string, string, int) ([]SourceDocument, error) {
	return a.Documents, a.Err
}

func openConnectorTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", "file:"+url.QueryEscape(t.Name())+"?mode=memory&cache=shared")
	if err != nil {
		t.Fatalf("sql.Open error = %v", err)
	}
	t.Cleanup(func() {
		_ = db.Close()
	})
	for _, stmt := range connectorTestSchema {
		if _, err := db.Exec(stmt); err != nil {
			t.Fatalf("schema error: %v\n%s", err, stmt)
		}
	}
	return db
}

var connectorTestSchema = []string{
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
}

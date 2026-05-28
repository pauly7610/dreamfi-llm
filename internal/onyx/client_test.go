package onyx

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPingReportsReachableOnlyOnOK(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/health" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	client := NewClient(server.URL, "onyx_pat_test", WithRetryWait(0))
	if got := client.Ping(context.Background()); got != "reachable" {
		t.Fatalf("Ping() = %q, want reachable", got)
	}
}

func TestListPersonasAttachesBearerAndRetriesServerErrors(t *testing.T) {
	calls := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if got := r.Header.Get("Authorization"); got != "Bearer onyx_pat_test" {
			t.Fatalf("Authorization = %q", got)
		}
		if calls == 1 {
			http.Error(w, "temporary", http.StatusInternalServerError)
			return
		}
		writeJSON(t, w, map[string]any{"personas": []map[string]any{{"id": 42, "name": "DreamFi", "description": "ProductOS"}}})
	}))
	defer server.Close()

	client := NewClient(server.URL, "onyx_pat_test", WithRetryWait(0))
	personas, err := client.ListPersonas(context.Background())
	if err != nil {
		t.Fatalf("ListPersonas() error = %v", err)
	}
	if calls != 2 {
		t.Fatalf("calls = %d, want 2", calls)
	}
	if len(personas) != 1 || personas[0].ID != 42 {
		t.Fatalf("personas = %#v", personas)
	}
}

func TestSendMessageSyncParsesStreamingChatResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/chat/send-chat-message" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"answer_piece":"Hello ","citations":{"1":"doc-1"}}` + "\n"))
		_, _ = w.Write([]byte(`{"answer_piece":"there","documents":[{"document_id":"doc-1"}],"message_id":91}` + "\n"))
	}))
	defer server.Close()

	client := NewClient(server.URL, "k", WithRetryWait(0))
	result, err := client.SendMessageSync(context.Background(), "sess-1", nil, "hello", nil)
	if err != nil {
		t.Fatalf("SendMessageSync() error = %v", err)
	}
	if result.Text != "Hello there" {
		t.Fatalf("Text = %q", result.Text)
	}
	if result.Citations[1] != "doc-1" {
		t.Fatalf("Citations = %#v", result.Citations)
	}
	if result.MessageID == nil || *result.MessageID != 91 {
		t.Fatalf("MessageID = %#v", result.MessageID)
	}
}

func TestIngestDocumentUsesExpectedOnyxPayload(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		document := payload["document"].(map[string]any)
		if document["source"] != "ingestion_api" {
			t.Fatalf("source = %v", document["source"])
		}
		writeJSON(t, w, map[string]any{"document_id": "onyx-doc-1", "already_existed": false})
	}))
	defer server.Close()

	client := NewClient(server.URL, "k", WithRetryWait(0))
	result, err := client.IngestDocument(context.Background(), IngestDocumentRequest{
		DocID:              "dreamfi:metabase:1",
		Text:               "Revenue dashboard",
		SemanticIdentifier: "Revenue",
		Metadata:           map[string]any{"dreamfi_scope": map[string]any{"source_ids": []string{"metabase"}}},
	})
	if err != nil {
		t.Fatalf("IngestDocument() error = %v", err)
	}
	if result.DocumentID != "onyx-doc-1" {
		t.Fatalf("DocumentID = %q", result.DocumentID)
	}
}

func writeJSON(t *testing.T, w http.ResponseWriter, value any) {
	t.Helper()
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(value); err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
}

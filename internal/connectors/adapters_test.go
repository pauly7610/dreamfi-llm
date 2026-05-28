package connectors

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRestAdapterFetchesMetabaseDocumentsWithConfiguredAuth(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/card" {
			t.Fatalf("path = %s", r.URL.Path)
		}
		if got := r.Header.Get("x-api-key"); got != "metabase-token" {
			t.Fatalf("x-api-key = %q", got)
		}
		writeJSON(t, w, []map[string]any{{
			"id":            10,
			"name":          "KYC conversion",
			"updated_at":    "2026-05-28T12:00:00Z",
			"dataset_query": map[string]any{"database": 1},
		}})
	}))
	defer server.Close()

	connector, _ := ByID("metabase")
	docs, err := (RestAdapter{Client: server.Client()}).FetchDocuments(
		context.Background(),
		connector,
		map[string]string{
			"base_url":     server.URL,
			"endpoints":    "/api/card",
			"product_area": "activation",
			"topic_ids":    "kyc,onboarding",
			"owner":        "analytics@dreamfi.com",
		},
		"metabase-token",
		10,
	)
	if err != nil {
		t.Fatalf("FetchDocuments error = %v", err)
	}
	if len(docs) != 1 {
		t.Fatalf("docs len = %d", len(docs))
	}
	if docs[0].ConnectorID != "metabase" || docs[0].ExternalID != "10" || docs[0].Title != "KYC conversion" {
		t.Fatalf("doc = %#v", docs[0])
	}
	if docs[0].Metadata["owner"] != "analytics@dreamfi.com" {
		t.Fatalf("metadata = %#v", docs[0].Metadata)
	}
}

func TestGoogleAnalyticsAdapterPostsConfiguredReportShape(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Fatalf("method = %s", r.Method)
		}
		if got := r.Header.Get("authorization"); got != "Bearer ga-token" {
			t.Fatalf("authorization = %q", got)
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatalf("decode request error = %v", err)
		}
		if len(body["dimensions"].([]any)) != 2 || len(body["metrics"].([]any)) != 2 {
			t.Fatalf("report body = %#v", body)
		}
		writeJSON(t, w, map[string]any{
			"rows": []map[string]any{{
				"dimensionValues": []map[string]string{{"value": "US"}},
				"metricValues":    []map[string]string{{"value": "12"}},
			}},
		})
	}))
	defer server.Close()

	connector, _ := ByID("ga")
	docs, err := (GoogleAnalyticsAdapter{Client: server.Client()}).FetchDocuments(
		context.Background(),
		connector,
		map[string]string{
			"base_url":    server.URL,
			"property_id": "987654",
			"start_date":  "2026-05-01",
			"end_date":    "2026-05-28",
			"dimensions":  "country,deviceCategory",
			"metrics":     "sessions,engagedSessions",
		},
		"ga-token",
		10,
	)
	if err != nil {
		t.Fatalf("FetchDocuments error = %v", err)
	}
	if len(docs) != 1 || docs[0].ConnectorID != "ga" {
		t.Fatalf("docs = %#v", docs)
	}
}

func writeJSON(t *testing.T, w http.ResponseWriter, value any) {
	t.Helper()
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(value); err != nil {
		t.Fatalf("Encode error = %v", err)
	}
}

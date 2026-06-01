package httpapi

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
)

func TestRouterServesReadyWithoutAuth(t *testing.T) {
	router := NewRouter(config.Settings{AuthEnabled: true}, onyx.NewClient("http://onyx.invalid", ""))

	req := httptest.NewRequest(http.MethodGet, "/ready", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
	var body map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if body["status"] != "ready" {
		t.Fatalf("body = %#v", body)
	}
}

func TestRouterServesHealthWithOnyxStatus(t *testing.T) {
	onyxServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer onyxServer.Close()

	router := NewRouter(config.Settings{AuthEnabled: true}, onyx.NewClient(onyxServer.URL, ""))
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	var body map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if body["onyx"] != "reachable" {
		t.Fatalf("body = %#v", body)
	}
}

func TestRouterServesTemplConsoleWithAuth(t *testing.T) {
	router := NewRouter(
		config.Settings{AuthEnabled: true, AuthUsername: "dreamfi", AuthPassword: "secret"},
		onyx.NewClient("http://onyx.invalid", ""),
	)
	req := httptest.NewRequest(http.MethodGet, "/console", nil)
	req.Header.Set("Authorization", "Basic "+base64.StdEncoding.EncodeToString([]byte("dreamfi:secret")))
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if contentType := rec.Header().Get("Content-Type"); !strings.Contains(contentType, "text/html") {
		t.Fatalf("Content-Type = %q", contentType)
	}
	if !strings.Contains(rec.Body.String(), "DreamFi ProductOS") {
		t.Fatalf("console did not render ProductOS shell: %s", rec.Body.String())
	}
}

func TestConsoleRoutesRenderDarkConsolePages(t *testing.T) {
	router := NewRouter(config.Settings{AuthEnabled: false}, nil)
	cases := []struct {
		path  string
		wants []string
	}{
		{path: "/console", wants: []string{"Ask DreamFi", "Open threads", "Sources"}},
		{path: "/console/knowledge/ask", wants: []string{"Ask DreamFi", "Ask with receipts", "Sources this answer can use"}},
		{path: "/console/ask", wants: []string{"Ask DreamFi", "Ask with receipts", "Sources this answer can use"}},
		{path: "/console/topics", wants: []string{"Topic rooms", "KYC conversion"}},
		{path: "/console/topics/kyc-conversion", wants: []string{"Topic rooms", "Why did KYC conversion drop 4.2 pts?"}},
		{path: "/console/integrations", wants: []string{"Source directory", "Jira", "NetXD"}},
		{path: "/console/integrations/jira", wants: []string{"Source directory", "Jira", "NetXD"}},
		{path: "/console/sources", wants: []string{"Source directory", "Jira", "NetXD"}},
		{path: "/console/review", wants: []string{"Review queue", "Review posture"}},
		{path: "/console/artifacts", wants: []string{"Artifact library", "Review queue"}},
		{path: "/console/trust", wants: []string{"Trust posture", "Trust, measured."}},
		{path: "/console/settings", wants: []string{"Connector settings", "Onyx native"}},
	}

	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, tc.path, nil)
			rec := httptest.NewRecorder()
			router.ServeHTTP(rec, req)
			if rec.Code != http.StatusOK {
				t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
			}
			html := rec.Body.String()
			for _, want := range tc.wants {
				if !strings.Contains(html, want) {
					t.Fatalf("console HTML for %s missing %q", tc.path, want)
				}
			}
		})
	}
}

func TestRouterAddsRequestID(t *testing.T) {
	router := NewRouter(config.Settings{AuthEnabled: true}, onyx.NewClient("http://onyx.invalid", ""))
	req := httptest.NewRequest(http.MethodGet, "/ready", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Header().Get("X-Request-ID") == "" {
		t.Fatalf("X-Request-ID was not set")
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("X-Content-Type-Options = %q, want nosniff", got)
	}
	if got := rec.Header().Get("X-Frame-Options"); got != "DENY" {
		t.Fatalf("X-Frame-Options = %q, want DENY", got)
	}
}

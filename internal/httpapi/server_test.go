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

func TestRouterAddsRequestID(t *testing.T) {
	router := NewRouter(config.Settings{AuthEnabled: true}, onyx.NewClient("http://onyx.invalid", ""))
	req := httptest.NewRequest(http.MethodGet, "/ready", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Header().Get("X-Request-ID") == "" {
		t.Fatalf("X-Request-ID was not set")
	}
}

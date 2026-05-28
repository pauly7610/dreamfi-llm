package httpapi

import (
	"encoding/base64"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/pauly7610/dreamfi-llm/internal/config"
)

func TestAuthExemptsHealthChecks(t *testing.T) {
	handler := AuthMiddleware(config.Settings{AuthEnabled: true}, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := AuthFromContext(r.Context())
		if auth.ActorID != "healthcheck" || auth.AuthMethod != "exempt" {
			t.Fatalf("auth context = %#v", auth)
		}
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/ready", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestAuthRejectsUnconfiguredSecrets(t *testing.T) {
	handler := AuthMiddleware(config.Settings{AuthEnabled: true}, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("handler should not be called")
	}))

	req := httptest.NewRequest(http.MethodGet, "/console", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestAuthAllowsBasicCredentials(t *testing.T) {
	settings := config.Settings{AuthEnabled: true, AuthUsername: "dreamfi", AuthPassword: "secret"}
	handler := AuthMiddleware(settings, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := AuthFromContext(r.Context())
		if auth.ActorID != "dreamfi" || auth.AuthMethod != "basic" {
			t.Fatalf("auth context = %#v", auth)
		}
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/console", nil)
	req.Header.Set("Authorization", "Basic "+base64.StdEncoding.EncodeToString([]byte("dreamfi:secret")))
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestAuthAllowsBearerToken(t *testing.T) {
	settings := config.Settings{AuthEnabled: true, APIToken: "token"}
	handler := AuthMiddleware(settings, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := AuthFromContext(r.Context())
		if auth.ActorID != "api_token" || auth.AuthMethod != "bearer" {
			t.Fatalf("auth context = %#v", auth)
		}
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/console", nil)
	req.Header.Set("Authorization", "Bearer token")
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestAuthRejectsInvalidCredentials(t *testing.T) {
	settings := config.Settings{AuthEnabled: true, AuthUsername: "dreamfi", AuthPassword: "secret"}
	handler := AuthMiddleware(settings, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("handler should not be called")
	}))

	req := httptest.NewRequest(http.MethodGet, "/console", nil)
	req.Header.Set("Authorization", "Basic "+base64.StdEncoding.EncodeToString([]byte("dreamfi:nope")))
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", rec.Code)
	}
	if rec.Header().Get("WWW-Authenticate") == "" {
		t.Fatalf("WWW-Authenticate header was not set")
	}
}

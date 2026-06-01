package httpapi

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/a-h/templ"
	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
	"github.com/pauly7610/dreamfi-llm/web/templates"
)

type Server struct {
	settings config.Settings
	onyx     *onyx.Client
	store    *store.Store
	now      func() time.Time
}

type Option func(*Server)

func WithStore(repo *store.Store) Option {
	return func(s *Server) {
		s.store = repo
	}
}

func WithNow(now func() time.Time) Option {
	return func(s *Server) {
		s.now = now
	}
}

func NewRouter(settings config.Settings, onyxClient *onyx.Client, opts ...Option) http.Handler {
	server := &Server{settings: settings, onyx: onyxClient}
	for _, opt := range opts {
		opt(server)
	}
	mux := http.NewServeMux()

	mux.HandleFunc("GET /ready", server.ready)
	mux.HandleFunc("GET /health", server.health)
	mux.HandleFunc("GET /static/dreamfi-logo.svg", server.dreamfiLogo)
	mux.HandleFunc("GET /api/ops/status", server.opsStatus)
	mux.HandleFunc("GET /api/console", server.consoleData)
	mux.HandleFunc("POST /api/ask", server.ask)
	mux.HandleFunc("GET /api/workflows", server.workflowCatalog)
	mux.HandleFunc("POST /api/workflows/generate", server.generateWorkflow)
	mux.HandleFunc("GET /console", server.console)
	mux.HandleFunc("GET /console/", server.console)
	mux.HandleFunc("GET /", server.root)

	return securityHeadersMiddleware(requestIDMiddleware(AuthMiddleware(settings, mux)))
}

func (s *Server) ready(w http.ResponseWriter, _ *http.Request) {
	writeJSONResponse(w, http.StatusOK, map[string]string{"status": "ready"})
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSONResponse(w, http.StatusOK, map[string]string{
		"status": "ok",
		"onyx":   s.onyx.Ping(r.Context()),
	})
}

func (s *Server) opsStatus(w http.ResponseWriter, r *http.Request) {
	onyxStatus := s.onyx.Ping(r.Context())
	status := "ok"
	if onyxStatus != "reachable" {
		status = "degraded"
	}
	writeJSONResponse(w, http.StatusOK, map[string]any{
		"status": status,
		"onyx": map[string]string{
			"status": onyxStatus,
		},
		"database": map[string]string{
			"url":    s.settings.ResolvedDatabaseURL(),
			"status": "configured",
		},
	})
}

func (s *Server) consoleData(w http.ResponseWriter, r *http.Request) {
	payload, err := s.consolePayload(r.Context(), s.onyxStatus(r.Context()))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "console payload failed: "+err.Error())
		return
	}
	writeJSONResponse(w, http.StatusOK, payload)
}

func (s *Server) console(w http.ResponseWriter, r *http.Request) {
	payload, err := s.consolePayload(r.Context(), s.onyxStatus(r.Context()))
	if err != nil {
		http.Error(w, "console payload failed", http.StatusInternalServerError)
		return
	}
	renderComponent(w, r, templates.ConsoleShell(consoleTemplateData(payload, normalizeConsolePath(r.URL.Path))))
}

func (s *Server) root(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/" {
		http.Redirect(w, r, "/console", http.StatusFound)
		return
	}
	http.NotFound(w, r)
}

func renderComponent(w http.ResponseWriter, r *http.Request, component templ.Component) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := component.Render(r.Context(), w); err != nil {
		http.Error(w, "render failed", http.StatusInternalServerError)
	}
}

func writeJSONResponse(w http.ResponseWriter, statusCode int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

func requestIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := strings.TrimSpace(r.Header.Get("X-Request-ID"))
		if requestID == "" {
			requestID = newRequestID()
		}
		w.Header().Set("X-Request-ID", requestID)
		next.ServeHTTP(w, r)
	})
}

func securityHeadersMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		headers := w.Header()
		headers.Set("X-Content-Type-Options", "nosniff")
		headers.Set("X-Frame-Options", "DENY")
		headers.Set("Referrer-Policy", "strict-origin-when-cross-origin")
		headers.Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
		headers.Set("Cross-Origin-Opener-Policy", "same-origin")
		next.ServeHTTP(w, r)
	})
}

func newRequestID() string {
	var raw [16]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return "request-id-unavailable"
	}
	return hex.EncodeToString(raw[:])
}

func newEntityID(prefix string) string {
	return prefix + "-" + newRequestID()
}

func (s *Server) currentTime() time.Time {
	if s.now != nil {
		return s.now().UTC()
	}
	return time.Now().UTC()
}

func (s *Server) onyxStatus(ctx context.Context) string {
	if s.onyx == nil {
		return "unconfigured"
	}
	return s.onyx.Ping(ctx)
}

func primaryNav() []templates.NavItem {
	return []templates.NavItem{
		{Label: "Home", Href: "/console"},
		{Label: "Ask", Href: "/console/knowledge/ask"},
		{Label: "Inbox", Href: "/console/review"},
		{Label: "Topics", Href: "/console/topics"},
		{Label: "Sources", Href: "/console/integrations"},
		{Label: "Artifacts", Href: "/console/artifacts"},
		{Label: "Trust", Href: "/console/trust"},
		{Label: "Settings", Href: "/console/settings"},
	}
}

func normalizeConsolePath(path string) string {
	clean := strings.TrimRight(path, "/")
	if clean == "" || clean == "/console" {
		return "/console"
	}
	if clean == "/console/ask" || strings.HasPrefix(clean, "/console/ask/") {
		return "/console/knowledge/ask"
	}
	if clean == "/console/knowledge" {
		return "/console/knowledge/ask"
	}
	if clean == "/console/sources" || strings.HasPrefix(clean, "/console/sources/") {
		return "/console/integrations" + strings.TrimPrefix(clean, "/console/sources")
	}
	if clean == "/console/inbox" || strings.HasPrefix(clean, "/console/inbox/") {
		return "/console/review" + strings.TrimPrefix(clean, "/console/inbox")
	}
	if clean == "/console/generators" || strings.HasPrefix(clean, "/console/generators/") {
		return "/console/generate/weekly-brief"
	}
	if clean == "/console/planning" || strings.HasPrefix(clean, "/console/planning/") {
		return "/console/topics"
	}
	if clean == "/console/metrics" || strings.HasPrefix(clean, "/console/metrics/") {
		return "/console/integrations/metabase"
	}
	return clean
}

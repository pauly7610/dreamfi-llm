package httpapi

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/a-h/templ"
	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/web/templates"
)

type Server struct {
	settings config.Settings
	onyx     *onyx.Client
}

func NewRouter(settings config.Settings, onyxClient *onyx.Client) http.Handler {
	server := &Server{settings: settings, onyx: onyxClient}
	mux := http.NewServeMux()

	mux.HandleFunc("GET /ready", server.ready)
	mux.HandleFunc("GET /health", server.health)
	mux.HandleFunc("GET /api/ops/status", server.opsStatus)
	mux.HandleFunc("GET /api/console", server.consoleData)
	mux.HandleFunc("GET /console", server.console)
	mux.HandleFunc("GET /console/", server.console)
	mux.HandleFunc("GET /", server.root)

	return requestIDMiddleware(AuthMiddleware(settings, mux))
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
	writeJSONResponse(w, http.StatusOK, map[string]any{
		"status": "ok",
		"onyx":   s.onyx.Ping(r.Context()),
		"nav":    primaryNav(),
	})
}

func (s *Server) console(w http.ResponseWriter, r *http.Request) {
	data := templates.ConsoleData{
		ProductName: "DreamFi ProductOS",
		Status:      s.onyx.Ping(r.Context()),
		PrimaryNav:  primaryNav(),
	}
	renderComponent(w, r, templates.ConsoleShell(data))
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

func newRequestID() string {
	var raw [16]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return "request-id-unavailable"
	}
	return hex.EncodeToString(raw[:])
}

func primaryNav() []templates.NavItem {
	return []templates.NavItem{
		{Label: "Ask", Href: "/console/ask"},
		{Label: "Topics", Href: "/console/topics"},
		{Label: "Sources", Href: "/console/sources"},
		{Label: "Artifacts", Href: "/console/artifacts"},
		{Label: "Trust", Href: "/console/trust"},
		{Label: "Settings", Href: "/console/settings"},
	}
}

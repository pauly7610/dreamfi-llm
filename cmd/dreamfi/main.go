package main

import (
	"log/slog"
	"net/http"
	"os"

	"github.com/pauly7610/dreamfi-llm/internal/config"
	"github.com/pauly7610/dreamfi-llm/internal/httpapi"
	"github.com/pauly7610/dreamfi-llm/internal/onyx"
	"github.com/pauly7610/dreamfi-llm/internal/store"
)

func main() {
	settings := config.Load()
	client := onyx.NewClient(settings.OnyxBaseURL, settings.OnyxAPIKey)
	db, dialect, err := store.OpenDatabase(settings.ResolvedDatabaseURL())
	if err != nil {
		slog.Error("DreamFi database configuration failed", "error", err)
		os.Exit(1)
	}
	defer db.Close()
	router := httpapi.NewRouter(settings, client, httpapi.WithStore(store.New(db, dialect)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "5001"
	}

	addr := ":" + port
	slog.Info("starting DreamFi Go service", "addr", addr)
	if err := http.ListenAndServe(addr, router); err != nil {
		slog.Error("DreamFi Go service stopped", "error", err)
		os.Exit(1)
	}
}

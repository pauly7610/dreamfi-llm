package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

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

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	server := &http.Server{
		Addr:              addr,
		Handler:           router,
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			slog.Error("DreamFi Go service shutdown failed", "error", err)
		}
	}()

	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		slog.Error("DreamFi Go service stopped", "error", err)
		os.Exit(1)
	}
}

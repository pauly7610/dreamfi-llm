package config

import (
	"net/url"
	"os"
	"strconv"
	"strings"
)

const LocalDatabaseURL = "postgres://dreamfi:dreamfi@localhost:5433/dreamfi?sslmode=disable"

type Settings struct {
	DatabaseURL string
	PGHost      string
	PGPort      int
	PGUser      string
	PGPassword  string
	PGDatabase  string

	OnyxBaseURL string
	OnyxAPIKey  string

	AuthEnabled  bool
	AuthUsername string
	AuthPassword string
	APIToken     string

	AuditEnabled  bool
	AuditLogReads bool

	ConfidenceThreshold  float64
	ImprovementThreshold float64
	AskSearchLimit       int
}

func Load() Settings {
	return Settings{
		DatabaseURL: envString("DATABASE_URL", ""),
		PGHost:      firstEnvString("", "PGHOST", "PG_HOST"),
		PGPort:      firstEnvInt(0, "PGPORT", "PG_PORT"),
		PGUser:      firstEnvString("", "PGUSER", "PG_USER"),
		PGPassword:  firstEnvString("", "PGPASSWORD", "PG_PASSWORD"),
		PGDatabase:  firstEnvString("", "PGDATABASE", "PG_DATABASE"),

		OnyxBaseURL: envString("ONYX_BASE_URL", "http://localhost:8080"),
		OnyxAPIKey:  envString("ONYX_API_KEY", ""),

		AuthEnabled:  envBool("DREAMFI_AUTH_ENABLED", true),
		AuthUsername: envString("DREAMFI_AUTH_USERNAME", "dreamfi"),
		AuthPassword: envString("DREAMFI_AUTH_PASSWORD", ""),
		APIToken:     firstEnvString("", "DREAMFI_API_TOKEN", "DREAMFI_API_KEY"),

		AuditEnabled:  envBool("DREAMFI_AUDIT_ENABLED", true),
		AuditLogReads: envBool("DREAMFI_AUDIT_LOG_READS", true),

		ConfidenceThreshold:  envFloat("DREAMFI_CONFIDENCE_THRESHOLD", 0.75),
		ImprovementThreshold: envFloat("DREAMFI_IMPROVEMENT_THRESHOLD", 0.02),
		AskSearchLimit:       envInt("DREAMFI_ASK_SEARCH_LIMIT", 5),
	}
}

func NormalizeDatabaseURL(raw string) string {
	value := strings.TrimSpace(raw)
	switch {
	case strings.HasPrefix(value, "postgresql+psycopg://"):
		return "postgres://" + strings.TrimPrefix(value, "postgresql+psycopg://")
	case strings.HasPrefix(value, "postgresql://"):
		return "postgres://" + strings.TrimPrefix(value, "postgresql://")
	default:
		return value
	}
}

func (s Settings) ResolvedDatabaseURL() string {
	if strings.TrimSpace(s.DatabaseURL) != "" {
		return NormalizeDatabaseURL(s.DatabaseURL)
	}

	if s.PGHost != "" && s.PGUser != "" && s.PGPassword != "" && s.PGDatabase != "" {
		port := s.PGPort
		if port == 0 {
			port = 5432
		}
		u := url.URL{
			Scheme: "postgres",
			User:   url.UserPassword(s.PGUser, s.PGPassword),
			Host:   s.PGHost + ":" + strconv.Itoa(port),
			Path:   "/" + s.PGDatabase,
		}
		query := u.Query()
		query.Set("sslmode", "disable")
		u.RawQuery = query.Encode()
		return u.String()
	}

	return LocalDatabaseURL
}

func envString(key string, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func envBool(key string, fallback bool) bool {
	value, ok := os.LookupEnv(key)
	if !ok {
		return fallback
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envInt(key string, fallback int) int {
	value, ok := os.LookupEnv(key)
	if !ok {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envFloat(key string, fallback float64) float64 {
	value, ok := os.LookupEnv(key)
	if !ok {
		return fallback
	}
	parsed, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return fallback
	}
	return parsed
}

func firstEnvString(fallback string, keys ...string) string {
	for _, key := range keys {
		if value, ok := os.LookupEnv(key); ok {
			return value
		}
	}
	return fallback
}

func firstEnvInt(fallback int, keys ...string) int {
	for _, key := range keys {
		if value, ok := os.LookupEnv(key); ok {
			parsed, err := strconv.Atoi(value)
			if err == nil {
				return parsed
			}
		}
	}
	return fallback
}

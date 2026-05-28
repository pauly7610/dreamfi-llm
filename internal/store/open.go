package store

import (
	"database/sql"
	"errors"
	"strings"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "modernc.org/sqlite"
)

func OpenDatabase(databaseURL string) (*sql.DB, Dialect, error) {
	value := strings.TrimSpace(databaseURL)
	if value == "" {
		return nil, "", errors.New("database URL is required")
	}

	switch {
	case strings.HasPrefix(value, "postgres://"), strings.HasPrefix(value, "postgresql://"):
		normalized := strings.Replace(value, "postgresql://", "postgres://", 1)
		db, err := sql.Open("pgx", normalized)
		return db, DialectPostgres, err
	case strings.HasPrefix(value, "sqlite://"):
		dsn := strings.TrimPrefix(value, "sqlite://")
		if strings.TrimSpace(dsn) == "" {
			return nil, "", errors.New("sqlite database path is required")
		}
		db, err := sql.Open("sqlite", dsn)
		return db, DialectSQLite, err
	case strings.HasPrefix(value, "file:"), value == ":memory:", strings.HasSuffix(value, ".db"):
		db, err := sql.Open("sqlite", value)
		return db, DialectSQLite, err
	default:
		return nil, "", errors.New("unsupported database URL scheme")
	}
}

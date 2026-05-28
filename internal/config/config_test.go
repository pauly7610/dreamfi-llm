package config

import "testing"

func TestNormalizeDatabaseURLConvertsPythonDialectForGoDrivers(t *testing.T) {
	got := NormalizeDatabaseURL("postgresql+psycopg://user:pass@db:5432/dreamfi?sslmode=require")
	want := "postgres://user:pass@db:5432/dreamfi?sslmode=require"
	if got != want {
		t.Fatalf("NormalizeDatabaseURL() = %q, want %q", got, want)
	}
}

func TestResolvedDatabaseURLPrefersExplicitDatabaseURL(t *testing.T) {
	settings := Settings{
		DatabaseURL: "postgresql://user:pass@db/dreamfi",
		PGHost:      "ignored",
		PGUser:      "ignored",
		PGPassword:  "ignored",
		PGDatabase:  "ignored",
	}

	got := settings.ResolvedDatabaseURL()
	want := "postgres://user:pass@db/dreamfi"
	if got != want {
		t.Fatalf("ResolvedDatabaseURL() = %q, want %q", got, want)
	}
}

func TestResolvedDatabaseURLBuildsFromPGVariables(t *testing.T) {
	settings := Settings{
		PGHost:     "postgres.internal",
		PGUser:     "dream fi",
		PGPassword: "secret/value",
		PGDatabase: "dreamfi",
	}

	got := settings.ResolvedDatabaseURL()
	want := "postgres://dream%20fi:secret%2Fvalue@postgres.internal:5432/dreamfi?sslmode=disable"
	if got != want {
		t.Fatalf("ResolvedDatabaseURL() = %q, want %q", got, want)
	}
}

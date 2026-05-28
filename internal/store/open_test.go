package store

import "testing"

func TestOpenDatabaseDetectsSQLiteDSNs(t *testing.T) {
	db, dialect, err := OpenDatabase("file:workflow-test?mode=memory&cache=shared")
	if err != nil {
		t.Fatalf("OpenDatabase() error = %v", err)
	}
	defer db.Close()
	if dialect != DialectSQLite {
		t.Fatalf("dialect = %q, want sqlite", dialect)
	}
}

func TestOpenDatabaseDetectsPostgresURLsWithoutConnecting(t *testing.T) {
	db, dialect, err := OpenDatabase("postgresql://dreamfi:dreamfi@localhost:5433/dreamfi?sslmode=disable")
	if err != nil {
		t.Fatalf("OpenDatabase() error = %v", err)
	}
	defer db.Close()
	if dialect != DialectPostgres {
		t.Fatalf("dialect = %q, want postgres", dialect)
	}
}

func TestOpenDatabaseRejectsUnsupportedScheme(t *testing.T) {
	_, _, err := OpenDatabase("mysql://dreamfi:dreamfi@localhost/dreamfi")
	if err == nil {
		t.Fatalf("OpenDatabase() error = nil, want unsupported scheme")
	}
}

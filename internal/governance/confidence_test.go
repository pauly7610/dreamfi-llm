package governance

import (
	"math"
	"testing"
	"time"
)

func TestConfidenceZeroWhenNoCitations(t *testing.T) {
	result := NewConfidenceScorer(14).Score(1, 1, 0, true)
	if result.Confidence != 0 {
		t.Fatalf("confidence = %v, want 0", result.Confidence)
	}
}

func TestConfidenceHalvedOnHardGateFail(t *testing.T) {
	scorer := NewConfidenceScorer(14)
	passing := scorer.Score(1, 1, 5, true).Confidence
	failing := scorer.Score(1, 1, 5, false).Confidence
	if math.Abs(failing-passing*0.5) > 1e-6 {
		t.Fatalf("failing = %v, passing = %v", failing, passing)
	}
}

func TestFreshnessZeroWhenNoDates(t *testing.T) {
	if got := NewConfidenceScorer(14).FreshnessFromUpdatedAt(nil, time.Now().UTC()); got != 0 {
		t.Fatalf("freshness = %v, want 0", got)
	}
}

func TestFreshnessDecaysOverTime(t *testing.T) {
	now := time.Date(2026, 5, 28, 12, 0, 0, 0, time.UTC)
	scorer := NewConfidenceScorer(14)
	fresh := scorer.FreshnessFromUpdatedAt([]time.Time{now}, now)
	old := scorer.FreshnessFromUpdatedAt([]time.Time{now.AddDate(0, 0, -14)}, now)
	if fresh <= old {
		t.Fatalf("fresh = %v, old = %v", fresh, old)
	}
	if math.Abs(old-0.5) > 1e-3 {
		t.Fatalf("old = %v, want about 0.5", old)
	}
}

package governance

import (
	"strings"
	"testing"
)

func TestPromotionFirstVersionAllowed(t *testing.T) {
	decision := NewPromotionGate(0.02).Decide(0.8, nil, nil, nil)
	if !decision.Promotable || decision.Improvement != nil {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPromotionBlocksRegression(t *testing.T) {
	previous := 0.8
	decision := NewPromotionGate(0.02).Decide(0.78, &previous, nil, nil)
	if decision.Promotable || !strings.Contains(decision.Reason, "REGRESSION") {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPromotionAllowsMeaningfulImprovement(t *testing.T) {
	previous := 0.8
	decision := NewPromotionGate(0.02).Decide(0.84, &previous, nil, nil)
	if !decision.Promotable {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPromotionBlocksFlatScore(t *testing.T) {
	previous := 0.8
	decision := NewPromotionGate(0.02).Decide(0.8, &previous, nil, nil)
	if decision.Promotable {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPromotionBlocksGoldRegression(t *testing.T) {
	decision := NewPromotionGate(0.02).Decide(0.9, nil, []GoldResult{{GoldID: "g1", Prev: ResultPass, New: ResultFail}}, nil)
	if decision.Promotable || !strings.Contains(decision.Reason, "blocked_by_regression") {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPublishGuardBlocksFailedHardGate(t *testing.T) {
	confidence := 0.99
	if NewPublishGuard(0.75).Check("fail", &confidence).Allowed {
		t.Fatal("failed hard gate should not publish")
	}
}

func TestPublishGuardBlocksLowConfidence(t *testing.T) {
	confidence := 0.4
	decision := NewPublishGuard(0.75).Check("pass", &confidence)
	if decision.Allowed || !strings.Contains(decision.Reason, "Low confidence") {
		t.Fatalf("decision = %#v", decision)
	}
}

func TestPublishGuardAllowsGoodOutput(t *testing.T) {
	confidence := 0.8
	if !NewPublishGuard(0.75).Check("pass", &confidence).Allowed {
		t.Fatal("good output should publish")
	}
}

func TestPublishGuardBlocksMissingConfidence(t *testing.T) {
	if NewPublishGuard(0.75).Check("pass", nil).Allowed {
		t.Fatal("missing confidence should not publish")
	}
}

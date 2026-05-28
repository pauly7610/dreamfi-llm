package governance

import (
	"fmt"
	"sort"
	"strings"
)

type ResultStatus string

const (
	ResultPass ResultStatus = "pass"
	ResultFail ResultStatus = "fail"
)

type GoldResult struct {
	GoldID string
	Prev   ResultStatus
	New    ResultStatus
}

type PromotionDecision struct {
	Promotable  bool
	Reason      string
	Improvement *float64
}

type PublishDecision struct {
	Allowed bool
	Reason  string
}

type PromotionGate struct {
	ImprovementThreshold float64
}

func NewPromotionGate(threshold float64) PromotionGate {
	if threshold == 0 {
		threshold = 0.02
	}
	return PromotionGate{ImprovementThreshold: threshold}
}

func (g PromotionGate) Decide(newScore float64, previousScore *float64, regressionFailures []GoldResult, canaryFailures []GoldResult) PromotionDecision {
	if len(regressionFailures) > 0 {
		return PromotionDecision{Promotable: false, Reason: "blocked_by_regression:" + goldIDs("regression", regressionFailures)}
	}
	if previousScore == nil {
		if len(canaryFailures) > 0 {
			return PromotionDecision{Promotable: true, Reason: "promote_with_canary_alert:" + goldIDs("canary", canaryFailures)}
		}
		return PromotionDecision{Promotable: true, Reason: "eligible"}
	}

	improvement := newScore - *previousScore
	if newScore < *previousScore {
		return PromotionDecision{
			Promotable:  false,
			Reason:      fmt.Sprintf("REGRESSION: %.4f < %.4f", newScore, *previousScore),
			Improvement: &improvement,
		}
	}
	if improvement < g.ImprovementThreshold {
		return PromotionDecision{
			Promotable:  false,
			Reason:      fmt.Sprintf("Improvement %.4f below threshold %.4f", improvement, g.ImprovementThreshold),
			Improvement: &improvement,
		}
	}
	if len(canaryFailures) > 0 {
		return PromotionDecision{Promotable: true, Reason: "promote_with_canary_alert:" + goldIDs("canary", canaryFailures), Improvement: &improvement}
	}
	return PromotionDecision{Promotable: true, Reason: "eligible", Improvement: &improvement}
}

type PublishGuard struct {
	ConfidenceThreshold float64
}

func NewPublishGuard(threshold float64) PublishGuard {
	if threshold == 0 {
		threshold = 0.75
	}
	return PublishGuard{ConfidenceThreshold: threshold}
}

func (g PublishGuard) Check(passFail string, confidence *float64) PublishDecision {
	if passFail != string(ResultPass) {
		return PublishDecision{Allowed: false, Reason: "Hard gate failed"}
	}
	if confidence == nil {
		return PublishDecision{Allowed: false, Reason: "Low confidence: missing confidence score"}
	}
	if *confidence < g.ConfidenceThreshold {
		return PublishDecision{Allowed: false, Reason: fmt.Sprintf("Low confidence: %.3f < %.3f", *confidence, g.ConfidenceThreshold)}
	}
	return PublishDecision{Allowed: true, Reason: "eligible"}
}

func goldIDs(prefix string, results []GoldResult) string {
	ids := make([]string, 0, len(results))
	for _, result := range results {
		ids = append(ids, prefix+":"+result.GoldID)
	}
	sort.Strings(ids)
	return strings.Join(ids, ",")
}

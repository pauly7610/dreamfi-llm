package governance

import (
	"math"
	"time"
)

type ConfidenceResult struct {
	Confidence     float64
	FreshnessScore float64
	CitationCount  int
	HardGatePassed bool
	EvalScore      float64
	Reasoning      []string
}

type ConfidenceScorer struct {
	FreshnessHalflifeDays float64
}

func NewConfidenceScorer(halflifeDays float64) ConfidenceScorer {
	if halflifeDays == 0 {
		halflifeDays = 14
	}
	return ConfidenceScorer{FreshnessHalflifeDays: halflifeDays}
}

func (s ConfidenceScorer) Score(evalScore float64, freshnessScore float64, citationCount int, hardGatePassed bool) ConfidenceResult {
	e := clamp01(evalScore)
	f := clamp01(freshnessScore)
	citationFactor := math.Min(float64(citationCount), 5) / 5
	hardGateFactor := 1.0
	if !hardGatePassed {
		hardGateFactor = 0.5
	}
	confidence := round3(e * f * citationFactor * hardGateFactor)
	return ConfidenceResult{
		Confidence:     confidence,
		FreshnessScore: f,
		CitationCount:  citationCount,
		HardGatePassed: hardGatePassed,
		EvalScore:      e,
		Reasoning: []string{
			"eval_score",
			"freshness",
			"citations",
			"hard_gate",
		},
	}
}

func (s ConfidenceScorer) FreshnessFromUpdatedAt(updatedAts []time.Time, now time.Time) float64 {
	if len(updatedAts) == 0 {
		return 0
	}
	if now.IsZero() {
		now = time.Now().UTC()
	}
	values := make([]float64, 0, len(updatedAts))
	for _, updatedAt := range updatedAts {
		if updatedAt.IsZero() {
			continue
		}
		ageDays := math.Max(0, now.Sub(updatedAt).Hours()/24)
		values = append(values, math.Exp(-math.Log(2)*ageDays/s.FreshnessHalflifeDays))
	}
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, value := range values {
		sum += value
	}
	return sum / float64(len(values))
}

func clamp01(value float64) float64 {
	return math.Max(0, math.Min(1, value))
}

func round3(value float64) float64 {
	return math.Round(value*1000) / 1000
}

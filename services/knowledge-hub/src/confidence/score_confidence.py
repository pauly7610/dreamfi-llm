"""
Confidence scoring module for knowledge hub.

Implements ADR-005: confidence = eval_score × freshness × citation_count × hard_gate
"""

from typing import Dict, Any, List, Optional


class ConfidenceScorer:
    """Calculates confidence scores for generated outputs."""
    
    def __init__(self):
        # Thresholds
        self.freshness_threshold = 0.8
        self.min_high_confidence = 0.75
    
    def score(
        self,
        eval_score: float,
        freshness_score: float,
        citation_count: int,
        hard_gate_passed: bool
    ) -> Dict[str, Any]:
        """
        Calculate confidence score with breakdown.
        
        Args:
            eval_score: Model evaluation (0-1)
            freshness_score: Data freshness (0-1)
            citation_count: Number of citations
            hard_gate_passed: Whether hard gate criteria passed
        
        Returns:
        {
            'confidence': float (0-1),
            'breakdown': {
                'eval_score': float,
                'freshness_score': float,
                'freshness_factor': float,
                'citation_count': int,
                'citation_factor': float,
                'hard_gate_passed': bool,
                'hard_gate_factor': float,
                'reasoning': [str]
            }
        }
        """
        # Ensure inputs are in valid range
        eval_score = max(0.0, min(1.0, eval_score))
        freshness_score = max(0.0, min(1.0, freshness_score))
        hard_gate_factor = 1.0 if hard_gate_passed else 0.5
        
        # Citation factor: min(count, 5) / 5
        citation_factor = min(citation_count, 5) / 5.0
        
        # Calculate confidence
        confidence = eval_score * freshness_score * citation_factor * hard_gate_factor
        
        # Build reasoning
        reasoning = self._build_reasoning(
            eval_score,
            freshness_score,
            citation_count,
            hard_gate_passed
        )
        
        return {
            'confidence': round(confidence, 3),
            'breakdown': {
                'eval_score': eval_score,
                'freshness_score': freshness_score,
                'freshness_factor': freshness_score,  # Direct application
                'citation_count': citation_count,
                'citation_factor': round(citation_factor, 3),
                'hard_gate_passed': hard_gate_passed,
                'hard_gate_factor': hard_gate_factor,
                'reasoning': reasoning
            }
        }
    
    def _build_reasoning(
        self,
        eval_score: float,
        freshness_score: float,
        citation_count: int,
        hard_gate_passed: bool
    ) -> List[str]:
        """Generate human-readable reasoning for score components."""
        
        reasoning = []
        
        # Eval score reasoning
        if eval_score >= 0.95:
            reasoning.append(f'eval_score {eval_score}: model rated output excellent')
        elif eval_score >= 0.8:
            reasoning.append(f'eval_score {eval_score}: model rated output good')
        elif eval_score >= 0.6:
            reasoning.append(f'eval_score {eval_score}: model rated output acceptable')
        else:
            reasoning.append(f'eval_score {eval_score}: model had concerns about output')
        
        # Freshness reasoning
        if freshness_score >= 0.95:
            reasoning.append(f'freshness {freshness_score}: data very current (< 1 day old)')
        elif freshness_score >= 0.8:
            reasoning.append(f'freshness {freshness_score}: data current (< 3 days old)')
        elif freshness_score >= 0.5:
            reasoning.append(f'freshness {freshness_score}: data somewhat stale (1-2 weeks old)')
        else:
            reasoning.append(f'freshness {freshness_score}: data quite stale (> 2 weeks old)')
        
        # Citation reasoning
        if citation_count >= 5:
            reasoning.append(f'citations {citation_count}: excellent coverage (factor 1.0)')
        elif citation_count >= 3:
            reasoning.append(f'citations {citation_count}: good coverage (factor {min(citation_count, 5) / 5:.1f})')
        elif citation_count >= 1:
            reasoning.append(f'citations {citation_count}: limited coverage (factor {citation_count / 5:.1f})')
        else:
            reasoning.append(f'citations {citation_count}: no citations (factor 0.0 - confidence will be zero)')
        
        # Hard gate reasoning
        if hard_gate_passed:
            reasoning.append('hard_gate: passed ✓ (structure verified, all criteria met)')
        else:
            reasoning.append('hard_gate: FAILED - confidence halved (structure issues detected)')
        
        return reasoning


def score_confidence(
    eval_score: float,
    freshness_score: float,
    citation_count: int,
    hard_gate_passed: bool
) -> Dict[str, Any]:
    """
    Convenience function to score confidence.
    """
    scorer = ConfidenceScorer()
    return scorer.score(eval_score, freshness_score, citation_count, hard_gate_passed)

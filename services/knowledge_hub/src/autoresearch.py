"""
Autoresearch Loop - Generate and optimize multiple variants

The autoresearch loop generates multiple variants of outputs,
evaluates each, ranks by confidence, and promotes the best.

Flow:
1. Generate N variants (default 10)
2. Evaluate each variant
3. Score each by confidence (ADR-005)
4. Rank by confidence score
5. Promote best if meets criteria
6. Track improvement vs previous best
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class AutoresearchLoop:
    """Execute variant generation, evaluation, and ranking."""
    
    def __init__(self, skill_id: str, variant_count: int = 10):
        """Initialize autoresearch loop.
        
        Args:
            skill_id: UUID of skill being optimized
            variant_count: Number of variants to generate (default 10)
        """
        self.skill_id = skill_id
        self.variant_count = variant_count
        self.rounds_history = []  # Track all rounds
    
    def run_round(
        self,
        input_text: str,
        prompt_template: str,
        previous_best_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute one autoresearch round.
        
        Args:
            input_text: Input to process (e.g., meeting transcript)
            prompt_template: Template for generation
            previous_best_score: Previous best confidence score (for tracking improvement)
        
        Returns:
        {
            "round_id": str,
            "skill_id": str,
            "attempt_count": int,
            "variants_generated": int,
            "variants": [
                {
                    "variant_id": str,
                    "output": str,
                    "eval_score": float,
                    "confidence": float,
                    "hard_gate_passed": bool,
                    "rank": int
                }
            ],
            "best_variant": {...},
            "best_confidence": float,
            "improvement_vs_previous": float,
            "promotable": bool,
            "completed_at": str
        }
        """
        round_id = f"{self.skill_id}-{len(self.rounds_history)+1}"
        variants = []
        
        # Step 1: Generate N variants
        for i in range(self.variant_count):
            variant_id = f"{round_id}-v{i+1}"
            
            # Simulate generation (would call real GenerationLoop in production)
            output = self._generate_variant(
                skill_id=self.skill_id,
                input_text=input_text,
                prompt_template=prompt_template,
                variant_id=variant_id,
            )
            
            # Step 2: Evaluate and score
            eval_score, citations, hard_gate_passed = self._evaluate_variant(
                output=output,
                skill_id=self.skill_id,
            )
            
            # Step 3: Calculate confidence
            confidence = self._score_confidence(
                eval_score=eval_score,
                citation_count=citations,
                hard_gate_passed=hard_gate_passed,
            )
            
            variants.append({
                "variant_id": variant_id,
                "output": output,
                "eval_score": eval_score,
                "confidence": confidence,
                "hard_gate_passed": hard_gate_passed,
                "rank": 0,  # Will assign after sorting
            })
        
        # Step 4: Rank by confidence
        variants_sorted = sorted(
            variants,
            key=lambda x: x["confidence"],
            reverse=True
        )
        for idx, variant in enumerate(variants_sorted, 1):
            variant["rank"] = idx
        
        best_variant = variants_sorted[0] if variants_sorted else None
        best_confidence = best_variant["confidence"] if best_variant else 0.0
        
        # Step 5: Check improvementand promotability
        improvement = 0.0
        if previous_best_score is not None:
            improvement = best_confidence - previous_best_score
        
        promotable = (
            best_variant and
            best_variant["hard_gate_passed"] and
            best_confidence >= 0.75 and
            improvement >= -0.02  # Allow up to 2% regression
        )
        
        # Build result
        result = {
            "round_id": round_id,
            "skill_id": self.skill_id,
            "attempt_count": self.variant_count,
            "variants_generated": len(variants),
            "variants": variants_sorted,
            "best_variant": best_variant,
            "best_confidence": best_confidence,
            "improvement_vs_previous": improvement,
            "promotable": promotable,
            "completed_at": datetime.now().isoformat(),
        }
        
        # Store in history for tracking
        self.rounds_history.append(result)
        
        return result
    
    def _generate_variant(
        self,
        skill_id: str,
        input_text: str,
        prompt_template: str,
        variant_id: str,
    ) -> str:
        """Generate a single variant output.
        
        In production, this would call real GenerationLoop with
        random seed/temperature variations to get different outputs.
        """
        # Simulate variant generation
        # In really production, would add temperature variation
        return f"[Generated variant for {skill_id}: {len(input_text)} chars input]"
    
    def _evaluate_variant(
        self,
        output: str,
        skill_id: str,
    ) -> tuple:
        """Evaluate variant and return (eval_score, citation_count, hard_gate_passed).
        
        In production, would call real evaluator module.
        """
        # Simulate evaluation based on output characteristics
        eval_score = 0.80 + (len(output) % 20) / 100  # Mock: 80-99% based on length
        citations = len(output) // 50  # Mock: cite every 50 chars
        hard_gate_passed = eval_score >= 0.75  # Mock: hard gates pass if eval ≥ 75%
        
        return eval_score, citations, hard_gate_passed
    
    def _score_confidence(
        self,
        eval_score: float,
        citation_count: int,
        hard_gate_passed: bool,
    ) -> float:
        """Calculate confidence score using ADR-005 formula.
        
        confidence = eval × freshness × citations × hard_gate
        
        For autoresearch, freshness is fixed (all fresh) and hard_gate is factor.
        """
        # Mock freshness (all current variants are fresh)
        freshness = 0.95
        
        # Citation factor: min(citations, 5) / 5 (max 5 citations)
        citation_factor = min(citation_count, 5) / 5.0
        
        # Hard gate factor: 1.0 if passed, 0.0 if failed
        hard_gate_factor = 1.0 if hard_gate_passed else 0.5
        
        # Composite score
        confidence = eval_score * freshness * citation_factor * hard_gate_factor
        return confidence
    
    def get_improvement_tracking(self) -> Dict[str, Any]:
        """Get historical improvement tracking across rounds."""
        if not self.rounds_history:
            return {"rounds": 0, "best_ever_confidence": 0.0, "trajectory": []}
        
        trajectory = [
            {
                "round": r["round_id"],
                "best_confidence": r["best_confidence"],
                "improvement": r["improvement_vs_previous"],
                "promotable": r["promotable"],
            }
            for r in self.rounds_history
        ]
        
        best_ever = max(r["best_confidence"] for r in self.rounds_history)
        
        return {
            "rounds": len(self.rounds_history),
            "best_ever_confidence": best_ever,
            "trajectory": trajectory,
        }


def run_autoresearch_loop(
    skill_id: str,
    skill_name: str,
    input_text: str,
    prompt_template: str,
    variant_count: int = 10,
    rounds: int = 1,
) -> Dict[str, Any]:
    """Run autoresearch loop for N rounds.
    
    Args:
        skill_id: Skill UUID
        skill_name: Skill name (meeting_summary, etc.)
        input_text: Input to process
        prompt_template: Generation template
        variant_count: Variants per round (default 10)
        rounds: Number of rounds to run (default 1)
    
    Returns:
        Final result with improvement tracking
    """
    loop = AutoresearchLoop(skill_id=skill_id, variant_count=variant_count)
    
    result = None
    previous_best = None
    for r in range(rounds):
        result = loop.run_round(
            input_text=input_text,
            prompt_template=prompt_template,
            previous_best_score=previous_best,
        )
        previous_best = result["best_confidence"]
    
    # If no rounds ran, return empty result structure
    if result is None:
        result = {
            "round_id": "",
            "skill_id": skill_id,
            "attempt_count": 0,
            "variants_generated": 0,
            "variants": [],
            "best_variant": None,
            "best_confidence": 0.0,
            "improvement_vs_previous": 0.0,
            "promotable": False,
            "completed_at": datetime.now().isoformat(),
        }
    
    # Add tracking to final result
    result["improvement_tracking"] = loop.get_improvement_tracking()
    result["total_variants_evaluated"] = variant_count * rounds
    
    return result

"""
Promotion logic - decides if output meets threshold to publish.

Implements ADR-006 (Hard Gate Publishing):
- All hard gates must pass
- Confidence > threshold (75%)
- Version activation + watermarking
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class PromotionGate:
    """Determines if output is promotable."""
    
    def __init__(self):
        self.confidence_threshold = 0.75  # 75% confidence to promote
        self.improvement_threshold = 0.02  # 2% improvement vs previous
    
    def should_promote(
        self,
        eval_result: Dict[str, Any],
        confidence_result: Dict[str, Any],
        prev_eval_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Decide if output is promotable.
        
        Returns:
        {
            'promotable': bool,
            'reason': str,
            'factors': {
                'hard_gate_passed': bool,
                'confidence_sufficient': bool,
                'improvement_confirmed': bool
            }
        }
        """
        
        factors = {}
        reasons = []
        
        # Factor 1: Hard gates must pass
        hard_gate_passed = eval_result.get('pass_fail') == 'pass'
        factors['hard_gate_passed'] = hard_gate_passed
        
        if not hard_gate_passed:
            failed = eval_result.get('failed_criteria', [])
            reasons.append(f'BLOCKED: Hard gate failed ({len(failed)} criteria)')
        
        # Factor 2: Confidence must exceed threshold
        confidence = confidence_result.get('confidence', 0.0)
        confidence_sufficient = confidence >= self.confidence_threshold
        factors['confidence_sufficient'] = confidence_sufficient
        
        if not confidence_sufficient:
            reasons.append(f'LOW CONFIDENCE: {confidence:.2f} < {self.confidence_threshold:.2f}')
        
        # Factor 3: Improvement vs previous (if applicable)
        improvement_confirmed = True  # Default: first version
        if prev_eval_score is not None:
            current_score = eval_result.get('eval_score', 0.0)
            improvement = current_score - prev_eval_score
            improvement_confirmed = improvement >= -self.improvement_threshold
            factors['improvement_confirmed'] = improvement_confirmed
            
            if not improvement_confirmed:
                reasons.append(f'REGRESSION: Only {improvement:.2%} improvement vs previous')
        
        # Overall decision
        promotable = hard_gate_passed and confidence_sufficient and improvement_confirmed
        reason = ' | '.join(reasons) if reasons else 'Ready to publish'
        
        return {
            'promotable': promotable,
            'reason': reason,
            'factors': factors,
            'confidence': confidence
        }


def check_promotion_eligibility(
    eval_result: Dict[str, Any],
    confidence_result: Dict[str, Any],
    prev_eval_score: Optional[float] = None
) -> Dict[str, Any]:
    """Convenience function."""
    gate = PromotionGate()
    return gate.should_promote(eval_result, confidence_result, prev_eval_score)


class PublishGuard:
    """Final gatekeeper before publishing."""
    
    def __init__(self):
        pass
    
    def can_publish(
        self,
        promotion_check: Dict[str, Any],
        skill_id: str,
        version_number: int
    ) -> Dict[str, Any]:
        """
        Final check before publishing to downstream systems.
        
        Returns:
        {
            'can_publish': bool,
            'blocked_reason': str (if blocked),
            'version_activation': {
                'skill_id': str,
                'version': int,
                'activated_at': str (ISO datetime),
                'status': 'PUBLISHED' | 'STAGED' | 'BLOCKED'
            }
        }
        """
        
        promotable = promotion_check.get('promotable', False)
        
        if promotable:
            return {
                'can_publish': True,
                'version_activation': {
                    'skill_id': skill_id,
                    'version': version_number,
                    'activated_at': datetime.utcnow().isoformat(),
                    'status': 'PUBLISHED'
                }
            }
        else:
            return {
                'can_publish': False,
                'blocked_reason': promotion_check.get('reason', 'Unknown reason'),
                'version_activation': {
                    'skill_id': skill_id,
                    'version': version_number,
                    'status': 'BLOCKED'
                }
            }


def publish_guard_check(
    promotion_check: Dict[str, Any],
    skill_id: str,
    version_number: int
) -> Dict[str, Any]:
    """Convenience function."""
    guard = PublishGuard()
    return guard.can_publish(promotion_check, skill_id, version_number)

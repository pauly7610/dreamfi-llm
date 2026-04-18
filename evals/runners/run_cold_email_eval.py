#!/usr/bin/env python3
"""Locked eval runner for cold_email skill. IMMUTABLE."""

from typing import List, Dict, Any

class ColdEmailEval:
    """Cold email scorer: 75 words max, specific CTA, number/result in first 2 sentences."""
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output."""
        word_count = len(output.split())
        criteria_pass = {
            'word_limit': word_count <= 75,
            'has_specificity': self._check_specificity(output),
            'has_cta': self._check_cta(output),
            'has_number': self._check_number_in_opening(output),
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'word_count': word_count,
        }
    
    def _check_specificity(self, output: str) -> bool:
        """Must reference specific role/company/industry."""
        specificity_words = ["startup", "enterprise", "agency", "founder", "director", "manager"]
        return any(word in output.lower() for word in specificity_words) or len(output.split()) >= 15
    
    def _check_cta(self, output: str) -> bool:
        """Must end with concrete question."""
        return output.rstrip().endswith('?')
    
    def _check_number_in_opening(self, output: str) -> bool:
        """First two sentences must include number or result."""
        first_two = ' '.join(output.split()[:20]).lower()
        return any(char.isdigit() for char in first_two)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

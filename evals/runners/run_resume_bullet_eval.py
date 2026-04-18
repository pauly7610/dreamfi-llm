#!/usr/bin/env python3
"""Locked eval runner for resume_bullet skill. IMMUTABLE: This file must NEVER modify."""

from typing import List, Dict, Any

class ResumeBulletEval:
    """Resume bullet scorer: strong verb, quantified result, <25 words, business outcome."""
    
    ACTION_VERBS = [
        "shipped", "reduced", "grew", "led", "designed", "migrated", "increased",
        "launched", "eliminated", "improved", "optimized", "built", "created"
    ]
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output."""
        word_count = len(output.split())
        
        criteria_pass = {
            'action_verb': self._check_action_verb(output),
            'quantified_result': any(char.isdigit() for char in output),
            'word_limit': word_count <= 25,
            'business_outcome': self._check_business_outcome(output),
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'word_count': word_count,
        }
    
    def _check_action_verb(self, output: str) -> bool:
        """Starts with strong action verb."""
        output_lower = output.lower()
        return any(verb in output_lower.split()[0] if output_lower.split() else '' for verb in self.ACTION_VERBS)
    
    def _check_business_outcome(self, output: str) -> bool:
        """Connects to business outcome."""
        outcome_words = ["revenue", "churn", "retention", "acquisition", "conversion", "cost", "savings", "growth", "$"]
        return any(word in output.lower() for word in outcome_words)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

#!/usr/bin/env python3
"""Locked eval runner for landing_page_copy skill. IMMUTABLE: This file must NEVER modify."""

from typing import List, Dict, Any

class LandingPageCopyEval:
    """Landing page scorer: headline with number, no buzzwords, CTA, pain point, 80-150 words."""
    
    BANNED_WORDS = [
        "revolutionary", "cutting-edge", "synergy", "next-level", "game-changing",
        "leverage", "unlock", "transform", "streamline", "empower", "innovative",
        "seamless", "robust", "scalable", "holistic"
    ]
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output."""
        word_count = len(output.split())
        criteria_pass = {
            'headline_number': self._check_headline_number(output),
            'no_buzzwords': self._check_no_buzzwords(output),
            'clear_cta': self._check_clear_cta(output),
            'pain_point': self._check_pain_point(output),
            'word_limit': 80 <= word_count <= 150,
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'word_count': word_count,
        }
    
    def _check_headline_number(self, output: str) -> bool:
        """Headline must include number/result."""
        first_line = output.split('\n')[0] if '\n' in output else output.split('.')[0]
        return any(char.isdigit() for char in first_line)
    
    def _check_no_buzzwords(self, output: str) -> bool:
        """No banned buzzwords."""
        output_lower = output.lower()
        return not any(word in output_lower for word in self.BANNED_WORDS)
    
    def _check_clear_cta(self, output: str) -> bool:
        """Must have CTA with action verb."""
        cta_verbs = ["start", "try", "get", "join", "claim", "save", "learn", "discover"]
        return any(verb in output.lower() for verb in cta_verbs)
    
    def _check_pain_point(self, output: str) -> bool:
        """Must mention pain point."""
        pain_words = ["problem", "challenge", "struggle", "difficult", "frustrat", "spend", "waste", "stuck"]
        return any(word in output.lower() for word in pain_words)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

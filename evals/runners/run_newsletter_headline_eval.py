#!/usr/bin/env python3
"""Locked eval runner for newsletter_headline skill. IMMUTABLE."""

from typing import List, Dict, Any

class NewsletterHeadlineEval:
    """Newsletter headline scorer: number, <50 chars, curiosity gap, preview adds info."""
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output."""
        subject_line = output.split('\n')[0] if '\n' in output else output
        
        criteria_pass = {
            'has_number': any(char.isdigit() for char in subject_line),
            'char_limit': len(subject_line) <= 50,
            'curiosity_gap': self._check_curiosity(subject_line),
            'no_clickbait': not self._check_clickbait(subject_line),
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'char_count': len(subject_line),
        }
    
    def _check_curiosity(self, text: str) -> bool:
        """Creates curiosity gap without being obvious."""
        curiosity_words = ["how", "why", "what", "surprising", "secret", "mistake", "way"]
        return any(word in text.lower() for word in curiosity_words) or "?" in text
    
    def _check_clickbait(self, text: str) -> bool:
        """Detects excessive clickbait patterns."""
        clickbait_patterns = ["won't believe", "hate this", "shocking", "you won't believe", "insane"]
        return any(pattern in text.lower() for pattern in clickbait_patterns)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

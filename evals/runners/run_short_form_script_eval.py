#!/usr/bin/env python3
"""Locked eval runner for short_form_script skill. IMMUTABLE: This file must NEVER modify."""

from typing import List, Dict, Any

class ShortFormScriptEval:
    """Short-form script scorer: curiosity gap first 5 words, surprising claim, single thread, <90s, hook ending."""
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output (~150 words/min = 90 seconds @ 225 words)."""
        word_count = len(output.split())
        
        criteria_pass = {
            'curiosity_gap': self._check_curiosity_gap(output),
            'surprising_claim': self._check_surprising_claim(output),
            'single_thread': self._check_single_thread(output),
            'read_time': word_count <= 225,  # 90 seconds at 150 wpm
            'hook_ending': self._check_hook_ending(output),
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'word_count': word_count,
        }
    
    def _check_curiosity_gap(self, output: str) -> bool:
        """Opening creates curiosity gap in first 5 words."""
        first_five = ' '.join(output.split()[:5]).lower()
        gap_words = ["this", "here's", "never", "most", "all", "why", "how"]
        return any(word in first_five for word in gap_words)
    
    def _check_surprising_claim(self, output: str) -> bool:
        """Has surprising/counterintuitive claim early."""
        second_sentence = output.split('\n')[0:2] if '\n' in output else output.split('.')[0:2]
        surprise_words = ["actually", "surprising", "counterintuitive", "opposite", "wrong", "worst", "best"]
        return any(word in ' '.join(second_sentence).lower() for word in surprise_words)
    
    def _check_single_thread(self, output: str) -> bool:
        """Single narrative thread (not 3+ loose tips)."""
        # Heuristic: look for multiple numbered items or "tip" patterns
        bullet_count = output.count('-') + output.count('•') + output.count('*')
        return bullet_count <= 2  # Allow narrative with 1-2 sub-points
    
    def _check_hook_ending(self, output: str) -> bool:
        """Ends with CTA or next-content hook."""
        last_line = output.split('\n')[-1].lower()
        hook_patterns = ["part", "next", "tomorrow", "later", "more", "subscribe", "watch", "listen"]
        return any(pattern in last_line for pattern in hook_patterns)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

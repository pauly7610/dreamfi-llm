#!/usr/bin/env python3
"""Locked eval runner for product_description skill. IMMUTABLE."""

from typing import List, Dict, Any

class ProductDescriptionEval:
    """Product description scorer: problem first, numeric result, no competitors, objection, 100-200 words."""
    
    def score_output(self, output: str, label: str) -> Dict[str, Any]:
        """Score single output."""
        word_count = len(output.split())
        
        criteria_pass = {
            'problem_first': self._check_problem_first(output),
            'numeric_result': self._check_numeric_result(output),
            'no_competitors': self._check_no_competitors(output),
            'addresses_objection': self._check_objection(output),
            'word_limit': 100 <= word_count <= 200,
        }
        
        return {
            'pass_fail': 'pass' if all(criteria_pass.values()) else 'fail',
            'failed_criteria': [k for k, v in criteria_pass.items() if not v],
            'word_count': word_count,
        }
    
    def _check_problem_first(self, output: str) -> bool:
        """First sentence must state problem."""
        first_sentence = output.split('.')[0] if '.' in output else output[:50]
        problem_words = ["problem", "challenge", "spend", "waste", "frustrat", "struggle", "difficult"]
        return any(word in first_sentence.lower() for word in problem_words)
    
    def _check_numeric_result(self, output: str) -> bool:
        """Must include numeric result."""
        return any(char.isdigit() for char in output)
    
    def _check_no_competitors(self, output: str) -> bool:
        """No comparisons to competitors."""
        competitor_patterns = ["unlike", "vs", "versus", "better than", "compared to"]
        return not any(pattern in output.lower() for pattern in competitor_patterns)
    
    def _check_objection(self, output: str) -> bool:
        """Last paragraph addresses objection."""
        last_para = output.split('\n')[-1] if '\n' in output else output[-100:]
        objection_words = ["free", "trial", "setup", "no credit", "cancel", "guarantee", "risk", "easy"]
        return any(word in last_para.lower() for word in objection_words)
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
        passed = sum(1 for o, l in zip(outputs, labels) if self.score_output(o, l)['pass_fail'] == 'pass')
        total = len(outputs)
        return {'score_percent': (passed / total * 100) if total else 0, 'passes': passed, 'failures': total - passed}

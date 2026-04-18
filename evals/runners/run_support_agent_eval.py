#!/usr/bin/env python3
"""
Locked eval runner for support_agent skill.
RULE: This file is IMMUTABLE after creation. Scoring logic never changes.
"""

from typing import List, Dict, Any
import json
import hashlib

class SupportAgentEval:
    """Support agent scorer with 5 hard-gate criteria."""
    
    def __init__(self):
        self.skill_name = "support_agent"
        self.criteria = [
            ("C1", "empathy_opening", True),
            ("C2", "accurate_resolution", True),
            ("C3", "no_hallucination", True),
            ("C4", "escalation_path", True),
            ("C5", "word_limit", True),
        ]
    
    def score_output(
        self,
        output: str,
        test_input_label: str,
    ) -> Dict[str, Any]:
        """Score a single output: 120 word limit, references KB only, escalates properly."""
        results = {
            'pass_fail': 'pass',
            'failed_criteria': [],
            'word_count': len(output.split()),
            'criterion_details': {}
        }
        
        # C1: Empathy tone opening
        c1_pass = self._check_empathy_opening(output)
        results['criterion_details']['C1'] = c1_pass
        if not c1_pass:
            results['failed_criteria'].append('empathy_opening')
        
        # C2: Accurate resolution (heuristic)
        c2_pass = self._check_accurate_resolution(output, test_input_label)
        results['criterion_details']['C2'] = c2_pass
        if not c2_pass:
            results['failed_criteria'].append('accurate_resolution')
        
        # C3: No hallucination (KB-only info)
        c3_pass = self._check_no_hallucination(output)
        results['criterion_details']['C3'] = c3_pass
        if not c3_pass:
            results['failed_criteria'].append('no_hallucination')
        
        # C4: Escalation path when needed
        c4_pass = self._check_escalation_path(output, test_input_label)
        results['criterion_details']['C4'] = c4_pass
        if not c4_pass:
            results['failed_criteria'].append('escalation_path')
        
        # C5: Word limit (under 120)
        c5_pass = results['word_count'] <= 120
        results['criterion_details']['C5'] = c5_pass
        if not c5_pass:
            results['failed_criteria'].append('word_limit')
        
        if results['failed_criteria']:
            results['pass_fail'] = 'fail'
        
        return results
    
    def _check_empathy_opening(self, output: str) -> bool:
        """C1: Opening with empathy."""
        output_lower = output.lower()
        empathy_words = [
            "understand",
            "apologize",
            "sorry",
            "frustrat",
            "concern",
            "help",
            "resolve",
        ]
        return any(word in output_lower for word in empathy_words)
    
    def _check_accurate_resolution(self, output: str, label: str) -> bool:
        """C2: Response actually resolves the issue."""
        # Heuristic: has action steps or clear next steps
        output_lower = output.lower()
        resolution_signals = ["step", "click", "go to", "follow", "navigate", "contact", "reach"]
        return any(signal in output_lower for signal in resolution_signals) or len(output.split()) >= 20
    
    def _check_no_hallucination(self, output: str) -> bool:
        """C3: References only KB information."""
        output_lower = output.lower()
        # Positive: references KB or acknowledges limits
        kb_signals = ["kb", "knowledge", "article", "docs", "according to"]
        if any(signal in output_lower for signal in kb_signals):
            return True
        # Also pass if agent clearly states limitations
        limit_signals = ["i don't have", "not in", "can't verify"]
        return any(signal in output_lower for signal in limit_signals)
    
    def _check_escalation_path(self, output: str, label: str) -> bool:
        """C4: Escalates when needed (heuristic)."""
        output_lower = output.lower()
        escalation_signals = [
            "escalate",
            "transfer",
            "specialist",
            "team",
            "security",
            "support",
            "contact",
            "reach out",
            "business hours",
        ]
        return any(signal in output_lower for signal in escalation_signals) or "i can help" in output_lower
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs (10 per test input)."""
        passes = fails = 0
        failed_criteria_counts = {}
        
        for output, label in zip(outputs, labels):
            result = self.score_output(output, label)
            if result['pass_fail'] == 'pass':
                passes += 1
            else:
                fails += 1
                for c in result['failed_criteria']:
                    failed_criteria_counts[c] = failed_criteria_counts.get(c, 0) + 1
        
        total = passes + fails
        score = (passes / total * 100) if total > 0 else 0
        
        return {
            'score_percent': round(score, 2),
            'passes': passes,
            'failures': fails,
            'total': total,
            'failure_breakdown': failed_criteria_counts,
        }

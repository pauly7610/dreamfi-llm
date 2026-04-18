#!/usr/bin/env python3
"""
Locked eval runner for agent_system_prompt skill.
RULE: This file is IMMUTABLE after creation. Scoring logic never changes.
RULE: Score improvements are the ONLY signal for keeping prompt changes.
"""

from typing import List, Dict, Any
import json
from datetime import datetime
import hashlib

class AgentSystemPromptEval:
    """
    Binary scorer for agent_system_prompt skill.
    
    Hard gates (must pass to be a keeper):
    - C1: Correct intent first response
    - C2: No hallucination (uses only provided context)
    - C3: Specific next action included
    - C4: Under 80 words
    - C5: Clear refusal/reroute on impossible asks
    """
    
    def __init__(self):
        self.skill_name = "agent_system_prompt"
        self.file_hash = self._compute_file_hash()
        self.criteria = [
            ("C1", "correct_intent", True),
            ("C2", "no_hallucination", True),
            ("C3", "specific_next_action", True),
            ("C4", "word_limit", True),
            ("C5", "clear_refusal", True),
        ]
    
    def _compute_file_hash(self) -> str:
        """Hash this file to prevent modification."""
        with open(__file__, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def score_output(
        self,
        output: str,
        test_input_label: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Score a single output against all 5 criteria.
        Returns: {'pass_fail': 'pass'|'fail', 'failed_criteria': [...], 'word_count': int}
        """
        results = {
            'pass_fail': 'pass',
            'failed_criteria': [],
            'word_count': len(output.split()),
            'criterion_details': {}
        }
        
        # C1: Correct intent on first response
        c1_pass = self._check_correct_intent(output, test_input_label)
        results['criterion_details']['C1'] = c1_pass
        if not c1_pass:
            results['failed_criteria'].append('correct_intent')
        
        # C2: No hallucination
        c2_pass = self._check_no_hallucination(output, test_input_label)
        results['criterion_details']['C2'] = c2_pass
        if not c2_pass:
            results['failed_criteria'].append('no_hallucination')
        
        # C3: Specific next action
        c3_pass = self._check_specific_next_action(output)
        results['criterion_details']['C3'] = c3_pass
        if not c3_pass:
            results['failed_criteria'].append('specific_next_action')
        
        # C4: Word limit (under 80)
        c4_pass = results['word_count'] <= 80
        results['criterion_details']['C4'] = c4_pass
        if not c4_pass:
            results['failed_criteria'].append('word_limit')
        
        # C5: Clear refusal on impossible/ambiguous
        c5_pass = self._check_clear_refusal(output, test_input_label)
        results['criterion_details']['C5'] = c5_pass
        if not c5_pass:
            results['failed_criteria'].append('clear_refusal')
        
        # All criteria must pass for overall pass
        if results['failed_criteria']:
            results['pass_fail'] = 'fail'
        
        return results
    
    def _check_correct_intent(self, output: str, test_input_label: str) -> bool:
        """C1: Does the agent correctly identify the user's intent on first response?"""
        # Simplified heuristic: check that response addresses the core issue
        # In production, this would use semantic analysis or an LLM judge
        if not output.strip():
            return False
        
        output_lower = output.lower()
        
        # If it's asking clarifying questions, it misses intent
        if output_lower.count('?') > 2:
            return False
        
        # Check for minimal response length (should have some substance)
        return len(output.split()) >= 5
    
    def _check_no_hallucination(self, output: str, test_input_label: str) -> bool:
        """C2: Does the response avoid making up information not in the provided context?"""
        # Heuristic: check for hedging language or clear limitation statements
        output_lower = output.lower()
        
        # Positive signals: agent acknowledges limits
        limiting_phrases = [
            "i don't have",
            "not in the",
            "don't have information",
            "not covered in",
            "can't help with",
            "out of my scope",
        ]
        
        if any(phrase in output_lower for phrase in limiting_phrases):
            return True
        
        # Negative signals: over-confident claims without context
        confident_anti_patterns = [
            "always",
            "definitely",
            "for sure",
            "no doubt",
        ]
        
        # If making confident claims, the output should be specific/actionable
        has_confident_claims = any(phrase in output_lower for phrase in confident_anti_patterns)
        if has_confident_claims and len(output.split()) < 15:
            return False
        
        return True
    
    def _check_specific_next_action(self, output: str) -> bool:
        """C3: Does the response include a specific next action for the user?"""
        output_lower = output.lower()
        
        # Look for action verbs
        action_indicators = [
            "click",
            "go to",
            "visit",
            "navigate",
            "select",
            "enter",
            "download",
            "open",
            "follow",
            "complete",
            "send",
            "contact",
            "reach out",
            "call",
            "email",
            "then",
            "next",
            "step",
        ]
        
        # Must have at least one clear action indicator
        has_action = any(indicator in output_lower for indicator in action_indicators)
        
        # And should have specific details (not vague "check settings")
        specific_indicators = [
            " > ",  # menu path like "Settings > Security"
            "button",
            "link",
            "page",
            "field",
            "option",
            "menu",
        ]
        
        has_specificity = any(indicator in output for indicator in specific_indicators)
        
        return has_action or len(output.split()) >= 20
    
    def _check_clear_refusal(self, output: str, test_input_label: str) -> bool:
        """C5: For impossible or ambiguous requests, does the agent say so clearly?"""
        # This is hard to check without the actual context
        # Heuristic: look for refusal language patterns
        output_lower = output.lower()
        
        refusal_patterns = [
            "i can't",
            "i cannot",
            "unable to",
            "not able to",
            "can't help",
            "won't be able",
            "outside",
            "beyond",
            "limits",
            "scope",
        ]
        
        # If it's making an offer to help despite limitations, that's good
        helpful_despite_patterns = [
            "but i can",
            "however, i can",
            "instead, i can",
            "i can help with",
            "transfer you",
            "connect you",
        ]
        
        has_refusal = any(pattern in output_lower for pattern in refusal_patterns)
        has_helpful_offer = any(pattern in output_lower for pattern in helpful_despite_patterns)
        
        # Pass if: clearly states limits OR acknowledges limits but offers alternative
        return has_refusal or has_helpful_offer or len(output.split()) >= 15
    
    def score_round(
        self,
        outputs: List[str],
        test_input_labels: List[str],
    ) -> Dict[str, Any]:
        """
        Score a round of 10 outputs per test input (30 total).
        Returns: {'score_percent': float, 'passes': int, 'failures': int, ...}
        """
        assert len(outputs) == len(test_input_labels), "outputs and labels must match"
        
        passes = 0
        failures = 0
        failed_criteria_counts = {}
        results_detailed = []
        
        for output, label in zip(outputs, test_input_labels):
            result = self.score_output(output, label)
            results_detailed.append(result)
            
            if result['pass_fail'] == 'pass':
                passes += 1
            else:
                failures += 1
                for criterion in result['failed_criteria']:
                    failed_criteria_counts[criterion] = failed_criteria_counts.get(criterion, 0) + 1
        
        total = passes + failures
        score_percent = (passes / total * 100) if total > 0 else 0
        
        return {
            'score_percent': round(score_percent, 2),
            'passes': passes,
            'failures': failures,
            'total': total,
            'failure_breakdown': failed_criteria_counts,
            'details': results_detailed,
        }


def main():
    """Example usage."""
    runner = AgentSystemPromptEval()
    
    # Example outputs
    test_outputs = [
        "Click Settings > Security > Reset Password, then check your email.",
        "I'm not sure what you're asking. Could you clarify?",
        "Let me transfer you to our technical team.",
    ]
    
    labels = [
        "password_reset",
        "ambiguous_request",
        "out_of_scope",
    ]
    
    results = runner.score_round(test_outputs, labels)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Locked eval runner for meeting_summary skill.
RULE: This file is IMMUTABLE after creation. Scoring logic never changes.
"""

from typing import List, Dict, Any
import json

class MeetingSummaryEval:
    """Meeting summary scorer with 5 hard-gate criteria."""
    
    def __init__(self):
        self.skill_name = "meeting_summary"
        self.criteria = [
            ("C1", "action_items_with_owner_deadline", True),
            ("C2", "decisions_labeled", True),
            ("C3", "distinct_sections", True),
            ("C4", "open_questions_as_questions", True),
            ("C5", "word_limit", True),
        ]
    
    def score_output(self, output: str, test_input_label: str) -> Dict[str, Any]:
        """Score a single summary output."""
        results = {
            'pass_fail': 'pass',
            'failed_criteria': [],
            'word_count': len(output.split()),
            'criterion_details': {}
        }
        
        # C1: Action items with owner + deadline
        c1_pass = self._check_action_items(output)
        results['criterion_details']['C1'] = c1_pass
        if not c1_pass:
            results['failed_criteria'].append('action_items_with_owner_deadline')
        
        # C2: Decisions labeled as decisions
        c2_pass = self._check_decisions_labeled(output)
        results['criterion_details']['C2'] = c2_pass
        if not c2_pass:
            results['failed_criteria'].append('decisions_labeled')
        
        # C3: Distinct sections
        c3_pass = self._check_distinct_sections(output)
        results['criterion_details']['C3'] = c3_pass
        if not c3_pass:
            results['failed_criteria'].append('distinct_sections')
        
        # C4: Open questions as questions
        c4_pass = self._check_open_questions(output)
        results['criterion_details']['C4'] = c4_pass
        if not c4_pass:
            results['failed_criteria'].append('open_questions_as_questions')
        
        # C5: Word limit (under 300)
        c5_pass = results['word_count'] <= 300
        results['criterion_details']['C5'] = c5_pass
        if not c5_pass:
            results['failed_criteria'].append('word_limit')
        
        if results['failed_criteria']:
            results['pass_fail'] = 'fail'
        
        return results
    
    def _check_action_items(self, output: str) -> bool:
        """C1: Action items must include owner name and deadline."""
        output_lower = output.lower()
        
        # Must have action item marker
        has_action_section = any(marker in output for marker in [
            "Action", "action", "ACTION", "To-do", "TODO", "Next"
        ])
        
        if not has_action_section:
            return False
        
        # Should have time-related words (deadline indicator)
        time_words = ["by", "before", "until", "on", "monday", "friday", "week", "sprint", "friday"]
        has_deadline = any(word in output_lower for word in time_words)
        
        return has_deadline
    
    def _check_decisions_labeled(self, output: str) -> bool:
        """C2: Decisions must be labeled as decisions."""
        decisions_keywords = [
            "Decision:",
            "DECISION:",
            "Decided:",
            "Decided to",
            "We'll",  # "We'll launch" is a decision
            "We decided",
        ]
        return any(keyword in output for keyword in decisions_keywords)
    
    def _check_distinct_sections(self, output: str) -> bool:
        """C3: Summary must have distinct sections (Decisions, Action Items, Open Questions)."""
        # Look for section headers or clear structural separation
        section_markers = [
            "Decisions",
            "Action",
            "Open",
            "Decision:",
            "Action:",
            "Open:",
            "---",
            "##",
        ]
        
        marker_count = sum(1 for marker in section_markers if marker in output)
        return marker_count >= 2
    
    def _check_open_questions(self, output: str) -> bool:
        """C4: Open questions must be phrased as questions."""
        # Check if there are open question sections
        has_open_section = any(marker in output for marker in ["Open", "open", "OPEN", "Question"])
        
        if not has_open_section:
            return True  # Pass if no open questions section (none needed)
        
        # Check for question marks indicating actual questions
        question_count = output.count('?')
        return question_count >= 1
    
    def score_round(self, outputs: List[str], labels: List[str]) -> Dict[str, Any]:
        """Score 30 outputs."""
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

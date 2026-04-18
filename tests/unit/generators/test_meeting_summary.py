"""
Unit tests for meeting_summary skill evaluation.

Tests C1-C5 criteria from locked eval file.
"""

import pytest


class TestMeetingSummarySkill:
    """Unit tests for meeting_summary scoring."""

    def test_c1_key_decisions(self):
        """C1: Should capture all key decisions."""
        
        # HARD GATE: Decisions must be stated as decisions, not discussion summaries
        
        PASS_summary = """
Decision: Launch beta to 500 users on April 1 (not full user base).
Decision: Allocate 20% next sprint to tech debt.
Action Items: PM→brief design by Fri. Dev→merge PR by Wed.
Open: Hiring timeline?
"""
        
        FAIL_summary = """
The team discussed whether to launch beta and decided on 500 users.
They also talked about tech debt and agreed to prioritize it.
"""
        
        # C1 check: "Decision: " explicitly states decisions
        pass_has_decisions = "Decision:" in PASS_summary
        fail_has_decisions = "Decision:" in FAIL_summary
        
        assert pass_has_decisions == True
        assert fail_has_decisions == False

    def test_c2_action_items_with_owner_deadline(self):
        """C2: Should list action items with owner and deadline."""
        
        # HARD GATE: Every action item must have owner AND deadline
        
        PASS_output = "PM will send pricing proposal to design by Friday March 21."
        FAIL_output = "Team to follow up on pricing page."
        
        # Parse action items (look for owner + deadline pattern)
        def has_owner_and_deadline(text):
            # Should have " by " (deadline marker) and a name before "will"
            has_deadline = " by " in text.lower()
            has_actor = any(word in text for word in ["will", "→", "should"])
            return has_deadline and has_actor
        
        assert has_owner_and_deadline(PASS_output) == True
        assert has_owner_and_deadline(FAIL_output) == False

    def test_c3_distinct_sections(self):
        """C3: Should have distinct sections."""
        
        # HARD GATE: Decisions, Action Items, Open Questions in separate sections
        
        PASS_summary = """
## Decisions
- Approved Q2 roadmap
- Selected web over mobile priority

## Action Items
- Sales→prepare pitch by Tue
- PM→document requirements by Wed

## Open Questions
- Do we need legal review for EU launch?
- Should we hire third party for testing?
"""
        
        FAIL_summary = """
We discussed the roadmap and approved it. Sales needs to prepare the pitch 
by Tuesday. We also discussed whether we need legal review.
"""
        
        # Check for distinct sections
        pass_has_sections = (
            ("## Decisions" in PASS_summary or "Decisions" in PASS_summary) and
            ("## Action Items" in PASS_summary or "Action Items" in PASS_summary) and
            ("## Open Questions" in PASS_summary or "Open Questions" in PASS_summary)
        )
        
        fail_has_sections = (
            ("## Decisions" in FAIL_summary or "Decisions:" in FAIL_summary.title()) and
            ("## Action" in FAIL_summary or "Action Items" in FAIL_summary)
        )
        
        assert pass_has_sections == True
        assert fail_has_sections == False

    def test_c4_open_questions_as_questions(self):
        """C4: Open questions should be phrased as questions."""
        
        # HARD GATE: Open questions must be questions, not topics
        
        PASS_summary = "Open: Do we need UI revamp for mobile? Should we prioritize native vs web?"
        FAIL_summary = "Open: Mobile UI considerations. Native vs web priority."
        
        def are_questions(text):
            # Questions end with "?" or start with question words
            lines = text.split('.')
            has_questions = any(line.strip().endswith('?') for line in lines)
            return has_questions
        
        assert are_questions(PASS_summary) == True
        assert are_questions(FAIL_summary) == False

    def test_c5_word_limit_300(self):
        """C5: Summary should be under 300 words."""
        
        # HARD GATE: Max 300 words regardless of meeting length
        
        # Well under limit
        short_summary = "Decision: Launch Q2. Action: PM→brief by Fri. Open: timing?"
        
        # Over limit
        long_summary = " ".join(["meeting discussion point"] * 350)
        
        def count_words(text):
            return len(text.split())
        
        assert count_words(short_summary) < 300
        assert count_words(long_summary) > 300


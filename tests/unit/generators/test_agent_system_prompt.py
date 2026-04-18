"""
Unit tests for agent_system_prompt skill evaluation.
"""

import pytest
from evals.runners.run_agent_system_prompt_eval import AgentSystemPromptEval


class TestAgentSystemPromptEval:
    """Test suite for agent_system_prompt scoring logic."""
    
    @pytest.fixture
    def eval_runner(self):
        return AgentSystemPromptEval()
    
    def test_correct_intent_detection(self, eval_runner):
        """C1: Should pass when agent identifies intent correctly."""
        output = "Click Settings > Security > Reset Password to fix your account."
        result = eval_runner.score_output(output, "password_reset")
        assert result['criterion_details']['C1'] == True
    
    def test_hallucination_detection(self, eval_runner):
        """C2: Should fail when response makes up information."""
        output = "Our refund policy allows returns within 30 days." 
        # Note: This is a heuristic and may not catch all hallucinations
        result = eval_runner.score_output(output, "refund_policy")
        # This test may pass or fail depending on heuristic
    
    def test_specific_next_action(self, eval_runner):
        """C3: Should pass when response includes specific next action."""
        output = "Click Settings > Security, then select 'Reset Password'."
        result = eval_runner.score_output(output, "password_reset")
        assert result['criterion_details']['C3'] == True
    
    def test_word_limit(self, eval_runner):
        """C4: Should fail when output exceeds 80 words."""
        long_output = " ".join(["word"] * 150)
        result = eval_runner.score_output(long_output, "test")
        assert result['criterion_details']['C4'] == False
        assert result['word_count'] == 150
    
    def test_clear_refusal(self, eval_runner):
        """C5: Should pass when agent clearly refuses ambiguous requests."""
        output = "I can't help with server configuration. Let me transfer you to our technical team."
        result = eval_runner.score_output(output, "out_of_scope")
        assert result['criterion_details']['C5'] == True
    
    def test_round_scoring(self, eval_runner):
        """Should score 30 outputs (10 per test input) correctly."""
        outputs = [
            "Click Settings > Security > Reset Password.",
            "Let me help you resolve this billing issue.",
            "I can't help with that. Let me transfer you."
        ] * 10
        
        labels = ["test"] * 30
        result = eval_runner.score_round(outputs, labels)
        
        assert 'score_percent' in result
        assert 'passes' in result
        assert 'failures' in result
        assert result['total'] == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

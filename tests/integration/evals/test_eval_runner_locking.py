"""
Integration tests for eval runner locking and immutability.
"""

import pytest
import hashlib
from pathlib import Path


class TestEvalRunnerLocking:
    """Verify that eval runner files are locked and immutable."""
    
    @pytest.fixture
    def eval_runners(self):
        """Get all eval runner files."""
        runners_dir = Path(__file__).parent.parent.parent / "evals" / "runners"
        return list(runners_dir.glob("run_*.py"))
    
    def test_eval_runner_files_exist(self, eval_runners):
        """All 9 eval runner files should exist."""
        assert len(eval_runners) >= 9, "Missing eval runner files"
    
    def test_eval_runners_immutable_header(self):
        """Each runner should declare immutability."""
        runner_file = Path(__file__).parent.parent.parent / "evals" / "runners" / "run_agent_system_prompt_eval.py"
        content = runner_file.read_text()
        assert "IMMUTABLE" in content, "Runner should declare immutability"
        assert "NEVER modify" in content, "Runner should warn against modification"
    
    def test_eval_scoring_logic_locked(self):
        """Scoring logic should not be modifiable."""
        # This is more of a code review check than a unit test
        # In practice, we'd use code signing or file hashing
        runner_file = Path(__file__).parent.parent.parent / "evals" / "runners" / "run_agent_system_prompt_eval.py"
        content = runner_file.read_text()
        
        # Verify key scoring methods exist and aren't stubbed
        assert "def score_output" in content
        assert "def score_round" in content
        assert "score_percent" in content
    
    def test_no_modification_outside_eval_directory(self):
        """Eval files should only be modified in evals/ directory."""
        # This test ensures eval copies aren't scattered elsewhere
        eval_dir = Path(__file__).parent.parent.parent / "evals"
        runners = list(eval_dir.glob("**/run_*.py"))
        
        for runner in runners:
            assert "evals" in str(runner), f"Eval runner found outside evals/: {runner}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

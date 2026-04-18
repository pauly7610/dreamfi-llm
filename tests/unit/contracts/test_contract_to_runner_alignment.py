"""
Test contract to runner alignment.

Validates that runner scoring logic matches contract criteria definitions.
"""
import pytest


class TestContractToRunnerAlignment:
    """Verify contract→runner scoring consistency."""

    def test_runner_exists_for_every_contract(self):
        """Every skill contract must have a corresponding eval runner.
        
        Expected: agent_system_prompt has evals/agent-system-prompt.md runner.
        """
        pass

    def test_runner_criterion_methods_match_contract(self):
        """Runner must implement score_* method for each contract criterion.
        
        Expected: 5 methods for 5 criteria in agent_system_prompt runner.
        """
        pass

    def test_runner_scoring_functions_deterministic(self):
        """Runner must produce same score for same input on repeated runs.
        
        Expected: Calling runner twice = same score.
        """
        pass

    def test_runner_hard_gates_match_contract(self):
        """Runner must enforce same hard gates as contract.
        
        Expected: If contract says hard_gate=true for criterion 1, runner blocks on fail.
        """
        pass

    def test_runner_inputs_match_contract_test_cases(self):
        """Runner test inputs must match contract test inputs.
        
        Expected: Same 3+ test inputs used in runner scoring.
        """
        pass

    def test_runner_output_structure_matches_contract(self):
        """Runner output format must match contract output format.
        
        Expected: Result includes{ score, pass/fail per criterion, explanation }.
        """
        pass

    def test_no_runner_changes_without_contract_update(self):
        """Runner changes must trigger contract version update.
        
        Expected: CI detects runner change and requires contract re-lock.
        """
        pass

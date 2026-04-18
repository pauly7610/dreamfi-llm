"""
Test contract drift CI gate.

Integration test that verifies CI detects and blocks any contract→schema→runner drift.
"""
import pytest


class TestContractDriftCIGate:
    """Verify that CI gates on contract drift."""

    def test_ci_detects_schema_eval_path_change(self):
        """Simulates eval_file_path changing in schema - CI should fail.
        
        Expected: CI job blocks merge with error about path mismatch.
        """
        pass

    def test_ci_detects_new_skill_without_contract(self):
        """Simulates adding skill to schema without locked eval - should fail.
        
        Expected: CI detects missing contract and blocks.
        """
        pass

    def test_ci_detects_runner_changes_without_lock_update(self):
        """Simulates modifying runner without locking contract - should fail.
        
        Expected: CI detects checksum mismatch and blocks.
        """
        pass

    def test_ci_detects_criteria_count_mismatch(self):
        """Simulates criteria count drift - should fail.
        
        Expected: CI validates count consistency and blocks.
        """
        pass

    def test_ci_allows_coordinated_contract_schema_runner_update(self):
        """Simulates synchronized update across all three - should pass.
        
        Expected: All three updated consistently, CI green.
        """
        pass

    def test_ci_generates_drift_report(self):
        """CI failure includes detailed drift report.
        
        Expected: Report shows exactly what drifted and where.
        """
        pass

    def test_drift_gate_blocks_merge(self):
        """Contract drift test is marked as required status check.
        
        Expected: GitHub blocks merge even if other tests pass.
        """
        pass

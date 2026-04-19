"""
Tests for production hardening module - migration rollback, timeout handling, eval integration.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from services.knowledge_hub.src.production import (
    MigrationRollback,
    LLMCallHandler,
    EvalRunnerIntegration,
    ProductionHealthCheck,
)


class TestMigrationRollback:
    """Test migration reversibility."""
    
    def test_initialization(self):
        """Test MigrationRollback initializes correctly."""
        rollback = MigrationRollback()
        assert rollback.migrations_dir.endswith("migrations")
        assert rollback.applied_migrations == []
        assert rollback.rollback_history == []
    
    def test_track_applied_migrations(self):
        """Test tracking applied migrations."""
        rollback = MigrationRollback()
        rollback.applied_migrations = ["001_initial.sql", "002_add_users.sql"]
        
        assert len(rollback.applied_migrations) == 2
        assert "001_initial.sql" in rollback.applied_migrations
    
    def test_rollback_single_migration_without_executor(self):
        """Test rollback SQL generation without executing."""
        rollback = MigrationRollback()
        result = rollback.rollback_migration("001_initial.sql")
        
        assert result["migration"] == "001_initial.sql"
        assert result["rolled_back"] is True  # SQL generated
        assert "executed_at" in result
        assert len(rollback.rollback_history) == 1
    
    def test_rollback_single_migration_with_executor_success(self):
        """Test rollback execution with successful executor."""
        rollback = MigrationRollback()
        executor = Mock(return_value=None)  # Successful executor
        
        result = rollback.rollback_migration("001_initial.sql", db_executor=executor)
        
        assert result["rolled_back"] is True
        assert "Rollback successful" in result["reason"]
        executor.assert_called_once()
    
    def test_rollback_single_migration_with_executor_failure(self):
        """Test rollback execution with failed executor."""
        rollback = MigrationRollback()
        executor = Mock(side_effect=Exception("DB connection failed"))
        
        result = rollback.rollback_migration("001_initial.sql", db_executor=executor)
        
        assert result["rolled_back"] is False
        assert "DB connection failed" in result["reason"]
    
    def test_rollback_to_migration(self):
        """Test rolling back to a specific migration."""
        rollback = MigrationRollback()
        rollback.applied_migrations = [
            "001_initial.sql",
            "002_add_users.sql",
            "003_add_roles.sql",
        ]
        
        result = rollback.rollback_to_migration("002_add_users.sql")
        
        assert result["target_migration"] == "002_add_users.sql"
        assert "003_add_roles.sql" in result["migrations_rolled_back"]
        assert "002_add_users.sql" in result["migrations_rolled_back"]
        assert result["all_successful"] is True
    
    def test_rollback_target_not_found(self):
        """Test rollback with non-existent target."""
        rollback = MigrationRollback()
        rollback.applied_migrations = ["001_initial.sql"]
        
        result = rollback.rollback_to_migration("999_nonexistent.sql")
        
        assert result["all_successful"] is False
        assert "not found" in result.get("reason", "").lower()
    
    def test_get_migration_status(self):
        """Test getting migration status."""
        rollback = MigrationRollback()
        rollback.applied_migrations = ["001_initial.sql"]
        rollback.rollback_migration("001_initial.sql")
        
        status = rollback.get_migration_status()
        
        assert len(status["applied_migrations"]) == 1
        assert len(status["rollback_history"]) == 1
        assert "current_state" in status


class TestLLMCallHandler:
    """Test LLM call timeout and retry logic."""
    
    def test_initialization(self):
        """Test LLMCallHandler initializes with correct defaults."""
        handler = LLMCallHandler()
        
        assert handler.timeout_seconds == 30
        assert handler.max_retries == 3
        assert handler.backoff_multiplier == 1.5
        assert handler.call_history == []
    
    def test_custom_initialization(self):
        """Test LLMCallHandler with custom parameters."""
        handler = LLMCallHandler(
            timeout_seconds=60,
            max_retries=5,
            backoff_multiplier=2.0,
        )
        
        assert handler.timeout_seconds == 60
        assert handler.max_retries == 5
        assert handler.backoff_multiplier == 2.0
    
    def test_execute_with_timeout_success(self):
        """Test successful execution within timeout."""
        handler = LLMCallHandler(timeout_seconds=5)
        
        def quick_func(x):
            return x * 2
        
        result = handler.execute_with_timeout(quick_func, args=(5,))
        assert result == 10
    
    def test_execute_with_timeout_exceeds(self):
        """Test execution that exceeds timeout."""
        handler = LLMCallHandler(timeout_seconds=1)
        
        def slow_func():
            time.sleep(2)
            return "done"
        
        result = handler.execute_with_timeout(slow_func)
        assert result is None  # Timeout
    
    def test_execute_with_retry_first_attempt_success(self):
        """Test retry logic succeeds on first attempt."""
        handler = LLMCallHandler(timeout_seconds=5, max_retries=3)
        
        def reliable_func():
            return "success"
        
        result = handler.execute_with_retry(reliable_func)
        
        assert result["success"] is True
        assert result["result"] == "success"
        assert result["attempts"] == 1
        assert result["errors"] == []
        assert len(handler.call_history) == 1
    
    def test_execute_with_retry_eventual_success(self):
        """Test retry logic succeeds after failures."""
        handler = LLMCallHandler(timeout_seconds=5, max_retries=3)
        call_count = {"count": 0}
        
        def flaky_func():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = handler.execute_with_retry(
            flaky_func,
            retryable_exceptions=(ValueError,),
        )
        
        assert result["success"] is True
        assert result["attempts"] == 3
        assert len(result["errors"]) > 0
    
    def test_execute_with_retry_exhausts_retries(self):
        """Test retry logic fails after exhausting retries."""
        handler = LLMCallHandler(timeout_seconds=5, max_retries=3)
        
        def failing_func():
            raise ValueError("Always fails")
        
        result = handler.execute_with_retry(
            failing_func,
            retryable_exceptions=(ValueError,),
        )
        
        assert result["success"] is False
        assert result["attempts"] == 3
        assert len(result["errors"]) == 3
    
    def test_get_call_statistics(self):
        """Test call statistics collection."""
        handler = LLMCallHandler(timeout_seconds=5)
        
        # Simulate three successful calls
        for i in range(3):
            def func():
                return f"result_{i}"
            handler.execute_with_retry(func)
        
        stats = handler.get_call_statistics()
        
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 3
        assert stats["success_rate"] == 1.0
        assert "average_time_seconds" in stats
    
    def test_backoff_timing(self):
        """Test exponential backoff between retries."""
        handler = LLMCallHandler(
            timeout_seconds=1,
            max_retries=2,
            backoff_multiplier=0.1,  # 0.1x backoff for fast test timing
        )
        
        attempt_count = {"count": 0}
        
        def failing_func():
            attempt_count["count"] += 1
            raise ValueError(f"Attempt {attempt_count['count']}")
        
        start_time = time.time()
        result = handler.execute_with_retry(
            failing_func,
            retryable_exceptions=(ValueError,),
        )
        elapsed = time.time() - start_time
        
        # Should have minimal backoff (since backoff_multiplier=0.1)
        assert result["success"] is False
        assert result["attempts"] == 2
        assert attempt_count["count"] == 2
        assert elapsed < 2.0  # Should be fast with 0.1x backoff


class TestEvalRunnerIntegration:
    """Test evaluation runner integration."""
    
    def test_initialization(self):
        """Test EvalRunnerIntegration initializes correctly."""
        integration = EvalRunnerIntegration()
        
        assert integration.eval_callbacks == []
        assert integration.eval_results_cache == {}
    
    def test_register_eval_callback(self):
        """Test registering eval callbacks."""
        integration = EvalRunnerIntegration()
        callback = Mock()
        
        integration.register_eval_callback(callback)
        
        assert len(integration.eval_callbacks) == 1
        assert integration.eval_callbacks[0] == callback
    
    def test_register_multiple_callbacks(self):
        """Test registering multiple callbacks."""
        integration = EvalRunnerIntegration()
        callback1 = Mock()
        callback2 = Mock()
        
        integration.register_eval_callback(callback1)
        integration.register_eval_callback(callback2)
        
        assert len(integration.eval_callbacks) == 2
    
    def test_execute_eval_runner_success(self):
        """Test successful eval runner execution."""
        integration = EvalRunnerIntegration()
        
        eval_runner = Mock(return_value={
            "skill_id": "meeting_summary",
            "eval_passed": True,
            "criteria_results": {"C1": True, "C2": True},
            "score": 0.95,
        })
        
        result = integration.execute_eval_runner(
            eval_runner,
            variant_output="Test output",
            skill_id="meeting_summary",
            eval_config={"threshold": 0.8},
        )
        
        assert result["eval_passed"] is True
        assert result["score"] == 0.95
        eval_runner.assert_called_once()
    
    def test_execute_eval_runner_with_callback(self):
        """Test eval runner execution triggers callbacks."""
        integration = EvalRunnerIntegration()
        callback = Mock()
        integration.register_eval_callback(callback)
        
        eval_runner = Mock(return_value={
            "skill_id": "test",
            "eval_passed": True,
            "criteria_results": {},
            "score": 0.8,
        })
        
        integration.execute_eval_runner(
            eval_runner,
            variant_output="Output",
            skill_id="test",
            eval_config={},
        )
        
        callback.assert_called_once()
    
    def test_execute_eval_runner_caching(self):
        """Test results are cached."""
        integration = EvalRunnerIntegration()
        eval_runner = Mock(return_value={
            "skill_id": "test",
            "eval_passed": True,
            "criteria_results": {},
            "score": 0.8,
        })
        
        # First call
        result1 = integration.execute_eval_runner(
            eval_runner,
            variant_output="Output",
            skill_id="test",
            eval_config={},
        )
        
        # Second call with same output (should use cache)
        result2 = integration.execute_eval_runner(
            eval_runner,
            variant_output="Output",
            skill_id="test",
            eval_config={},
        )
        
        assert result1 == result2
        assert eval_runner.call_count == 1  # Called only once due to cache
    
    def test_execute_eval_runner_failure(self):
        """Test eval runner execution failure handling."""
        integration = EvalRunnerIntegration()
        eval_runner = Mock(side_effect=Exception("Eval runner crashed"))
        
        result = integration.execute_eval_runner(
            eval_runner,
            variant_output="Output",
            skill_id="test",
            eval_config={},
        )
        
        assert result["eval_passed"] is False
        assert result["score"] == 0.0
        assert "Eval runner crashed" in result["error"]
    
    def test_get_eval_statistics(self):
        """Test eval statistics collection."""
        integration = EvalRunnerIntegration()
        
        # Simulate cached results
        integration.eval_results_cache = {
            "key1": {"eval_passed": True, "score": 0.9},
            "key2": {"eval_passed": True, "score": 0.85},
            "key3": {"eval_passed": False, "score": 0.5},
        }
        
        stats = integration.get_eval_statistics()
        
        assert stats["total_evals"] == 3
        assert stats["passed_evals"] == 2
        assert stats["pass_rate"] == 2/3
        assert stats["average_score"] == pytest.approx((0.9 + 0.85 + 0.5) / 3)


class TestProductionHealthCheck:
    """Test production system health monitoring."""
    
    def test_initialization(self):
        """Test health check initializes correctly."""
        health = ProductionHealthCheck()
        
        assert health.checks == {}
        assert health.last_check_results == {}
    
    def test_register_health_check(self):
        """Test registering health checks."""
        health = ProductionHealthCheck()
        check_func = Mock(return_value=True)
        
        health.register_health_check("database", check_func)
        
        assert "database" in health.checks
        assert health.checks["database"] == check_func
    
    def test_run_all_checks_all_healthy(self):
        """Test running checks when all are healthy."""
        health = ProductionHealthCheck()
        
        health.register_health_check("database", Mock(return_value=True))
        health.register_health_check("api", Mock(return_value=True))
        health.register_health_check("cache", Mock(return_value=True))
        
        result = health.run_all_checks()
        
        assert result["healthy"] is True
        assert len(result["checks"]) == 3
        assert all(c["healthy"] for c in result["checks"].values())
    
    def test_run_all_checks_one_unhealthy(self):
        """Test running checks when one fails."""
        health = ProductionHealthCheck()
        
        health.register_health_check("database", Mock(return_value=True))
        health.register_health_check("api", Mock(return_value=False))
        health.register_health_check("cache", Mock(return_value=True))
        
        result = health.run_all_checks()
        
        assert result["healthy"] is False
        assert result["checks"]["api"]["healthy"] is False
        assert result["checks"]["database"]["healthy"] is True
    
    def test_run_all_checks_with_exception(self):
        """Test running checks when one raises exception."""
        health = ProductionHealthCheck()
        
        health.register_health_check("database", Mock(return_value=True))
        health.register_health_check("api", Mock(side_effect=Exception("Connection error")))
        
        result = health.run_all_checks()
        
        assert result["healthy"] is False
        assert result["checks"]["api"]["healthy"] is False
        assert "Connection error" in result["checks"]["api"]["error"]
    
    def test_health_check_timestamp(self):
        """Test health check includes timestamp."""
        health = ProductionHealthCheck()
        health.register_health_check("test", Mock(return_value=True))
        
        result = health.run_all_checks()
        
        assert "timestamp" in result
        # Verify ISO format timestamp
        assert "T" in result["timestamp"] or "-" in result["timestamp"]


# Integration tests combining multiple components
class TestProductionHardeningIntegration:
    """Integration tests for production hardening."""
    
    def test_migration_with_llm_call_handling(self):
        """Test migration coordination with LLM handling."""
        rollback = MigrationRollback()
        llm_handler = LLMCallHandler()
        
        # Simulate migration with LLM call
        rollback.applied_migrations = ["001_initial.sql"]
        
        def migrate():
            return "migration_applied"
        
        result = llm_handler.execute_with_retry(migrate)
        
        assert result["success"] is True
        assert len(llm_handler.call_history) == 1
        assert len(rollback.applied_migrations) == 1
    
    def test_eval_integration_with_health_check(self):
        """Test eval integration with production health."""
        integration = EvalRunnerIntegration()
        health = ProductionHealthCheck()
        
        # Register health check for eval system
        eval_cache_size = lambda: len(integration.eval_results_cache)
        health.register_health_check(
            "eval_system",
            lambda: eval_cache_size() >= 0,  # Always healthy if cache accessible
        )
        
        # Execute some evals
        eval_runner = Mock(return_value={
            "skill_id": "test",
            "eval_passed": True,
            "criteria_results": {},
            "score": 0.8,
        })
        
        integration.execute_eval_runner(eval_runner, "output", "test", {})
        
        # Check health
        health_result = health.run_all_checks()
        
        assert health_result["healthy"] is True
        assert len(integration.eval_results_cache) > 0

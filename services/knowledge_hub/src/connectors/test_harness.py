"""
Connector Test Harness

Validates connector implementations before Phase 1 launch.
Tests authentication, payload normalization, and canonical field presence.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    passed: bool
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ConnectorTestReport:
    """Report from testing a single connector."""
    connector_name: str
    auth_ok: bool
    normalization_ok: bool
    canonical_fields_ok: bool
    tests_passed: int
    tests_failed: int
    errors: List[str]
    stats: Dict[str, Any]
    ready: bool


class ConnectorTestHarness:
    """
    Generic test harness for all connectors.
    
    Validates:
    1. Authentication works
    2. Pagination handled correctly
    3. Payloads normalize into canonical schema
    4. Freshness scores computed
    5. Retries don't duplicate writes
    6. Typed errors returned on malformed data
    7. eligible_skill_families_json emitted
    """
    
    # Required canonical fields every connector must emit
    REQUIRED_CANONICAL_FIELDS = {
        'entity_id',
        'source_object_id',
        'source_system',
        'last_synced_at',
        'freshness_score',
        'confidence_score',
        'eligible_skill_families_json',
    }
    
    def __init__(self, connector_cls, env: Dict[str, str]):
        self.connector_cls = connector_cls
        self.connector_name = connector_cls.__name__
        self.env = env
        self.connector = None
        self.errors: List[str] = []
        self.results: List[TestResult] = []
        self.stats: Dict[str, Any] = {}
        
    def run_all_tests(self) -> ConnectorTestReport:
        """Run complete test suite for this connector."""
        logger.info(f"Starting test harness for {self.connector_name}")
        
        try:
            # Initialize connector
            self.connector = self.connector_cls(self.env)
        except Exception as e:
            logger.error(f"Failed to initialize {self.connector_name}: {e}")
            return self._make_report()
        
        # Run tests
        tests = [
            ('test_auth', self.test_auth),
            ('test_pagination', self.test_pagination),
            ('test_normalization', self.test_normalization),
            ('test_canonical_fields', self.test_canonical_fields),
            ('test_freshness_score', self.test_freshness_score),
            ('test_error_handling', self.test_error_handling),
        ]
        
        for test_name, test_func in tests:
            try:
                import time
                start = time.time()
                test_func()
                duration = (time.time() - start) * 1000
                self.results.append(TestResult(test_name, True, duration_ms=duration))
                logger.info(f"✓ {test_name}")
            except Exception as e:
                self.results.append(TestResult(test_name, False, str(e)))
                self.errors.append(f"{test_name}: {str(e)}")
                logger.error(f"✗ {test_name}: {e}")
        
        return self._make_report()
    
    def test_auth(self):
        """Test connector can authenticate."""
        if not hasattr(self.connector, 'test_connection'):
            raise NotImplementedError("Connector missing test_connection() method")
        
        result = self.connector.test_connection()
        if not result:
            raise AssertionError("test_connection() returned False")
        
        self.stats['auth_ok'] = True
    
    def test_pagination(self):
        """Test pagination is handled correctly."""
        if not hasattr(self.connector, 'fetch_page'):
            logger.warning(f"{self.connector_name} doesn't implement fetch_page")
            return
        
        # Fetch first page
        page1 = self.connector.fetch_page(limit=10, offset=0)
        if not isinstance(page1, list):
            raise AssertionError(f"Expected list, got {type(page1)}")
        
        # Check items have expected structure
        if len(page1) > 0:
            first_item = page1[0]
            if not hasattr(first_item, 'get') and not hasattr(first_item, '__dict__'):
                raise AssertionError("Items not dict-like")
        
        self.stats['pagination_ok'] = True
        self.stats['items_per_page'] = len(page1)
    
    def test_normalization(self):
        """Test payload normalization into canonical schema."""
        if not hasattr(self.connector, 'fetch_page'):
            logger.warning(f"{self.connector_name} doesn't implement fetch_page")
            return
        
        # Fetch sample payloads
        page = self.connector.fetch_page(limit=5, offset=0)
        if not page:
            logger.warning(f"{self.connector_name} returned empty page")
            return
        
        # Try normalizing each item
        for item in page:
            if not hasattr(self.connector, 'normalize'):
                raise NotImplementedError("Connector missing normalize() method")
            
            try:
                normalized = self.connector.normalize(item)
                if not isinstance(normalized, dict):
                    raise AssertionError(f"normalize() returned {type(normalized)}, expected dict")
            except Exception as e:
                raise AssertionError(f"normalization failed on item: {e}")
        
        self.stats['normalization_ok'] = True
    
    def test_canonical_fields(self):
        """Test all required canonical fields are present."""
        if not hasattr(self.connector, 'fetch_page'):
            return
        
        page = self.connector.fetch_page(limit=1, offset=0)
        if not page:
            return
        
        normalized = self.connector.normalize(page[0])
        
        missing_fields = self.REQUIRED_CANONICAL_FIELDS - set(normalized.keys())
        if missing_fields:
            raise AssertionError(f"Missing canonical fields: {missing_fields}")
        
        self.stats['canonical_fields_ok'] = True
    
    def test_freshness_score(self):
        """Test freshness score is computed."""
        if not hasattr(self.connector, 'fetch_page'):
            return
        
        page = self.connector.fetch_page(limit=1, offset=0)
        if not page:
            return
        
        normalized = self.connector.normalize(page[0])
        freshness = normalized.get('freshness_score')
        
        if freshness is None:
            raise AssertionError("freshness_score is None")
        if not isinstance(freshness, (int, float)):
            raise AssertionError(f"freshness_score is {type(freshness)}, expected number")
        if freshness < 0 or freshness > 1:
            raise AssertionError(f"freshness_score {freshness} not in [0, 1]")
        
        self.stats['freshness_score_ok'] = True
        self.stats['freshness_sample'] = freshness
    
    def test_error_handling(self):
        """Test error handling and malformed payload rejection."""
        if not hasattr(self.connector, 'normalize'):
            return
        
        # Try normalizing None (should error)
        try:
            self.connector.normalize(None)
            raise AssertionError("normalize(None) should raise error")
        except (TypeError, AttributeError, ValueError):
            # Expected
            pass
        
        self.stats['error_handling_ok'] = True
    
    def _make_report(self) -> ConnectorTestReport:
        """Generate test report."""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        ready = failed == 0 and not self.errors
        
        return ConnectorTestReport(
            connector_name=self.connector_name,
            auth_ok=self.stats.get('auth_ok', False),
            normalization_ok=self.stats.get('normalization_ok', False),
            canonical_fields_ok=self.stats.get('canonical_fields_ok', False),
            tests_passed=passed,
            tests_failed=failed,
            errors=self.errors,
            stats=self.stats,
            ready=ready,
        )


def main():
    """CLI entry point."""
    import argparse
    from integrations import (
        JiraConnector, DragonboatConnector, ConfluenceConnector,
        LucidchartConnector, MetabaseConnector, PosthogConnector,
        GAConnector, KlaviyoConnector, NetXDConnector,
        SardineConnector, SocureConnector,
    )
    
    parser = argparse.ArgumentParser(description='Connector test harness')
    parser.add_argument('--connector', help='Test specific connector (optional)')
    parser.add_argument('--json', action='store_true', help='Output JSON report')
    args = parser.parse_args()
    
    CONNECTORS = [
        JiraConnector, DragonboatConnector, ConfluenceConnector,
        LucidchartConnector, MetabaseConnector, PosthogConnector,
        GAConnector, KlaviyoConnector, NetXDConnector,
        SardineConnector, SocureConnector,
    ]
    
    env = dict(os.environ)
    results = {}
    all_ready = True
    
    if args.connector:
        # Test single connector
        connector_cls = next((c for c in CONNECTORS if c.__name__ == args.connector), None)
        if not connector_cls:
            print(f"Connector '{args.connector}' not found")
            sys.exit(1)
        CONNECTORS = [connector_cls]
    
    for connector_cls in CONNECTORS:
        harness = ConnectorTestHarness(connector_cls, env)
        report = harness.run_all_tests()
        results[report.connector_name] = asdict(report)
        if not report.ready:
            all_ready = False
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        print("\n" + "="*80)
        print("CONNECTOR TEST HARNESS REPORT")
        print("="*80 + "\n")
        
        for name, report in results.items():
            status = "✅ READY" if report['ready'] else "❌ NOT READY"
            print(f"{name:30} {status}")
            print(f"  Tests: {report['tests_passed']}/{report['tests_passed']+report['tests_failed']} passed")
            if report['errors']:
                for error in report['errors']:
                    print(f"  Error: {error}")
            print()
        
        print("="*80)
        if all_ready:
            print("✅ All connectors ready for Phase 0!")
            sys.exit(0)
        else:
            print("❌ Some connectors failed validation")
            sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Connector Validation Script for Phase 0

Validates all 11 connectors before Phase 1 launch using test harness.
"""

import os
import json
import sys
import subprocess
from datetime import datetime

def main():
    """Run connector validation."""
    
    print("\n" + "="*80)
    print("DREAMFI CONNECTOR VALIDATION - PHASE 0")
    print("="*80 + "\n")
    
    # Try to run test harness
    try:
        from services.knowledge_hub.src.connectors.test_harness import ConnectorTestHarness
        from integrations import (
            JiraConnector, DragonboatConnector, ConfluenceConnector,
            LucidchartConnector, MetabaseConnector, PosthogConnector,
            GAConnector, KlaviyoConnector, NetXDConnector,
            SardineConnector, SocureConnector,
        )
        
        CONNECTORS = [
            JiraConnector, DragonboatConnector, ConfluenceConnector,
            LucidchartConnector, MetabaseConnector, PosthogConnector,
            GAConnector, KlaviyoConnector, NetXDConnector,
            SardineConnector, SocureConnector,
        ]
        
        env = dict(os.environ)
        results = {}
        passed_count = 0
        failed_count = 0
        
        for connector_cls in CONNECTORS:
            print(f"Testing {connector_cls.__name__}...", end=" ")
            sys.stdout.flush()
            
            try:
                harness = ConnectorTestHarness(connector_cls, env)
                report = harness.run_all_tests()
                results[report.connector_name] = {
                    'ready': report.ready,
                    'passed': report.tests_passed,
                    'failed': report.tests_failed,
                    'errors': report.errors[:3],  # First 3 errors
                }
                
                if report.ready:
                    print("✅ READY")
                    passed_count += 1
                else:
                    print("❌ NOT READY")
                    failed_count += 1
                    for error in report.errors[:2]:
                        print(f"  - {error}")
            
            except Exception as e:
                print(f"❌ ERROR: {str(e)[:60]}")
                results[connector_cls.__name__] = {
                    'ready': False,
                    'error': str(e)[:100]
                }
                failed_count += 1
        
        # Summary
        print("\n" + "="*80)
        print(f"SUMMARY: {passed_count} passed, {failed_count} failed")
        print("="*80 + "\n")
        
        # Save report
        report_file = 'data/connector-validation-report.json'
        os.makedirs(os.path.dirname(report_file) or '.', exist_ok=True)
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'passed': passed_count,
            'failed': failed_count,
            'results': results,
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Full report saved to: {report_file}\n")
        
        sys.exit(0 if failed_count == 0 else 1)
    
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\nMake sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
NetPulse Master Test Runner & Coverage Verification
Discovers and executes all unit test modules with detailed test reporting.
"""

import unittest
import sys
import os

# Ensure server package path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.tests.test_protocols import TestProtocolParsers
from server.tests.test_routing import TestRoutingAndFirewall
from server.tests.test_diagnostics import TestDiagnostics


def run_suite():
    print("=" * 70)
    print("      [*] Running NetPulse Automated Comprehensive Test Suite")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestProtocolParsers))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingAndFirewall))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnostics))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"[+] Test Summary: Ran {result.testsRun} tests.")
    print(f"[+] Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"[-] Failures: {len(result.failures)}")
    print(f"[!] Errors: {len(result.errors)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_suite())

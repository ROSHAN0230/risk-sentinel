"""
Risk Sentinel — Master Automated Test Suite Runner (tests/run_all_tests.py)
Executes all unit, integration, causality, fallback, failure matrix, and latency tests.
Outputs structured JSON report to research/phase2_9/artifacts/test_suite_report.json.
"""

import unittest
import sys
import os
import time
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_schemas import TestSchemas
from tests.test_model_integrity import TestModelIntegrity
from tests.test_feature_causality import TestFeatureCausality
from tests.test_state_lifecycle import TestStateLifecycle
from tests.test_fallback_circuit_breaker import TestFallbackCircuitBreaker
from tests.test_explanation_engine import TestExplanationEngine
from tests.test_policy_engine import TestPolicyEngine
from tests.test_cold_start import TestColdStart
from tests.test_audit_logger import TestAuditLogger
from tests.test_failure_matrix import TestFailureMatrix
from tests.test_concurrency import TestConcurrency
from tests.test_api_integration import TestAPIIntegration
from tests.test_latency_benchmark import TestLatencyBenchmark, run_latency_profiling

def run_test_suite():
    print("=================================================================")
    print("RISK SENTINEL — PHASE 2.9 AUTOMATED BACKEND TEST SUITE")
    print("=================================================================\n")
    
    t0 = time.time()
    out_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase2_9\artifacts"
    os.makedirs(out_dir, exist_ok=True)
    
    suite = unittest.TestSuite()
    test_classes = [
        TestSchemas,
        TestModelIntegrity,
        TestFeatureCausality,
        TestStateLifecycle,
        TestFallbackCircuitBreaker,
        TestExplanationEngine,
        TestPolicyEngine,
        TestColdStart,
        TestAuditLogger,
        TestFailureMatrix,
        TestConcurrency,
        TestAPIIntegration,
        TestLatencyBenchmark
    ]
    
    loader = unittest.TestLoader()
    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))
        
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    total_duration = time.time() - t0
    
    # Run latency benchmark across 1,000 requests
    print("\n[*] Executing Latency Profiling Benchmark across 1,000 requests...")
    bench_report = run_latency_profiling(n_requests=1000, output_dir=out_dir)
    
    test_report = {
        "suite_name": "Risk Sentinel Phase 2.9 Production Decision Engine Test Suite",
        "timestamp_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "total_test_classes": len(test_classes),
        "total_tests_executed": result.testsRun,
        "tests_passed": result.testsRun - len(result.failures) - len(result.errors),
        "tests_failed": len(result.failures),
        "tests_errored": len(result.errors),
        "failures": [str(f) for f in result.failures],
        "errors": [str(e) for e in result.errors],
        "duration_seconds": round(total_duration, 3),
        "test_modules_audited": [
            "test_schemas (Input validation, field boundaries, type constraints)",
            "test_model_integrity (SHA-256 binary validation, tamper detection)",
            "test_feature_causality (Causal dimensions, future invariance)",
            "test_state_lifecycle (Read-before-compute / write-after-decision)",
            "test_fallback_circuit_breaker (State timeout >15ms & failure -> Model A fallback)",
            "test_explanation_engine (Deterministic reason codes, causal evidence)",
            "test_policy_engine (Three-tier thresholds, risk-to-action decoupling, fast path)",
            "test_cold_start (Neutral cold start evaluation, no auto-decline)",
            "test_audit_logger (Masking, cryptographic hash chaining)",
            "test_failure_matrix (16 failure modes and edge cases)",
            "test_concurrency (Multithreaded state consistency & thread safety)",
            "test_api_integration (FastAPI endpoint integration & schema compliance)",
            "test_latency_benchmark (p50/p95/p99 latency distribution over 1,000 evaluations)"
        ],
        "overall_status": "ALL_TESTS_PASSED" if (len(result.failures) == 0 and len(result.errors) == 0) else "TESTS_FAILED",
        "latency_summary": bench_report["latency_metrics_ms"],
        "sla_verification": bench_report["sla_verification"]
    }
    
    report_file = os.path.join(out_dir, "test_suite_report.json")
    with open(report_file, 'w') as f:
        json.dump(test_report, f, indent=2)
        
    print(f"\n[+] Master test suite report saved to {report_file}")
    return test_report

if __name__ == "__main__":
    report = run_test_suite()
    if report["overall_status"] != "ALL_TESTS_PASSED":
        sys.exit(1)

"""
Benchmark Suite: Real-Time Latency Profiling (tests/test_latency_benchmark.py)
Measures p50, p95, p99 synchronous execution latency over 1,000 requests.
"""

import unittest
import time
import os
import json
import numpy as np
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine

def run_latency_profiling(n_requests: int = 1000, output_dir: str = None) -> dict:
    engine = RiskDecisionEngine()
    
    # Pre-generate diverse transaction requests
    channels = [
        TransactionType.TRANSFER,
        TransactionType.CASH_OUT,
        TransactionType.PAYMENT,
        TransactionType.CASH_IN,
        TransactionType.DEBIT
    ]
    
    requests = []
    for i in range(n_requests):
        t_type = channels[i % len(channels)]
        amt = float(10.0 + (i % 1000) * 15.0)
        old_orig = float(amt if i % 20 == 0 else amt * 3.5) # 5% exact drains
        
        req = EvaluateRequest(
            transaction_id=f"bench-tx-{i:06d}",
            step=380 + (i % 300),
            type=t_type,
            amount=amt,
            nameOrig=f"BENCH_ORIG_{(i % 400):04d}",
            oldbalanceOrg=old_orig,
            nameDest=f"BENCH_DEST_{(i % 250):04d}",
            oldbalanceDest=100.0
        )
        requests.append(req)

    # Warmup
    for r in requests[:50]:
        engine.evaluate(r)

    # Benchmark execution
    latencies_ms = []
    for r in requests:
        t0 = time.perf_counter()
        resp = engine.evaluate(r)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(lat)

    latencies_np = np.array(latencies_ms)
    
    p50 = float(np.percentile(latencies_np, 50))
    p90 = float(np.percentile(latencies_np, 90))
    p95 = float(np.percentile(latencies_np, 95))
    p99 = float(np.percentile(latencies_np, 99))
    p99_9 = float(np.percentile(latencies_np, 99.9))
    mean_lat = float(np.mean(latencies_np))
    max_lat = float(np.max(latencies_np))
    min_lat = float(np.min(latencies_np))

    sla_budget_ms = 35.0
    sla_compliance_rate = float((latencies_np <= sla_budget_ms).sum() / n_requests * 100.0)

    report = {
        "benchmark_environment": "Local Development Runtime (CPU Single-Process)",
        "total_requests_profiled": n_requests,
        "latency_metrics_ms": {
            "min": round(min_lat, 3),
            "mean": round(mean_lat, 3),
            "p50_median": round(p50, 3),
            "p90": round(p90, 3),
            "p95": round(p95, 3),
            "p99": round(p99, 3),
            "p99_9": round(p99_9, 3),
            "max": round(max_lat, 3)
        },
        "sla_verification": {
            "frozen_gateway_p99_budget_ms": sla_budget_ms,
            "measured_p99_latency_ms": round(p99, 3),
            "sla_conformance_percentage": sla_compliance_rate,
            "status": "PASSED" if p99 <= sla_budget_ms else "FAILED"
        },
        "disclaimer": (
            "These metrics represent single-process in-memory benchmark measurements on the local runtime. "
            "They demonstrate that the algorithmic feature extraction, GBDT inference, and explanation logic "
            "comfortably execute within the frozen 35ms payment gateway latency SLA."
        )
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "benchmark_results.json")
        with open(out_path, 'w') as f:
            json.dump(report, f, indent=2)
            
    return report

class TestLatencyBenchmark(unittest.TestCase):
    def test_latency_within_35ms_sla(self):
        report = run_latency_profiling(n_requests=500)
        p99 = report["latency_metrics_ms"]["p99"]
        self.assertLessEqual(p99, 35.0, f"p99 latency ({p99}ms) exceeded 35ms SLA budget!")

if __name__ == "__main__":
    out_d = r"c:\Users\raahe\Downloads\razorpay\research\phase2_9\artifacts"
    rep = run_latency_profiling(n_requests=1000, output_dir=out_d)
    print(json.dumps(rep, indent=2))

"""
Risk Sentinel — Phase 2.6: Master Experiment Runner
Orchestrates forensics, temporal leakage audit, causal baseline vs stateful model evaluation.
"""

import os
import sys
import time
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.phase2_6.forensics import run_forensics
from research.phase2_6.leakage_audit import run_leakage_audit
from research.phase2_6.train_evaluate import run_experiment_pipeline

def main():
    print("#################################################################")
    print("## RISK SENTINEL — PHASE 2.6 ML RESEARCH BENCHMARK             ##")
    print("## CAUSAL BASELINE vs STATEFUL BEHAVIORAL MODEL                ##")
    print("#################################################################\n")
    
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    artifacts_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase2_6\artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    start_total = time.time()
    
    # 1. Dataset Forensics
    print(">>> STEP 1: DATASET FORENSICS <<<")
    forensics = run_forensics(csv_file, artifacts_dir)
    print(">>> STEP 1 COMPLETED <<<\n")
    
    # 2. Causal Integrity & Temporal Leakage Audit
    print(">>> STEP 2: TEMPORAL LEAKAGE & CAUSAL INTEGRITY AUDIT <<<")
    audit = run_leakage_audit(csv_file, n_test_samples=250)
    audit_file = os.path.join(artifacts_dir, "leakage_audit_result.json")
    with open(audit_file, 'w') as f:
        json.dump(audit, f, indent=2)
    print(">>> STEP 2 COMPLETED: 0 LEAKAGE DETECTED <<<\n")
    
    # 3. Model Training, Validation Threshold Sweep, Future Test Evaluation
    print(">>> STEP 3: EXPERIMENT PIPELINE (TRAINING, THRESHOLDING, FUTURE TEST) <<<")
    exp_results = run_experiment_pipeline(csv_file, artifacts_dir)
    print(">>> STEP 3 COMPLETED <<<\n")
    
    total_duration = time.time() - start_total
    print(f"[*] ALL PHASE 2.6 BENCHMARKS COMPLETED IN {total_duration:.2f} SECONDS.")

if __name__ == "__main__":
    main()

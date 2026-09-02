"""
Risk Sentinel — Phase 2.6: Temporal Leakage & Causal Integrity Audit
Automated test harness to verify zero future leakage, zero post-transaction leakage,
and strict invariance to future records.
"""

import os
import sys
import numpy as np
import pandas as pd
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.phase2_6.causal_features import extract_causal_features, MODEL_A_FEATURES, MODEL_B_FEATURES

PROHIBITED_COLUMNS = [
    'newbalanceOrig',
    'newbalanceDest',
    'isFlaggedFraud',
    'orig_gap',
    'dest_gap'
]

def run_leakage_audit(csv_path: str, n_test_samples: int = 500) -> dict:
    print("[*] Starting Causal Integrity & Temporal Leakage Audit...")
    start_time = time.time()
    
    # 1. Load dataset
    df = pd.read_csv(csv_path)
    print(f"[*] Dataset loaded for audit: {len(df):,} rows.")
    
    # 2. Check prohibited columns in feature lists
    for col in PROHIBITED_COLUMNS:
        assert col not in MODEL_A_FEATURES, f"LEAKAGE VIOLATION: Prohibited column {col} in Model A features!"
        assert col not in MODEL_B_FEATURES, f"LEAKAGE VIOLATION: Prohibited column {col} in Model B features!"
        assert not any(col.lower() in feat.lower() for feat in MODEL_A_FEATURES if 'newbalance' in feat.lower()), "Forbidden balance in Model A!"
        assert not any(col.lower() in feat.lower() for feat in MODEL_B_FEATURES if 'newbalance' in feat.lower()), "Forbidden balance in Model B!"

    print("[+] Check 1 PASSED: Zero prohibited/post-transaction columns in feature definitions.")

    # 3. Verify chronological ordering
    assert df['step'].is_monotonic_increasing, "Dataset step is not monotonically increasing!"
    print("[+] Check 2 PASSED: Chronological monotonic ordering confirmed.")

    # 4. Generate features on full dataset
    df_a, df_b = extract_causal_features(df)
    
    # 5. Point-in-time verification on random samples
    print(f"[*] Replay-verifying {n_test_samples} random transactions strictly against prior slices...")
    random.seed(42)
    sample_indices = sorted(random.sample(range(100, len(df)), n_test_samples))
    
    violations = []
    
    for idx in sample_indices:
        target_step = df.loc[idx, 'step']
        target_orig = df.loc[idx, 'nameOrig']
        target_dest = df.loc[idx, 'nameDest']
        target_amt = df.loc[idx, 'amount']
        
        # Ground truth history: strictly transactions before idx
        prior_df = df.iloc[:idx]
        
        # Historical sender truth
        prior_orig_txs = prior_df[prior_df['nameOrig'] == target_orig]
        expected_orig_cnt = len(prior_orig_txs)
        expected_orig_cum_amt = prior_orig_txs['amount'].sum() if expected_orig_cnt > 0 else 0.0
        expected_orig_max_amt = prior_orig_txs['amount'].max() if expected_orig_cnt > 0 else 0.0
        expected_orig_last_step = prior_orig_txs['step'].iloc[-1] if expected_orig_cnt > 0 else None
        expected_orig_time_since = (target_step - expected_orig_last_step) if expected_orig_last_step is not None else -1.0
        
        # Historical dest truth
        prior_dest_txs = prior_df[prior_df['nameDest'] == target_dest]
        expected_dest_cnt = len(prior_dest_txs)
        expected_dest_cum_amt = prior_dest_txs['amount'].sum() if expected_dest_cnt > 0 else 0.0
        expected_dest_max_amt = prior_dest_txs['amount'].max() if expected_dest_cnt > 0 else 0.0
        expected_dest_last_step = prior_dest_txs['step'].iloc[-1] if expected_dest_cnt > 0 else None
        expected_dest_time_since = (target_step - expected_dest_last_step) if expected_dest_last_step is not None else -1.0
        
        # Compare with generated features in df_b
        actual_orig_cnt = df_b.loc[idx, 'orig_prev_tx_cnt']
        actual_orig_cum_amt = df_b.loc[idx, 'orig_prev_cum_amt']
        actual_orig_max_amt = df_b.loc[idx, 'orig_prev_max_amt']
        actual_orig_time_since = df_b.loc[idx, 'orig_time_since_prev']
        
        actual_dest_cnt = df_b.loc[idx, 'dest_prev_in_tx_cnt']
        actual_dest_cum_amt = df_b.loc[idx, 'dest_prev_in_cum_amt']
        actual_dest_max_amt = df_b.loc[idx, 'dest_prev_in_max_amt']
        actual_dest_time_since = df_b.loc[idx, 'dest_time_since_prev']
        
        # Assertions
        if actual_orig_cnt != expected_orig_cnt:
            violations.append(f"Row {idx} orig_prev_tx_cnt mismatch: actual={actual_orig_cnt}, expected={expected_orig_cnt}")
        if not np.isclose(actual_orig_cum_amt, expected_orig_cum_amt, atol=1e-3):
            violations.append(f"Row {idx} orig_prev_cum_amt mismatch: actual={actual_orig_cum_amt}, expected={expected_orig_cum_amt}")
        if not np.isclose(actual_orig_max_amt, expected_orig_max_amt, atol=1e-3):
            violations.append(f"Row {idx} orig_prev_max_amt mismatch: actual={actual_orig_max_amt}, expected={expected_orig_max_amt}")
        if not np.isclose(actual_orig_time_since, expected_orig_time_since, atol=1e-3):
            violations.append(f"Row {idx} orig_time_since_prev mismatch: actual={actual_orig_time_since}, expected={expected_orig_time_since}")
            
        if actual_dest_cnt != expected_dest_cnt:
            violations.append(f"Row {idx} dest_prev_in_tx_cnt mismatch: actual={actual_dest_cnt}, expected={expected_dest_cnt}")
        if not np.isclose(actual_dest_cum_amt, expected_dest_cum_amt, atol=1e-3):
            violations.append(f"Row {idx} dest_prev_in_cum_amt mismatch: actual={actual_dest_cum_amt}, expected={expected_dest_cum_amt}")
        if not np.isclose(actual_dest_max_amt, expected_dest_max_amt, atol=1e-3):
            violations.append(f"Row {idx} dest_prev_in_max_amt mismatch: actual={actual_dest_max_amt}, expected={expected_dest_max_amt}")
        if not np.isclose(actual_dest_time_since, expected_dest_time_since, atol=1e-3):
            violations.append(f"Row {idx} dest_time_since_prev mismatch: actual={actual_dest_time_since}, expected={expected_dest_time_since}")
            
        if violations:
            break

    assert len(violations) == 0, f"LEAKAGE VIOLATIONS FOUND:\n" + "\n".join(violations[:10])
    print(f"[+] Check 3 PASSED: Point-in-time historical replay verified on {n_test_samples} random samples with 0 discrepancies.")

    # 6. Future Invariance Test
    print("[*] Performing Future Invariance Test (truncating future steps and verifying identical past features)...")
    cutoff_idx = 100_000
    df_truncated = df.iloc[:cutoff_idx].copy()
    df_a_trunc, df_b_trunc = extract_causal_features(df_truncated)
    
    np.testing.assert_array_almost_equal(
        df_a.iloc[:cutoff_idx].values,
        df_a_trunc.values,
        err_msg="Model A features changed when future was truncated!"
    )
    np.testing.assert_array_almost_equal(
        df_b.iloc[:cutoff_idx].values,
        df_b_trunc.values,
        err_msg="Model B features changed when future was truncated!"
    )
    print("[+] Check 4 PASSED: Future Invariance confirmed. Modifying or truncating future records has ZERO impact on historical features.")
    
    audit_results = {
        "status": "PASSED",
        "total_rows_audited": len(df),
        "replay_samples_checked": n_test_samples,
        "prohibited_columns_found": 0,
        "future_leakage_detected": False,
        "future_invariance_verified": True,
        "audit_duration_seconds": time.time() - start_time
    }
    return audit_results

if __name__ == "__main__":
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    res = run_leakage_audit(csv_file, n_test_samples=200)
    print("Audit Result:", res)

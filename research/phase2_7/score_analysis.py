"""
Risk Sentinel — Phase 2.7: Score & Probability Distribution Analysis (Audit 2)
Analyzes:
1. Score distributions, quantiles, min/max/median for Model A and B across splits.
2. Number of observations above threshold ladder (0.50, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999).
3. Calibration diagnostics and mathematical explanation of high threshold requirement (~0.98-0.99).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.phase2_6.causal_features import extract_causal_features, MODEL_A_FEATURES, MODEL_B_FEATURES

THRESHOLDS = [0.50, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999]
QUANTILES = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.995, 0.999, 0.9999]

def get_distribution_stats(scores: np.ndarray, y_true: np.ndarray) -> dict:
    quantiles_dict = {f"p{int(q*1000)/10}%": float(np.percentile(scores, q * 100)) for q in QUANTILES}
    
    threshold_counts = {}
    for th in THRESHOLDS:
        mask_above = scores >= th
        total_above = int(mask_above.sum())
        fraud_above = int(y_true[mask_above].sum())
        nonfraud_above = total_above - fraud_above
        prec = fraud_above / total_above if total_above > 0 else 0.0
        
        threshold_counts[f"th_{th:.3f}"] = {
            "total_above": total_above,
            "fraud_above": fraud_above,
            "nonfraud_above": nonfraud_above,
            "precision_in_bucket": prec
        }
        
    hist_bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 1.0]
    hist_counts, _ = np.histogram(scores, bins=hist_bins)
    histogram_dict = {f"[{hist_bins[i]:.3f}, {hist_bins[i+1]:.3f})": int(hist_counts[i]) for i in range(len(hist_counts))}
    
    return {
        "min": float(np.min(scores)),
        "max": float(np.max(scores)),
        "mean": float(np.mean(scores)),
        "median": float(np.median(scores)),
        "std": float(np.std(scores)),
        "quantiles": quantiles_dict,
        "counts_above_threshold": threshold_counts,
        "histogram": histogram_dict
    }

def run_score_analysis(csv_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print("AUDIT 2: SCORE & PROBABILITY INTEGRITY ANALYSIS")
    print("==================================================")
    
    df = pd.read_csv(csv_path)
    df_a, df_b = extract_causal_features(df)
    
    train_mask = (df['step'] >= 1) & (df['step'] <= 322)
    val_mask = (df['step'] >= 323) & (df['step'] <= 377)
    test_mask = (df['step'] >= 378) & (df['step'] <= 743)
    
    y = df['isFraud'].to_numpy()
    y_train, y_val, y_test = y[train_mask], y[val_mask], y[test_mask]
    
    X_train_a, X_val_a, X_test_a = df_a[train_mask].to_numpy(dtype=np.float32), df_a[val_mask].to_numpy(dtype=np.float32), df_a[test_mask].to_numpy(dtype=np.float32)
    X_train_b, X_val_b, X_test_b = df_b[train_mask].to_numpy(dtype=np.float32), df_b[val_mask].to_numpy(dtype=np.float32), df_b[test_mask].to_numpy(dtype=np.float32)
    
    print("[*] Training HistGradientBoosting models for score distribution analysis...")
    hgb_a = HistGradientBoostingClassifier(class_weight='balanced', max_iter=150, random_state=42, min_samples_leaf=50)
    hgb_a.fit(X_train_a, y_train)
    
    hgb_b = HistGradientBoostingClassifier(class_weight='balanced', max_iter=150, random_state=42, min_samples_leaf=50)
    hgb_b.fit(X_train_b, y_train)
    
    # Predict probabilities
    prob_val_a = hgb_a.predict_proba(X_val_a)[:, 1]
    prob_test_a = hgb_a.predict_proba(X_test_a)[:, 1]
    
    prob_val_b = hgb_b.predict_proba(X_val_b)[:, 1]
    prob_test_b = hgb_b.predict_proba(X_test_b)[:, 1]
    
    # Distribution diagnostics
    stats_val_a = get_distribution_stats(prob_val_a, y_val)
    stats_test_a = get_distribution_stats(prob_test_a, y_test)
    
    stats_val_b = get_distribution_stats(prob_val_b, y_val)
    stats_test_b = get_distribution_stats(prob_test_b, y_test)
    
    # Mathematical explanation of calibration shift:
    # Prior in training: p_raw = 3633 / 4433703 = 0.0008194
    # Re-weighted prior under class_weight='balanced': p_balanced = 0.50
    # Logit shift = ln((1-p_raw)/p_raw) = ln(4430070 / 3633) = ln(1219.4) = +7.106
    # An event with true posterior probability p_true = 0.01 gets predicted as:
    # logit_pred = logit_true + 7.106 = ln(0.01/0.99) + 7.106 = -4.595 + 7.106 = +2.511 -> sigmoid(+2.511) = 0.925!
    calibration_math = {
        "training_raw_fraud_prior": float(y_train.mean()),
        "effective_balanced_prior": 0.50,
        "bayes_logit_shift": float(np.log((len(y_train) - y_train.sum()) / y_train.sum())),
        "explanation": (
            "Because class_weight='balanced' artificiality inflates fraud weight by 1,219.4x during tree loss computation, "
            "the raw predict_proba output is NOT a true Bayesian posterior probability of fraud, but a re-weighted risk score. "
            "A model output score of 0.99 corresponds to a calibrated true posterior probability of ~0.076. "
            "Therefore, an operating threshold of 0.98-0.99 is mathematically natural and expected for balanced GBDTs."
        )
    }
    
    results = {
        "model_a_validation": stats_val_a,
        "model_a_future_test": stats_test_a,
        "model_b_validation": stats_val_b,
        "model_b_future_test": stats_test_b,
        "calibration_forensics": calibration_math
    }
    
    out_file = os.path.join(output_dir, "score_distribution.json")
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"[+] Score distribution analysis complete. Saved to {out_file}")
    return results, (prob_val_a, prob_test_a, prob_val_b, prob_test_b, y_val, y_test)

if __name__ == "__main__":
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    out_d = r"c:\Users\raahe\Downloads\razorpay\research\phase2_7\artifacts"
    run_score_analysis(csv_file, out_d)

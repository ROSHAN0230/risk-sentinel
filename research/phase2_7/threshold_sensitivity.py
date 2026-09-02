"""
Risk Sentinel — Phase 2.7: Dense Threshold Sensitivity Analysis (Audit 3)
Evaluates dense threshold ladder around operating region strictly on VALIDATION data:
[0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99, 0.995, 0.997, 0.999]
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DENSE_THRESHOLDS = [
    0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99, 0.995, 0.997, 0.999
]

FP_PENALTIES = [0.001, 0.005, 0.01, 0.02, 0.05]

def evaluate_threshold_dense(y_true, y_prob, amounts, thresholds=None):
    if thresholds is None:
        thresholds = DENSE_THRESHOLDS
        
    rows = []
    for th in thresholds:
        y_pred = (y_prob >= th).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
        
        fraud_mask = (y_true == 1)
        nonfraud_mask = (y_true == 0)
        pred_fraud_mask = (y_pred == 1)
        pred_nonfraud_mask = (y_pred == 0)
        
        detected_amt = float(amounts[fraud_mask & pred_fraud_mask].sum())
        missed_amt = float(amounts[fraud_mask & pred_nonfraud_mask].sum())
        flagged_nonfraud_amt = float(amounts[nonfraud_mask & pred_fraud_mask].sum())
        
        cost_01 = missed_amt + flagged_nonfraud_amt * 0.001
        cost_05 = missed_amt + flagged_nonfraud_amt * 0.005
        cost_10 = missed_amt + flagged_nonfraud_amt * 0.010
        cost_20 = missed_amt + flagged_nonfraud_amt * 0.020
        cost_50 = missed_amt + flagged_nonfraud_amt * 0.050
        
        rows.append({
            "threshold": th,
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "fpr": fpr,
            "fnr": fnr,
            "detected_fraud_amount": detected_amt,
            "missed_fraud_amount": missed_amt,
            "flagged_nonfraud_amount": flagged_nonfraud_amt,
            "total_cost_fp_0.1%": cost_01,
            "total_cost_fp_0.5%": cost_05,
            "total_cost_fp_1.0%": cost_10,
            "total_cost_fp_2.0%": cost_20,
            "total_cost_fp_5.0%": cost_50
        })
    return rows

def run_threshold_sensitivity_audit(y_val, prob_val_b, amt_val, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print("AUDIT 3: DENSE THRESHOLD SENSITIVITY SWEEP (VAL)")
    print("==================================================")
    
    rows = evaluate_threshold_dense(y_val, prob_val_b, amt_val)
    df_sweep = pd.DataFrame(rows)
    
    csv_path = os.path.join(output_dir, "threshold_sensitivity.csv")
    df_sweep.to_csv(csv_path, index=False)
    print(f"[+] Dense threshold sensitivity saved to {csv_path}")
    return df_sweep

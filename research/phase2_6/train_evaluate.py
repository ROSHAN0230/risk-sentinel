"""
Risk Sentinel — Phase 2.6: Model Training, Validation Threshold Sweep, and Future Test Evaluation
Rigorous comparison of Causal Baseline (Model A) vs Stateful Behavioral Model (Model B).
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_recall_curve,
    roc_curve,
    auc,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.phase2_6.causal_features import extract_causal_features, MODEL_A_FEATURES, MODEL_B_FEATURES

FP_COST_ASSUMPTIONS = [0.001, 0.005, 0.01, 0.02, 0.05] # 0.1%, 0.5%, 1%, 2%, 5%

def evaluate_predictions_at_threshold(y_true, y_prob, amounts, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    
    # Financial metrics
    fraud_mask = (y_true == 1)
    nonfraud_mask = (y_true == 0)
    pred_fraud_mask = (y_pred == 1)
    pred_nonfraud_mask = (y_pred == 0)
    
    detected_fraud_amt = float(amounts[fraud_mask & pred_fraud_mask].sum())
    missed_fraud_amt = float(amounts[fraud_mask & pred_nonfraud_mask].sum()) # FN financial loss
    flagged_nonfraud_amt = float(amounts[nonfraud_mask & pred_fraud_mask].sum()) # FP exposed volume
    
    # Costs under different FP penalty assumptions
    costs = {}
    for fp_pct in FP_COST_ASSUMPTIONS:
        fp_pct_key = f"{fp_pct*100:.1f}%"
        intervention_burden = flagged_nonfraud_amt * fp_pct
        total_cost = missed_fraud_amt + intervention_burden
        costs[fp_pct_key] = {
            "intervention_burden": float(intervention_burden),
            "total_financial_loss": float(total_cost)
        }
        
    return {
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
        "detected_fraud_amount": detected_fraud_amt,
        "missed_fraud_amount": missed_fraud_amt,
        "flagged_nonfraud_amount": flagged_nonfraud_amt,
        "costs_by_fp_assumption": costs
    }

def run_threshold_sweep(y_true, y_prob, amounts, thresholds=None):
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.99, 99)
    
    results = []
    for th in thresholds:
        res = evaluate_predictions_at_threshold(y_true, y_prob, amounts, th)
        results.append(res)
    return results

def run_experiment_pipeline(csv_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()
    print("==================================================")
    print("RISK SENTINEL — PHASE 2.6 EXPERIMENT PIPELINE")
    print("==================================================")
    
    # 1. Load raw dataset
    print(f"[*] Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"[*] Total records: {len(df):,}")
    
    # 2. Extract Causal Features for Model A and Model B
    df_feat_a, df_feat_b = extract_causal_features(df)
    
    # 3. Create strict chronological masks
    train_mask = (df['step'] >= 1) & (df['step'] <= 322)
    val_mask = (df['step'] >= 323) & (df['step'] <= 377)
    test_mask = (df['step'] >= 378) & (df['step'] <= 743)
    
    y = df['isFraud'].to_numpy(dtype=np.int32)
    amounts = df['amount'].to_numpy(dtype=np.float64)
    
    y_train, y_val, y_test = y[train_mask], y[val_mask], y[test_mask]
    amt_train, amt_val, amt_test = amounts[train_mask], amounts[val_mask], amounts[test_mask]
    
    print(f"[*] Split sizes: Train={len(y_train):,} (Fraud={y_train.sum():,}), Val={len(y_val):,} (Fraud={y_val.sum():,}), Test={len(y_test):,} (Fraud={y_test.sum():,})")
    
    # Pre-scale features for Logistic Regression
    print("[*] Preprocessing features for Logistic Regression...")
    scaler_a = StandardScaler()
    scaler_b = StandardScaler()
    
    X_train_a = df_feat_a[train_mask].to_numpy(dtype=np.float32)
    X_val_a = df_feat_a[val_mask].to_numpy(dtype=np.float32)
    X_test_a = df_feat_a[test_mask].to_numpy(dtype=np.float32)
    
    X_train_b = df_feat_b[train_mask].to_numpy(dtype=np.float32)
    X_val_b = df_feat_b[val_mask].to_numpy(dtype=np.float32)
    X_test_b = df_feat_b[test_mask].to_numpy(dtype=np.float32)
    
    X_train_a_scaled = scaler_a.fit_transform(X_train_a)
    X_val_a_scaled = scaler_a.transform(X_val_a)
    X_test_a_scaled = scaler_a.transform(X_test_a)
    
    X_train_b_scaled = scaler_b.fit_transform(X_train_b)
    X_val_b_scaled = scaler_b.transform(X_val_b)
    X_test_b_scaled = scaler_b.transform(X_test_b)
    
    # 4. Train Models
    models = {}
    
    # Model A - Logistic Regression
    print("[*] Training Model A: Logistic Regression (Causal Baseline)...")
    lr_a = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42, n_jobs=-1)
    lr_a.fit(X_train_a_scaled, y_train)
    models['Model_A_LR'] = {
        'model': lr_a,
        'scaled': True,
        'features': MODEL_A_FEATURES,
        'val_X': X_val_a_scaled,
        'test_X': X_test_a_scaled
    }
    
    # Model A - HistGradientBoosting
    print("[*] Training Model A: HistGradientBoosting (Causal Baseline)...")
    hgb_a = HistGradientBoostingClassifier(class_weight='balanced', max_iter=150, random_state=42, min_samples_leaf=50)
    hgb_a.fit(X_train_a, y_train)
    models['Model_A_HGB'] = {
        'model': hgb_a,
        'scaled': False,
        'features': MODEL_A_FEATURES,
        'val_X': X_val_a,
        'test_X': X_test_a
    }
    
    # Model B - Logistic Regression
    print("[*] Training Model B: Logistic Regression (Stateful Behavioral)...")
    lr_b = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42, n_jobs=-1)
    lr_b.fit(X_train_b_scaled, y_train)
    models['Model_B_LR'] = {
        'model': lr_b,
        'scaled': True,
        'features': MODEL_B_FEATURES,
        'val_X': X_val_b_scaled,
        'test_X': X_test_b_scaled
    }
    
    # Model B - HistGradientBoosting
    print("[*] Training Model B: HistGradientBoosting (Stateful Behavioral)...")
    hgb_b = HistGradientBoostingClassifier(class_weight='balanced', max_iter=150, random_state=42, min_samples_leaf=50)
    hgb_b.fit(X_train_b, y_train)
    models['Model_B_HGB'] = {
        'model': hgb_b,
        'scaled': False,
        'features': MODEL_B_FEATURES,
        'val_X': X_val_b,
        'test_X': X_test_b
    }
    
    # 5. Validation Evaluation & Threshold Selection
    print("==================================================")
    print("VALIDATION EVALUATION & THRESHOLD SELECTION")
    print("==================================================")
    
    val_summary = {}
    val_sweeps = {}
    
    for name, m_info in models.items():
        model = m_info['model']
        val_X = m_info['val_X']
        val_prob = model.predict_proba(val_X)[:, 1]
        m_info['val_prob'] = val_prob
        
        pr_auc = float(average_precision_score(y_val, val_prob))
        roc_auc = float(roc_auc_score(y_val, val_prob))
        
        sweep = run_threshold_sweep(y_val, val_prob, amt_val)
        val_sweeps[name] = sweep
        
        # Best threshold by F1
        best_f1_entry = max(sweep, key=lambda x: x['f1'])
        # Best threshold by total financial cost at 1.0% FP cost assumption
        best_cost_1pct_entry = min(sweep, key=lambda x: x['costs_by_fp_assumption']['1.0%']['total_financial_loss'])
        
        val_summary[name] = {
            'pr_auc': pr_auc,
            'roc_auc': roc_auc,
            'best_f1_threshold': best_f1_entry['threshold'],
            'best_f1_score': best_f1_entry['f1'],
            'best_f1_precision': best_f1_entry['precision'],
            'best_f1_recall': best_f1_entry['recall'],
            'best_f1_fpr': best_f1_entry['fpr'],
            'best_cost_1pct_threshold': best_cost_1pct_entry['threshold'],
            'best_cost_1pct_loss': best_cost_1pct_entry['costs_by_fp_assumption']['1.0%']['total_financial_loss'],
            'best_cost_1pct_recall': best_cost_1pct_entry['recall'],
            'best_cost_1pct_fpr': best_cost_1pct_entry['fpr']
        }
        print(f"[{name}] Validation PR-AUC: {pr_auc:.5f} | ROC-AUC: {roc_auc:.5f} | Best F1: {best_f1_entry['f1']:.4f} (at th={best_f1_entry['threshold']:.2f}) | Min Cost 1%: {best_cost_1pct_entry['costs_by_fp_assumption']['1.0%']['total_financial_loss']:,.2f} (at th={best_cost_1pct_entry['threshold']:.2f})")
    
    # 6. Select Champion Model and Optimal Operating Policy on Validation
    # Highest validation PR-AUC / lowest financial loss
    champion_name = 'Model_B_HGB' if val_summary['Model_B_HGB']['pr_auc'] >= val_summary['Model_A_HGB']['pr_auc'] else 'Model_A_HGB'
    print(f"[*] Champion Model selected based on Validation PR-AUC/Economics: {champion_name}")
    
    # Operating threshold: based on validation F1 / balanced economic tradeoff
    # We lock the threshold that optimizes validation performance
    selected_threshold = val_summary[champion_name]['best_f1_threshold']
    print(f"[*] Locked Operating Threshold for Future Test: {selected_threshold:.2f}")
    
    # 7. Held-Out Future Test Evaluation (Steps 378–743)
    print("==================================================")
    print("HELD-OUT FUTURE TEST EVALUATION (STEPS 378–743)")
    print("==================================================")
    
    test_results = {}
    
    for name, m_info in models.items():
        model = m_info['model']
        test_X = m_info['test_X']
        test_prob = model.predict_proba(test_X)[:, 1]
        m_info['test_prob'] = test_prob
        
        pr_auc = float(average_precision_score(y_test, test_prob))
        roc_auc = float(roc_auc_score(y_test, test_prob))
        
        # Evaluate at locked validation threshold for this model
        th = val_summary[name]['best_f1_threshold']
        perf_at_locked_th = evaluate_predictions_at_threshold(y_test, test_prob, amt_test, th)
        
        test_results[name] = {
            'pr_auc': pr_auc,
            'roc_auc': roc_auc,
            'locked_threshold': th,
            'performance_at_locked_threshold': perf_at_locked_th
        }
        
        print(f"[{name}] Future Test PR-AUC: {pr_auc:.5f} | ROC-AUC: {roc_auc:.5f} | Precision: {perf_at_locked_th['precision']:.4f} | Recall: {perf_at_locked_th['recall']:.4f} | F1: {perf_at_locked_th['f1']:.4f} | FPR: {perf_at_locked_th['fpr']:.6f} | Missed Fraud Loss: {perf_at_locked_th['missed_fraud_amount']:,.2f}")

    # 8. Cold-Start Subgroup Performance on Future Test
    print("==================================================")
    print("COLD-START vs KNOWN-HISTORY SUBGROUP EVALUATION")
    print("==================================================")
    
    test_df_feat_b = df_feat_b[test_mask]
    sender_cold_start_mask = (test_df_feat_b['is_sender_cold_start'] == 1.0).to_numpy()
    sender_known_mask = ~sender_cold_start_mask
    
    dest_cold_start_mask = (test_df_feat_b['is_dest_cold_start'] == 1.0).to_numpy()
    dest_known_mask = ~dest_cold_start_mask
    
    cold_start_breakdown = {}
    
    for name in ['Model_A_HGB', 'Model_B_HGB']:
        test_prob = models[name]['test_prob']
        th = val_summary[name]['best_f1_threshold']
        
        # Senders
        perf_sender_cold = evaluate_predictions_at_threshold(y_test[sender_cold_start_mask], test_prob[sender_cold_start_mask], amt_test[sender_cold_start_mask], th)
        perf_sender_known = evaluate_predictions_at_threshold(y_test[sender_known_mask], test_prob[sender_known_mask], amt_test[sender_known_mask], th)
        
        # Destinations
        perf_dest_cold = evaluate_predictions_at_threshold(y_test[dest_cold_start_mask], test_prob[dest_cold_start_mask], amt_test[dest_cold_start_mask], th)
        perf_dest_known = evaluate_predictions_at_threshold(y_test[dest_known_mask], test_prob[dest_known_mask], amt_test[dest_known_mask], th)
        
        cold_start_breakdown[name] = {
            'sender_cold_start': {
                'total_tx': int(sender_cold_start_mask.sum()),
                'fraud_tx': int(y_test[sender_cold_start_mask].sum()),
                'perf': perf_sender_cold
            },
            'sender_known_history': {
                'total_tx': int(sender_known_mask.sum()),
                'fraud_tx': int(y_test[sender_known_mask].sum()),
                'perf': perf_sender_known
            },
            'dest_cold_start': {
                'total_tx': int(dest_cold_start_mask.sum()),
                'fraud_tx': int(y_test[dest_cold_start_mask].sum()),
                'perf': perf_dest_cold
            },
            'dest_known_history': {
                'total_tx': int(dest_known_mask.sum()),
                'fraud_tx': int(y_test[dest_known_mask].sum()),
                'perf': perf_dest_known
            }
        }
        
    # 9. Feature Importance / Forensics
    print("==================================================")
    print("FEATURE FORENSICS & IMPORTANCE AUDIT")
    print("==================================================")
    
    # Feature coefficients for Logistic Regression
    lr_b_coefs = dict(zip(MODEL_B_FEATURES, [float(c) for c in lr_b.coef_[0]]))
    sorted_lr_coefs = sorted(lr_b_coefs.items(), key=lambda x: abs(x[1]), reverse=True)
    
    # Save artifacts
    artifacts = {
        'val_summary': val_summary,
        'val_sweeps': val_sweeps,
        'test_results': test_results,
        'cold_start_breakdown': cold_start_breakdown,
        'lr_b_coefficients': sorted_lr_coefs,
        'champion_model': champion_name,
        'locked_threshold': selected_threshold,
        'total_runtime_seconds': time.time() - t0
    }
    
    out_file = os.path.join(output_dir, "phase2_6_experiment_results.json")
    with open(out_file, 'w') as f:
        json.dump(artifacts, f, indent=2)
        
    print(f"[*] Experiment completed in {time.time() - t0:.2f}s. Results saved to {out_file}")
    return artifacts

if __name__ == "__main__":
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    out_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase2_6\artifacts"
    run_experiment_pipeline(csv_file, out_dir)

"""
Risk Sentinel — Export Frozen Production Model Artifacts
Fits Model A (Causal Baseline HGB) and Model B (Stateful HGB) strictly on Train Split (steps 1-322),
serializes them to src/engine/artifacts/, computes SHA-256 hashes, and writes the engine manifest.
"""

import os
import sys
import hashlib
import json
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.phase2_6.causal_features import extract_causal_features, MODEL_A_FEATURES, MODEL_B_FEATURES

def compute_sha256(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def export_models(csv_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print("EXPORTING FROZEN PRODUCTION MODEL ARTIFACTS")
    print("==================================================")
    
    t0 = time.time()
    df = pd.read_csv(csv_path)
    train_mask = (df['step'] >= 1) & (df['step'] <= 322)
    
    print(f"[*] Extracting causal features on {len(df):,} rows...")
    df_a, df_b = extract_causal_features(df)
    
    y_train = df.loc[train_mask, 'isFraud'].to_numpy(dtype=np.int32)
    X_train_a = df_a[train_mask].to_numpy(dtype=np.float32)
    X_train_b = df_b[train_mask].to_numpy(dtype=np.float32)
    
    print(f"[*] Fitting Model A (Causal Baseline HGB) on {len(y_train):,} training rows (Fraud={y_train.sum():,})...")
    model_a = HistGradientBoostingClassifier(
        class_weight='balanced',
        max_iter=150,
        random_state=42,
        min_samples_leaf=50
    )
    model_a.fit(X_train_a, y_train)
    
    print(f"[*] Fitting Model B (Stateful HGB) on {len(y_train):,} training rows (Fraud={y_train.sum():,})...")
    model_b = HistGradientBoostingClassifier(
        class_weight='balanced',
        max_iter=150,
        random_state=42,
        min_samples_leaf=50
    )
    model_b.fit(X_train_b, y_train)
    
    # Save artifacts
    path_a = os.path.join(output_dir, "model_a_causal_hgb.joblib")
    path_b = os.path.join(output_dir, "model_b_stateful_hgb.joblib")
    
    joblib.dump(model_a, path_a, compress=3)
    joblib.dump(model_b, path_b, compress=3)
    
    sha_a = compute_sha256(path_a)
    sha_b = compute_sha256(path_b)
    
    with open(os.path.join(output_dir, "model_a_causal_hgb.sha256"), 'w') as f:
        f.write(sha_a)
        
    with open(os.path.join(output_dir, "model_b_stateful_hgb.sha256"), 'w') as f:
        f.write(sha_b)
        
    manifest = {
        "engine_version": "v2.8.0-prod",
        "created_at_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "training_metadata": {
            "dataset": "PS_20174392719_1491204439457_log.csv",
            "train_step_range": [1, 322],
            "train_row_count": int(train_mask.sum()),
            "train_fraud_count": int(y_train.sum()),
            "class_weight": "balanced"
        },
        "model_a": {
            "model_id": "model_a_causal_hgb_v1.0.0",
            "filename": "model_a_causal_hgb.joblib",
            "sha256": sha_a,
            "feature_count": len(MODEL_A_FEATURES),
            "features": MODEL_A_FEATURES,
            "role": "BASELINE_FALLBACK"
        },
        "model_b": {
            "model_id": "model_b_stateful_hgb_v1.0.0",
            "filename": "model_b_stateful_hgb.joblib",
            "sha256": sha_b,
            "feature_count": len(MODEL_B_FEATURES),
            "features": MODEL_B_FEATURES,
            "role": "CHAMPION_STATEFUL"
        },
        "operating_policy": {
            "threshold_high": 0.990,
            "threshold_medium": 0.900,
            "policy_version": "v1.2.0-frozen"
        }
    }
    
    manifest_path = os.path.join(output_dir, "engine_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[+] Model A exported. SHA-256: {sha_a}")
    print(f"[+] Model B exported. SHA-256: {sha_b}")
    print(f"[+] Manifest saved to {manifest_path}")
    print(f"[*] Export completed in {time.time() - t0:.2f}s.")

if __name__ == "__main__":
    csv_f = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    out_d = r"c:\Users\raahe\Downloads\razorpay\src\engine\artifacts"
    export_models(csv_f, out_d)

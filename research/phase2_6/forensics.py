"""
Risk Sentinel — Phase 2.6: Dataset Forensics
Inspects PS_20174392719_1491204439457_log.csv without altering data.
"""

import os
import json
import time
import pandas as pd
import numpy as np

def run_forensics(csv_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print(f"[*] Starting Dataset Forensics on: {csv_path}")
    start_time = time.time()
    
    # Load dataset
    df = pd.read_csv(csv_path)
    load_time = time.time() - start_time
    print(f"[*] Loaded {len(df):,} rows in {load_time:.2f} seconds.")
    
    # Basic structural properties
    num_rows, num_cols = df.shape
    columns = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in df.columns}
    missing_values = df.isnull().sum().to_dict()
    num_duplicates = int(df.duplicated().sum())
    
    # Chronological properties
    min_step = int(df['step'].min())
    max_step = int(df['step'].max())
    is_step_monotonic = bool(df['step'].is_monotonic_increasing)
    
    # Target distribution
    target_counts = df['isFraud'].value_counts().to_dict()
    fraud_rate = float(df['isFraud'].mean())
    is_flagged_fraud_counts = df['isFlaggedFraud'].value_counts().to_dict()
    
    # Transaction type distribution
    type_counts = df['type'].value_counts().to_dict()
    type_fraud_counts = df.groupby('type')['isFraud'].agg(['count', 'sum', 'mean']).to_dict(orient='index')
    
    # Split distributions (Train: 1-322, Val: 323-377, Test: 378-743)
    train_mask = (df['step'] >= 1) & (df['step'] <= 322)
    val_mask = (df['step'] >= 323) & (df['step'] <= 377)
    test_mask = (df['step'] >= 378) & (df['step'] <= 743)
    
    splits_info = {
        "train": {
            "step_range": [1, 322],
            "total_rows": int(train_mask.sum()),
            "fraud_rows": int(df.loc[train_mask, 'isFraud'].sum()),
            "fraud_rate": float(df.loc[train_mask, 'isFraud'].mean()) if train_mask.sum() > 0 else 0.0,
            "fraud_amount_total": float(df.loc[train_mask & (df['isFraud'] == 1), 'amount'].sum()),
            "nonfraud_amount_total": float(df.loc[train_mask & (df['isFraud'] == 0), 'amount'].sum()),
        },
        "val": {
            "step_range": [323, 377],
            "total_rows": int(val_mask.sum()),
            "fraud_rows": int(df.loc[val_mask, 'isFraud'].sum()),
            "fraud_rate": float(df.loc[val_mask, 'isFraud'].mean()) if val_mask.sum() > 0 else 0.0,
            "fraud_amount_total": float(df.loc[val_mask & (df['isFraud'] == 1), 'amount'].sum()),
            "nonfraud_amount_total": float(df.loc[val_mask & (df['isFraud'] == 0), 'amount'].sum()),
        },
        "future_test": {
            "step_range": [378, 743],
            "total_rows": int(test_mask.sum()),
            "fraud_rows": int(df.loc[test_mask, 'isFraud'].sum()),
            "fraud_rate": float(df.loc[test_mask, 'isFraud'].mean()) if test_mask.sum() > 0 else 0.0,
            "fraud_amount_total": float(df.loc[test_mask & (df['isFraud'] == 1), 'amount'].sum()),
            "nonfraud_amount_total": float(df.loc[test_mask & (df['isFraud'] == 0), 'amount'].sum()),
        }
    }
    
    # Entity repetitions
    num_unique_senders = int(df['nameOrig'].nunique())
    num_unique_destinations = int(df['nameDest'].nunique())
    sender_repeat_counts = int((df['nameOrig'].value_counts() > 1).sum())
    dest_repeat_counts = int((df['nameDest'].value_counts() > 1).sum())
    
    sender_repeat_rate = sender_repeat_counts / num_unique_senders if num_unique_senders > 0 else 0.0
    dest_repeat_rate = dest_repeat_counts / num_unique_destinations if num_unique_destinations > 0 else 0.0
    
    forensics_report = {
        "dataset_path": csv_path,
        "num_rows": num_rows,
        "num_cols": num_cols,
        "columns": columns,
        "dtypes": dtypes,
        "missing_values": {k: int(v) for k, v in missing_values.items()},
        "num_duplicates": num_duplicates,
        "min_step": min_step,
        "max_step": max_step,
        "is_step_monotonic": is_step_monotonic,
        "target_counts": {str(k): int(v) for k, v in target_counts.items()},
        "fraud_rate": fraud_rate,
        "is_flagged_fraud_counts": {str(k): int(v) for k, v in is_flagged_fraud_counts.items()},
        "type_counts": {str(k): int(v) for k, v in type_counts.items()},
        "type_fraud_stats": {k: {stat: float(val) for stat, val in v.items()} for k, v in type_fraud_counts.items()},
        "splits_info": splits_info,
        "entity_statistics": {
            "num_unique_senders": num_unique_senders,
            "num_unique_destinations": num_unique_destinations,
            "senders_with_multiple_tx": sender_repeat_counts,
            "sender_repeat_fraction": sender_repeat_rate,
            "destinations_with_multiple_tx": dest_repeat_counts,
            "destination_repeat_fraction": dest_repeat_rate
        }
    }
    
    output_file = os.path.join(output_dir, "dataset_forensics.json")
    with open(output_file, 'w') as f:
        json.dump(forensics_report, f, indent=2)
        
    print(f"[*] Dataset forensics completed. Saved to {output_file}")
    return forensics_report

if __name__ == "__main__":
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    out_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase2_6\artifacts"
    report = run_forensics(csv_file, out_dir)
    print("Forensics summary completed successfully.")

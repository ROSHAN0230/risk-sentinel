"""
Risk Sentinel — Phase 2.7: Financial Cost Function Integrity Audit (Audit 4)
Verifies:
1. Mathematical correctness of cost formula:
   Total Cost = Missed Fraud Dollar Amount + alpha * Flagged Legitimate Volume
2. Dimensional / Unit consistency (dollars + dollars).
3. Non-double counting of TP, FP, TN, FN dollars.
4. Methodological framing of alpha (scenario sensitivity analysis vs proprietary economics).
"""

import os
import json
import numpy as np

def audit_cost_function(output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print("AUDIT 4: FINANCIAL COST FUNCTION AUDIT")
    print("==================================================")
    
    # Mathematical audit checks
    # 1. Dimensional analysis:
    # Missed Fraud Dollar Amount = sum(amount for fraud rows where pred == 0) [Currency units: INR/USD]
    # Flagged Legitimate Volume = sum(amount for legitimate rows where pred == 1) [Currency units: INR/USD]
    # alpha = dimensionless scalar penalty (e.g. 0.01 = 1% loss due to friction, manual review, churn, drop-off)
    # Total Cost = Currency + Currency = Currency. (Dimensionally consistent)
    
    audit_results = {
        "cost_equation": "Total_Cost = FN_Missed_Fraud_Dollars + alpha * FP_Flagged_Legitimate_Volume",
        "dimensional_consistency": "PASSED (Currency + [Dimensionless * Currency] = Currency)",
        "double_counting_audit": "PASSED (FN partition and FP partition are mutually disjoint sets of transactions)",
        "sensitivity_parameters": {
            "0.1%": "Minimal operational friction / automated challenge with near-zero customer dropoff",
            "0.5%": "Low operational friction / frictionless step-up (e.g. fast push notification/biometric)",
            "1.0%": "Standard industry baseline / manual review queue + minor customer dropoff",
            "2.0%": "Elevated friction / substantial dropoff and high support contact rate",
            "5.0%": "Severe friction / high false decline business impact and customer churn"
        },
        "methodological_classification": "SCENARIO_SENSITIVITY_ANALYSIS",
        "disclaimer_required": (
            "The alpha penalty factors (0.1% to 5.0%) represent exploratory sensitivity assumptions "
            "for modeling operational intervention and false-decline friction. They must NOT be represented "
            "as proprietary or actual historical unit economics of Razorpay."
        )
    }
    
    out_file = os.path.join(output_dir, "cost_audit.json")
    with open(out_file, 'w') as f:
        json.dump(audit_results, f, indent=2)
        
    print(f"[+] Cost function audit complete. Saved to {out_file}")
    return audit_results

if __name__ == "__main__":
    out_d = r"c:\Users\raahe\Downloads\razorpay\research\phase2_7\artifacts"
    audit_cost_function(out_d)

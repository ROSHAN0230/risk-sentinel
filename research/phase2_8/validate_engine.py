"""
Risk Sentinel — Phase 2.8: Decision Engine Validation Harness
Simulates end-to-end transaction evaluation, explanation generation,
policy enforcement, fallback degradation, and audit logging.
"""

import os
import sys
import time
import uuid
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.phase2_6.causal_features import extract_causal_features, MODEL_A_FEATURES, MODEL_B_FEATURES

class RiskDecisionEngine:
    def __init__(self, model_a: HistGradientBoostingClassifier, model_b: HistGradientBoostingClassifier):
        self.model_a = model_a
        self.model_b = model_b
        self.engine_version = "v2.8.0-prod"
        self.model_version = "v1.0.0-HGB"
        self.policy_version = "v1.2.0-frozen"
        self.threshold_high = 0.990
        self.threshold_medium = 0.900
        
        # In-memory stateful store
        # sender_state: id -> [cnt, cum_amt, max_amt, last_step, tf_cnt, co_cnt, dest_set]
        # dest_state: id -> [cnt, cum_amt, max_amt, last_step, orig_set]
        # pair_state: (orig, dest) -> [cnt, last_step]
        self.sender_state: Dict[str, list] = {}
        self.dest_state: Dict[str, list] = {}
        self.pair_state: Dict[Tuple[str, str], list] = {}
        
    def validate_schema(self, tx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        required = ['transaction_id', 'step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg', 'nameDest', 'oldbalanceDest']
        for r in required:
            if r not in tx:
                return False, f"Missing field: {r}"
        if tx['amount'] <= 0.0:
            return False, "Amount must be strictly positive"
        if tx['oldbalanceOrg'] < 0.0 or tx['oldbalanceDest'] < 0.0:
            return False, "Balance cannot be negative"
        if tx['type'] not in ['TRANSFER', 'CASH_OUT', 'PAYMENT', 'CASH_IN', 'DEBIT']:
            return False, f"Invalid type: {tx['type']}"
        return True, None

    def read_state_strictly_before(self, orig: str, dest: str, step: int, simulate_timeout: bool = False) -> Tuple[dict, bool]:
        if simulate_timeout:
            return {}, True # Fallback mode triggered
            
        s_data = self.sender_state.get(orig)
        d_data = self.dest_state.get(dest)
        p_data = self.pair_state.get((orig, dest))
        
        state_ctx = {
            'sender': s_data,
            'dest': d_data,
            'pair': p_data
        }
        return state_ctx, False

    def build_model_a_features(self, tx: dict) -> np.ndarray:
        step = int(tx['step'])
        amt = float(tx['amount'])
        old_orig = float(tx['oldbalanceOrg'])
        old_dest = float(tx['oldbalanceDest'])
        tx_type = tx['type']
        
        feat = [
            amt,
            np.log1p(amt),
            old_orig,
            old_dest,
            old_orig - amt,
            old_orig / (amt + 1.0),
            1.0 if old_orig == 0.0 else 0.0,
            1.0 if old_dest == 0.0 else 0.0,
            float(step % 24),
            float((step // 24) % 7),
            1.0 if tx_type == 'CASH_OUT' else 0.0,
            1.0 if tx_type == 'TRANSFER' else 0.0,
            1.0 if tx_type == 'PAYMENT' else 0.0,
            1.0 if tx_type == 'CASH_IN' else 0.0,
            1.0 if tx_type == 'DEBIT' else 0.0
        ]
        return np.array([feat], dtype=np.float32)

    def build_model_b_features(self, tx: dict, state_ctx: dict) -> np.ndarray:
        a_feats = list(self.build_model_a_features(tx)[0])
        step = int(tx['step'])
        amt = float(tx['amount'])
        
        s_data = state_ctx.get('sender')
        d_data = state_ctx.get('dest')
        p_data = state_ctx.get('pair')
        
        if s_data is None:
            is_sender_cold = 1.0
            orig_prev_cnt = 0.0
            orig_prev_cum = 0.0
            orig_prev_avg = 0.0
            orig_prev_max = 0.0
            orig_time_since = -1.0
            orig_unique_dest = 0.0
            orig_tf_cnt = 0.0
            orig_co_cnt = 0.0
            orig_ratio = 1.0
            orig_diff = 0.0
        else:
            is_sender_cold = 0.0
            cnt, cum, max_a, last_s, tf_cnt, co_cnt, d_set = s_data
            orig_prev_cnt = float(cnt)
            orig_prev_cum = float(cum)
            orig_prev_avg = float(cum / cnt)
            orig_prev_max = float(max_a)
            orig_time_since = float(step - last_s)
            orig_unique_dest = float(len(d_set))
            orig_tf_cnt = float(tf_cnt)
            orig_co_cnt = float(co_cnt)
            orig_ratio = float(amt / (orig_prev_avg + 1.0))
            orig_diff = float(amt - max_a)
            
        if d_data is None:
            is_dest_cold = 1.0
            dest_prev_cnt = 0.0
            dest_prev_cum = 0.0
            dest_prev_avg = 0.0
            dest_prev_max = 0.0
            dest_time_since = -1.0
            dest_unique_orig = 0.0
        else:
            is_dest_cold = 0.0
            cnt_d, cum_d, max_d, last_sd, o_set = d_data
            dest_prev_cnt = float(cnt_d)
            dest_prev_cum = float(cum_d)
            dest_prev_avg = float(cum_d / cnt_d)
            dest_prev_max = float(max_d)
            dest_time_since = float(step - last_sd)
            dest_unique_orig = float(len(o_set))
            
        if p_data is None:
            is_pair_novel = 1.0
            pair_cnt = 0.0
            pair_time = -1.0
        else:
            is_pair_novel = 0.0
            cnt_p, last_sp = p_data
            pair_cnt = float(cnt_p)
            pair_time = float(step - last_sp)
            
        extra = [
            orig_prev_cnt, orig_prev_cum, orig_prev_avg, orig_prev_max, orig_time_since,
            orig_unique_dest, orig_tf_cnt, orig_co_cnt,
            dest_prev_cnt, dest_prev_cum, dest_prev_avg, dest_prev_max, dest_time_since,
            dest_unique_orig,
            pair_cnt, pair_time,
            is_sender_cold, is_dest_cold, is_pair_novel,
            orig_ratio, orig_diff
        ]
        return np.array([a_feats + extra], dtype=np.float32)

    def generate_explanations(self, tx: dict, score: float, band: str, state_ctx: dict) -> dict:
        amt = float(tx['amount'])
        old_orig = float(tx['oldbalanceOrg'])
        tx_type = tx['type']
        
        codes = []
        is_exact_drain = np.isclose(old_orig, amt, atol=1e-2) and amt > 0.0
        
        if is_exact_drain:
            codes.append("RC_EXACT_BALANCE_DRAIN")
        elif old_orig > 0 and (amt / (old_orig + 1.0)) > 0.90:
            codes.append("RC_SEVERE_LIQUIDITY_DRAIN")
            
        if tx_type in ['TRANSFER', 'CASH_OUT'] and tx['oldbalanceDest'] == 0.0:
            codes.append("RC_HIGH_RISK_CHANNEL_COMBO")
            
        if state_ctx.get('sender') is None and amt >= 100000.0:
            codes.append("RC_NEW_ACCOUNT_LARGE_OUTFLOW")
            
        d_data = state_ctx.get('dest')
        if d_data and d_data[0] >= 3:
            codes.append("RC_DEST_MULE_VELOCITY")
            
        if not codes:
            codes.append("RC_BENIGN_BASELINE")
            
        primary = codes[0]
        narrative = f"Risk evaluated as {band} (Score: {score:.4f}). Primary causal driver: {primary}."
        if primary == "RC_EXACT_BALANCE_DRAIN":
            narrative = f"Transaction attempts exact 100% liquidation of available sender balance (${amt:,.2f}) via {tx_type}."
            
        return {
            "primary_code": primary,
            "all_codes": codes,
            "narrative": narrative,
            "causal_evidence": {
                "amount": amt,
                "oldbalanceOrg": old_orig,
                "liquidation_pct": float(amt / old_orig * 100.0) if old_orig > 0 else 0.0,
                "channel": tx_type
            }
        }

    def resolve_action(self, band: str, tx_type: str, amt: float) -> Tuple[str, str]:
        # Fast-track bypass for low-risk empirical channels
        if tx_type in ['PAYMENT', 'CASH_IN', 'DEBIT']:
            return "APPROVED", "APPROVE"
            
        if band == "LOW_RISK":
            return "APPROVED", "APPROVE"
        elif band == "MEDIUM_RISK":
            if amt < 50000.0:
                return "CHALLENGED", "STEP_UP_CHALLENGE"
            else:
                return "REVIEW_REQUIRED", "MANUAL_REVIEW"
        else: # HIGH_RISK
            return "DECLINED", "DECLINE"

    def update_state_post_decision(self, tx: dict):
        step = int(tx['step'])
        orig = tx['nameOrig']
        dest = tx['nameDest']
        amt = float(tx['amount'])
        tx_type = tx['type']
        
        is_tf = 1 if tx_type == 'TRANSFER' else 0
        is_co = 1 if tx_type == 'CASH_OUT' else 0
        
        s_data = self.sender_state.get(orig)
        if s_data is None:
            self.sender_state[orig] = [1, amt, amt, step, is_tf, is_co, set([dest])]
        else:
            s_data[0] += 1
            s_data[1] += amt
            if amt > s_data[2]:
                s_data[2] = amt
            s_data[3] = step
            s_data[4] += is_tf
            s_data[5] += is_co
            s_data[6].add(dest)
            
        d_data = self.dest_state.get(dest)
        if d_data is None:
            self.dest_state[dest] = [1, amt, amt, step, set([orig])]
        else:
            d_data[0] += 1
            d_data[1] += amt
            if amt > d_data[2]:
                d_data[2] = amt
            d_data[3] = step
            d_data[4].add(orig)
            
        p_key = (orig, dest)
        p_data = self.pair_state.get(p_key)
        if p_data is None:
            self.pair_state[p_key] = [1, step]
        else:
            p_data[0] += 1
            p_data[1] = step

    def evaluate_transaction(self, tx: dict, force_fallback: bool = False) -> dict:
        t0 = time.time()
        
        # 1. Validation
        valid, err = self.validate_schema(tx)
        if not valid:
            return {"error": err, "status_code": 400}
            
        # 2. Stateful read (strictly < t)
        state_ctx, fallback_triggered = self.read_state_strictly_before(
            tx['nameOrig'], tx['nameDest'], int(tx['step']), simulate_timeout=force_fallback
        )
        
        # 3 & 4. Features & Model Inference
        if fallback_triggered:
            X = self.build_model_a_features(tx)
            score = float(self.model_a.predict_proba(X)[0, 1])
            model_used = "MODEL_A_CAUSAL_BASELINE_FALLBACK"
        else:
            X = self.build_model_b_features(tx, state_ctx)
            score = float(self.model_b.predict_proba(X)[0, 1])
            model_used = "MODEL_B_STATEFUL_HGB"
            
        # 5. Risk Band
        if score >= self.threshold_high:
            band = "HIGH_RISK"
        elif score >= self.threshold_medium:
            band = "MEDIUM_RISK"
        else:
            band = "LOW_RISK"
            
        # 6. Explanations
        reasons = self.generate_explanations(tx, score, band, state_ctx)
        
        # 7. Policy & Action
        decision, action = self.resolve_action(band, tx['type'], float(tx['amount']))
        
        # 8. Post-Decision State Update
        self.update_state_post_decision(tx)
        
        latency_ms = (time.time() - t0) * 1000.0
        
        # 9 & 10. Audit & Response
        response = {
            "transaction_id": tx['transaction_id'],
            "evaluation_id": f"eval_{uuid.uuid4()}",
            "timestamp_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "risk_score": round(score, 6),
            "risk_band": band,
            "decision": decision,
            "action": action,
            "reasons": reasons,
            "engine_metadata": {
                "engine_version": self.engine_version,
                "model_version": self.model_version,
                "model_type": model_used,
                "policy_version": self.policy_version,
                "operating_threshold": self.threshold_high,
                "fallback_triggered": fallback_triggered,
                "execution_latency_ms": round(latency_ms, 3)
            }
        }
        return response

def validate_all():
    print("==================================================")
    print("RISK SENTINEL — PHASE 2.8 ENGINE VALIDATION")
    print("==================================================")
    
    csv_file = r"c:\Users\raahe\Downloads\razorpay\PS_20174392719_1491204439457_log.csv"
    out_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase2_8\artifacts"
    os.makedirs(out_dir, exist_ok=True)
    
    # Train lightweight models on Train split for live validation
    df = pd.read_csv(csv_file)
    train_mask = (df['step'] >= 1) & (df['step'] <= 322)
    df_a, df_b = extract_causal_features(df)
    
    y_train = df.loc[train_mask, 'isFraud'].to_numpy()
    X_train_a = df_a[train_mask].to_numpy(dtype=np.float32)
    X_train_b = df_b[train_mask].to_numpy(dtype=np.float32)
    
    print("[*] Fitting validation GBDT models...")
    hgb_a = HistGradientBoostingClassifier(class_weight='balanced', max_iter=100, random_state=42, min_samples_leaf=50)
    hgb_a.fit(X_train_a, y_train)
    
    hgb_b = HistGradientBoostingClassifier(class_weight='balanced', max_iter=100, random_state=42, min_samples_leaf=50)
    hgb_b.fit(X_train_b, y_train)
    
    engine = RiskDecisionEngine(hgb_a, hgb_b)
    
    # Test Scenarios
    scenarios = [
        {
            "name": "Scenario 1: Legitimate Payment (Low Risk)",
            "tx": {
                "transaction_id": str(uuid.uuid4()),
                "step": 400,
                "type": "PAYMENT",
                "amount": 142.50,
                "nameOrig": "C10001",
                "oldbalanceOrg": 5000.00,
                "nameDest": "M20001",
                "oldbalanceDest": 0.00
            },
            "force_fallback": False
        },
        {
            "name": "Scenario 2: Critical Fraud - Exact 100% Balance Drain (Transfer)",
            "tx": {
                "transaction_id": str(uuid.uuid4()),
                "step": 401,
                "type": "TRANSFER",
                "amount": 250000.00,
                "nameOrig": "C10002",
                "oldbalanceOrg": 250000.00,
                "nameDest": "C20002",
                "oldbalanceDest": 0.00
            },
            "force_fallback": False
        },
        {
            "name": "Scenario 3: Borderline New Account Outflow (Medium Risk Step-Up)",
            "tx": {
                "transaction_id": str(uuid.uuid4()),
                "step": 402,
                "type": "TRANSFER",
                "amount": 80000.00,
                "nameOrig": "C10003",
                "oldbalanceOrg": 150000.00,
                "nameDest": "C20003",
                "oldbalanceDest": 5000.00
            },
            "force_fallback": False
        },
        {
            "name": "Scenario 4: Fallback Mode Simulation (State Store Timeout -> Model A)",
            "tx": {
                "transaction_id": str(uuid.uuid4()),
                "step": 403,
                "type": "TRANSFER",
                "amount": 180000.00,
                "nameOrig": "C10004",
                "oldbalanceOrg": 180000.00,
                "nameDest": "C20004",
                "oldbalanceDest": 0.00
            },
            "force_fallback": True
        }
    ]
    
    results = []
    for sc in scenarios:
        res = engine.evaluate_transaction(sc['tx'], force_fallback=sc['force_fallback'])
        results.append({
            "scenario": sc['name'],
            "input": sc['tx'],
            "output": res
        })
        print(f"\n[+] {sc['name']}:")
        print(f"    Risk Score: {res['risk_score']} | Band: {res['risk_band']} | Decision: {res['decision']} | Action: {res['action']}")
        print(f"    Model: {res['engine_metadata']['model_type']} | Latency: {res['engine_metadata']['execution_latency_ms']}ms")
        print(f"    Reason: {res['reasons']['primary_code']} -> {res['reasons']['narrative']}")
        
    out_file = os.path.join(out_dir, "engine_validation_report.json")
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\n[+] Validation report saved to {out_file}")
    return results

if __name__ == "__main__":
    validate_all()

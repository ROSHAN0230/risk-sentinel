"""
Risk Sentinel — Causal Feature Pipeline (Production Runtime)
Extracts 15-dim Model A features and 21-dim Model B features strictly at decision time.
Zero post-transaction leakage, zero future lookahead.
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from src.engine.schemas import EvaluateRequest

MODEL_A_FEATURE_NAMES = [
    'amount',
    'log_amount',
    'oldbalanceOrg',
    'oldbalanceDest',
    'diff_orig_bal_amt',
    'ratio_orig_bal_amt',
    'is_orig_zero',
    'is_dest_zero',
    'hour_of_day',
    'day_of_week',
    'is_type_CASH_OUT',
    'is_type_TRANSFER',
    'is_type_PAYMENT',
    'is_type_CASH_IN',
    'is_type_DEBIT'
]

MODEL_B_FEATURE_NAMES = MODEL_A_FEATURE_NAMES + [
    'orig_prev_tx_cnt',
    'orig_prev_cum_amt',
    'orig_prev_avg_amt',
    'orig_prev_max_amt',
    'orig_time_since_prev',
    'orig_unique_dest_cnt',
    'orig_prev_transfer_cnt',
    'orig_prev_cash_out_cnt',
    'dest_prev_in_tx_cnt',
    'dest_prev_in_cum_amt',
    'dest_prev_in_avg_amt',
    'dest_prev_in_max_amt',
    'dest_time_since_prev',
    'dest_unique_orig_cnt',
    'pair_prev_tx_cnt',
    'pair_time_since_prev',
    'is_sender_cold_start',
    'is_dest_cold_start',
    'is_pair_novel',
    'orig_amt_vs_avg_ratio',
    'orig_amt_vs_max_diff'
]

class FeaturePipeline:
    def __init__(self):
        self.feature_names_a = MODEL_A_FEATURE_NAMES
        self.feature_names_b = MODEL_B_FEATURE_NAMES
        
    def build_features_a(self, req: EvaluateRequest) -> Tuple[np.ndarray, Dict[str, float]]:
        amt = float(req.amount)
        log_amt = float(np.log1p(amt))
        old_orig = float(req.oldbalanceOrg)
        old_dest = float(req.oldbalanceDest)
        diff_bal = float(old_orig - amt)
        ratio_bal = float(old_orig / (amt + 1.0))
        is_orig_zero = 1.0 if old_orig == 0.0 else 0.0
        is_dest_zero = 1.0 if old_dest == 0.0 else 0.0
        
        step = int(req.step)
        hour = float(step % 24)
        day = float((step // 24) % 7)
        
        t = req.type.value if hasattr(req.type, 'value') else str(req.type)
        is_co = 1.0 if t == 'CASH_OUT' else 0.0
        is_tf = 1.0 if t == 'TRANSFER' else 0.0
        is_pm = 1.0 if t == 'PAYMENT' else 0.0
        is_ci = 1.0 if t == 'CASH_IN' else 0.0
        is_db = 1.0 if t == 'DEBIT' else 0.0
        
        raw_list = [
            amt, log_amt, old_orig, old_dest, diff_bal, ratio_bal,
            is_orig_zero, is_dest_zero, hour, day,
            is_co, is_tf, is_pm, is_ci, is_db
        ]
        
        # Impute non-finite values safely
        cleaned = [0.0 if (v != v or v == float('inf') or v == float('-inf')) else float(v) for v in raw_list]
        arr = np.array([cleaned], dtype=np.float32)
        dict_repr = dict(zip(self.feature_names_a, cleaned))
        return arr, dict_repr

    def build_features_b(self, req: EvaluateRequest, state_ctx: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, float]]:
        arr_a, dict_a = self.build_features_a(req)
        a_list = list(arr_a[0])
        
        step = int(req.step)
        amt = float(req.amount)
        
        s_data = state_ctx.get('sender')
        d_data = state_ctx.get('dest')
        p_data = state_ctx.get('pair')
        
        # 1. Sender state
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
            orig_prev_avg = float(cum / cnt) if cnt > 0 else 0.0
            orig_prev_max = float(max_a)
            orig_time_since = float(step - last_s)
            orig_unique_dest = float(len(d_set))
            orig_tf_cnt = float(tf_cnt)
            orig_co_cnt = float(co_cnt)
            orig_ratio = float(amt / (orig_prev_avg + 1.0))
            orig_diff = float(amt - max_a)
            
        # 2. Destination state
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
            dest_prev_avg = float(cum_d / cnt_d) if cnt_d > 0 else 0.0
            dest_prev_max = float(max_d)
            dest_time_since = float(step - last_sd)
            dest_unique_orig = float(len(o_set))
            
        # 3. Pair interaction state
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
        
        full_list = a_list + extra
        cleaned = [0.0 if (v != v or v == float('inf') or v == float('-inf')) else float(v) for v in full_list]
        arr = np.array([cleaned], dtype=np.float32)
        dict_repr = dict(zip(self.feature_names_b, cleaned))
        return arr, dict_repr

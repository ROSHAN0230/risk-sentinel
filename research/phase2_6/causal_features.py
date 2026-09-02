"""
Risk Sentinel — Phase 2.6: Causal Feature Generation
Strictly point-in-time and causal sequential feature extraction.
Zero post-transaction leakage, zero future lookahead.
"""

import numpy as np
import pandas as pd
import time
from typing import Dict, Tuple, List

MODEL_A_FEATURES = [
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

MODEL_B_EXTRA_FEATURES = [
    # Sender state
    'orig_prev_tx_cnt',
    'orig_prev_cum_amt',
    'orig_prev_avg_amt',
    'orig_prev_max_amt',
    'orig_time_since_prev',
    'orig_unique_dest_cnt',
    'orig_prev_transfer_cnt',
    'orig_prev_cash_out_cnt',
    # Destination state
    'dest_prev_in_tx_cnt',
    'dest_prev_in_cum_amt',
    'dest_prev_in_avg_amt',
    'dest_prev_in_max_amt',
    'dest_time_since_prev',
    'dest_unique_orig_cnt',
    # Interaction state
    'pair_prev_tx_cnt',
    'pair_time_since_prev',
    # Novelty & Cold-start
    'is_sender_cold_start',
    'is_dest_cold_start',
    'is_pair_novel',
    # Behavioral deviation
    'orig_amt_vs_avg_ratio',
    'orig_amt_vs_max_diff'
]

MODEL_B_FEATURES = MODEL_A_FEATURES + MODEL_B_EXTRA_FEATURES

def extract_causal_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts Model A and Model B features causally.
    Returns (df_model_a, df_model_b)
    """
    print("[*] Extracting Model A (Point-in-Time Stateless Baseline) features...")
    t0 = time.time()
    
    n_rows = len(df)
    
    # Pre-extract numpy arrays for fast processing
    steps = df['step'].to_numpy(dtype=np.int32)
    types = df['type'].to_numpy()
    amounts = df['amount'].to_numpy(dtype=np.float64)
    oldbalanceOrg = df['oldbalanceOrg'].to_numpy(dtype=np.float64)
    oldbalanceDest = df['oldbalanceDest'].to_numpy(dtype=np.float64)
    nameOrig = df['nameOrig'].to_numpy()
    nameDest = df['nameDest'].to_numpy()
    
    # Model A feature arrays
    log_amount = np.log1p(amounts)
    diff_orig_bal_amt = oldbalanceOrg - amounts
    ratio_orig_bal_amt = oldbalanceOrg / (amounts + 1.0)
    is_orig_zero = (oldbalanceOrg == 0.0).astype(np.float32)
    is_dest_zero = (oldbalanceDest == 0.0).astype(np.float32)
    hour_of_day = (steps % 24).astype(np.float32)
    day_of_week = ((steps // 24) % 7).astype(np.float32)
    
    is_type_CASH_OUT = (types == 'CASH_OUT').astype(np.float32)
    is_type_TRANSFER = (types == 'TRANSFER').astype(np.float32)
    is_type_PAYMENT = (types == 'PAYMENT').astype(np.float32)
    is_type_CASH_IN = (types == 'CASH_IN').astype(np.float32)
    is_type_DEBIT = (types == 'DEBIT').astype(np.float32)
    
    model_a_dict = {
        'amount': amounts,
        'log_amount': log_amount,
        'oldbalanceOrg': oldbalanceOrg,
        'oldbalanceDest': oldbalanceDest,
        'diff_orig_bal_amt': diff_orig_bal_amt,
        'ratio_orig_bal_amt': ratio_orig_bal_amt,
        'is_orig_zero': is_orig_zero,
        'is_dest_zero': is_dest_zero,
        'hour_of_day': hour_of_day,
        'day_of_week': day_of_week,
        'is_type_CASH_OUT': is_type_CASH_OUT,
        'is_type_TRANSFER': is_type_TRANSFER,
        'is_type_PAYMENT': is_type_PAYMENT,
        'is_type_CASH_IN': is_type_CASH_IN,
        'is_type_DEBIT': is_type_DEBIT
    }
    df_model_a = pd.DataFrame(model_a_dict)
    print(f"[*] Model A features extracted in {time.time() - t0:.2f}s.")
    
    print("[*] Extracting Model B (Stateful Causal Behavioral) features sequentially...")
    t1 = time.time()
    
    # Allocate Model B extra feature arrays
    orig_prev_tx_cnt = np.zeros(n_rows, dtype=np.float32)
    orig_prev_cum_amt = np.zeros(n_rows, dtype=np.float64)
    orig_prev_avg_amt = np.zeros(n_rows, dtype=np.float64)
    orig_prev_max_amt = np.zeros(n_rows, dtype=np.float64)
    orig_time_since_prev = np.full(n_rows, -1.0, dtype=np.float32)
    orig_unique_dest_cnt = np.zeros(n_rows, dtype=np.float32)
    orig_prev_transfer_cnt = np.zeros(n_rows, dtype=np.float32)
    orig_prev_cash_out_cnt = np.zeros(n_rows, dtype=np.float32)
    
    dest_prev_in_tx_cnt = np.zeros(n_rows, dtype=np.float32)
    dest_prev_in_cum_amt = np.zeros(n_rows, dtype=np.float64)
    dest_prev_in_avg_amt = np.zeros(n_rows, dtype=np.float64)
    dest_prev_in_max_amt = np.zeros(n_rows, dtype=np.float64)
    dest_time_since_prev = np.full(n_rows, -1.0, dtype=np.float32)
    dest_unique_orig_cnt = np.zeros(n_rows, dtype=np.float32)
    
    pair_prev_tx_cnt = np.zeros(n_rows, dtype=np.float32)
    pair_time_since_prev = np.full(n_rows, -1.0, dtype=np.float32)
    
    is_sender_cold_start = np.zeros(n_rows, dtype=np.float32)
    is_dest_cold_start = np.zeros(n_rows, dtype=np.float32)
    is_pair_novel = np.zeros(n_rows, dtype=np.float32)
    
    orig_amt_vs_avg_ratio = np.ones(n_rows, dtype=np.float32)
    orig_amt_vs_max_diff = np.zeros(n_rows, dtype=np.float32)
    
    # Tracking dictionaries for causal state
    # sender_state: nameOrig -> [cnt, cum_amt, max_amt, last_step, transfer_cnt, cash_out_cnt, set(dest)]
    # dest_state: nameDest -> [cnt, cum_amt, max_amt, last_step, set(orig)]
    # pair_state: (nameOrig, nameDest) -> [cnt, last_step]
    sender_state: Dict[str, list] = {}
    dest_state: Dict[str, list] = {}
    pair_state: Dict[Tuple[str, str], list] = {}
    
    # Progress monitoring
    log_interval = 1_000_000
    
    for i in range(n_rows):
        if i > 0 and i % log_interval == 0:
            print(f"    Processed {i:,} / {n_rows:,} rows ({i/n_rows*100:.1f}%) in {time.time() - t1:.1f}s...")
            
        step = steps[i]
        orig = nameOrig[i]
        dest = nameDest[i]
        amt = amounts[i]
        tx_type = types[i]
        
        # 1. READ SENDER HISTORY (strictly before i)
        s_data = sender_state.get(orig)
        if s_data is None:
            # Cold start sender
            is_sender_cold_start[i] = 1.0
            orig_prev_tx_cnt[i] = 0.0
            orig_prev_cum_amt[i] = 0.0
            orig_prev_avg_amt[i] = 0.0
            orig_prev_max_amt[i] = 0.0
            orig_time_since_prev[i] = -1.0
            orig_unique_dest_cnt[i] = 0.0
            orig_prev_transfer_cnt[i] = 0.0
            orig_prev_cash_out_cnt[i] = 0.0
            orig_amt_vs_avg_ratio[i] = 1.0
            orig_amt_vs_max_diff[i] = 0.0
        else:
            # Established sender history
            cnt, cum_amt, max_amt, last_step, transfer_cnt, cash_out_cnt, dest_set = s_data
            is_sender_cold_start[i] = 0.0
            orig_prev_tx_cnt[i] = cnt
            orig_prev_cum_amt[i] = cum_amt
            avg_amt = cum_amt / cnt if cnt > 0 else 0.0
            orig_prev_avg_amt[i] = avg_amt
            orig_prev_max_amt[i] = max_amt
            orig_time_since_prev[i] = float(step - last_step)
            orig_unique_dest_cnt[i] = float(len(dest_set))
            orig_prev_transfer_cnt[i] = float(transfer_cnt)
            orig_prev_cash_out_cnt[i] = float(cash_out_cnt)
            orig_amt_vs_avg_ratio[i] = float(amt / (avg_amt + 1.0))
            orig_amt_vs_max_diff[i] = float(amt - max_amt)
            
        # 2. READ DESTINATION HISTORY (strictly before i)
        d_data = dest_state.get(dest)
        if d_data is None:
            # Cold start destination
            is_dest_cold_start[i] = 1.0
            dest_prev_in_tx_cnt[i] = 0.0
            dest_prev_in_cum_amt[i] = 0.0
            dest_prev_in_avg_amt[i] = 0.0
            dest_prev_in_max_amt[i] = 0.0
            dest_time_since_prev[i] = -1.0
            dest_unique_orig_cnt[i] = 0.0
        else:
            cnt_d, cum_d, max_d, last_step_d, orig_set = d_data
            is_dest_cold_start[i] = 0.0
            dest_prev_in_tx_cnt[i] = cnt_d
            dest_prev_in_cum_amt[i] = cum_d
            dest_prev_in_avg_amt[i] = cum_d / cnt_d if cnt_d > 0 else 0.0
            dest_prev_in_max_amt[i] = max_d
            dest_time_since_prev[i] = float(step - last_step_d)
            dest_unique_orig_cnt[i] = float(len(orig_set))
            
        # 3. READ PAIR INTERACTION HISTORY (strictly before i)
        pair_key = (orig, dest)
        p_data = pair_state.get(pair_key)
        if p_data is None:
            is_pair_novel[i] = 1.0
            pair_prev_tx_cnt[i] = 0.0
            pair_time_since_prev[i] = -1.0
        else:
            cnt_p, last_step_p = p_data
            is_pair_novel[i] = 0.0
            pair_prev_tx_cnt[i] = cnt_p
            pair_time_since_prev[i] = float(step - last_step_p)
            
        # 4. UPDATE STATE (ONLY AFTER RECORDING PAST STATE FOR ROW i)
        is_tf = 1 if tx_type == 'TRANSFER' else 0
        is_co = 1 if tx_type == 'CASH_OUT' else 0
        
        if s_data is None:
            dest_set = set([dest])
            sender_state[orig] = [1, amt, amt, step, is_tf, is_co, dest_set]
        else:
            s_data[0] += 1
            s_data[1] += amt
            if amt > s_data[2]:
                s_data[2] = amt
            s_data[3] = step
            s_data[4] += is_tf
            s_data[5] += is_co
            s_data[6].add(dest)
            
        if d_data is None:
            orig_set = set([orig])
            dest_state[dest] = [1, amt, amt, step, orig_set]
        else:
            d_data[0] += 1
            d_data[1] += amt
            if amt > d_data[2]:
                d_data[2] = amt
            d_data[3] = step
            d_data[4].add(orig)
            
        if p_data is None:
            pair_state[pair_key] = [1, step]
        else:
            p_data[0] += 1
            p_data[1] = step

    model_b_dict = dict(model_a_dict)
    model_b_dict.update({
        'orig_prev_tx_cnt': orig_prev_tx_cnt,
        'orig_prev_cum_amt': orig_prev_cum_amt,
        'orig_prev_avg_amt': orig_prev_avg_amt,
        'orig_prev_max_amt': orig_prev_max_amt,
        'orig_time_since_prev': orig_time_since_prev,
        'orig_unique_dest_cnt': orig_unique_dest_cnt,
        'orig_prev_transfer_cnt': orig_prev_transfer_cnt,
        'orig_prev_cash_out_cnt': orig_prev_cash_out_cnt,
        'dest_prev_in_tx_cnt': dest_prev_in_tx_cnt,
        'dest_prev_in_cum_amt': dest_prev_in_cum_amt,
        'dest_prev_in_avg_amt': dest_prev_in_avg_amt,
        'dest_prev_in_max_amt': dest_prev_in_max_amt,
        'dest_time_since_prev': dest_time_since_prev,
        'dest_unique_orig_cnt': dest_unique_orig_cnt,
        'pair_prev_tx_cnt': pair_prev_tx_cnt,
        'pair_time_since_prev': pair_time_since_prev,
        'is_sender_cold_start': is_sender_cold_start,
        'is_dest_cold_start': is_dest_cold_start,
        'is_pair_novel': is_pair_novel,
        'orig_amt_vs_avg_ratio': orig_amt_vs_avg_ratio,
        'orig_amt_vs_max_diff': orig_amt_vs_max_diff
    })
    df_model_b = pd.DataFrame(model_b_dict)
    print(f"[*] Model B sequential extraction completed in {time.time() - t1:.2f}s.")
    
    return df_model_a, df_model_b

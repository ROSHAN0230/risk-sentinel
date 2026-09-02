"""
Risk Sentinel — Hybrid Causal Explanation Resolver
Translates model scores, tree split boundaries, and causal feature deltas
into deterministic, certified Reason Codes and human-readable narratives in <1.0ms.
"""

import numpy as np
from typing import Dict, Any, List
from src.engine.schemas import EvaluateRequest, ReasonDetails, RiskBand

REASON_TEMPLATES = {
    "RC_EXACT_BALANCE_DRAIN": "Transaction attempts exact 100% liquidation of available sender balance (${amount:,.2f}) via high-risk {channel} channel.",
    "RC_SEVERE_LIQUIDITY_DRAIN": "Transaction drains {drain_pct:.1f}% of sender total account liquidity (${amount:,.2f} of ${oldbalanceOrg:,.2f}).",
    "RC_DEST_MULE_VELOCITY": "Destination account exhibits mule aggregation velocity ({dest_unique_orig_cnt} unique senders across {dest_prev_in_tx_cnt} prior transactions).",
    "RC_NEW_ACCOUNT_LARGE_OUTFLOW": "First observed transaction for sender initiating high-value outflow (${amount:,.2f}).",
    "RC_HIGH_RISK_CHANNEL_COMBO": "Outflow routed to uninitialized/zero-balance destination via high-risk {channel} channel.",
    "RC_SENDER_AMOUNT_DEVIATION": "Transaction amount is {ratio:.1f}x higher than sender historical average (${avg:,.2f}).",
    "RC_FALLBACK_EVALUATION_ACTIVE": "State store unavailable; decision derived from causal point-in-time baseline features.",
    "RC_BENIGN_BASELINE": "Normal transaction velocity, adequate balance headroom, and established channel baseline."
}

class ExplanationResolver:
    def __init__(self):
        self.templates = REASON_TEMPLATES

    def resolve_explanations(
        self,
        req: EvaluateRequest,
        score: float,
        band: RiskBand,
        state_ctx: Dict[str, Any],
        fallback_active: bool = False
    ) -> ReasonDetails:
        amt = float(req.amount)
        old_orig = float(req.oldbalanceOrg)
        old_dest = float(req.oldbalanceDest)
        t_type = req.type.value if hasattr(req.type, 'value') else str(req.type)
        
        codes: List[str] = []
        evidence: Dict[str, Any] = {
            "amount": amt,
            "oldbalanceOrg": old_orig,
            "oldbalanceDest": old_dest,
            "channel": t_type,
            "risk_score": score
        }
        
        # 1. Fallback flag
        if fallback_active:
            codes.append("RC_FALLBACK_EVALUATION_ACTIVE")
            
        # 2. Exact balance liquidation
        is_exact_drain = np.isclose(old_orig, amt, atol=1e-2) and amt > 0.0
        if is_exact_drain:
            codes.append("RC_EXACT_BALANCE_DRAIN")
            evidence["liquidation_pct"] = 100.0
        elif old_orig > 0 and (amt / (old_orig + 1.0)) > 0.90:
            drain_pct = (amt / old_orig) * 100.0
            codes.append("RC_SEVERE_LIQUIDITY_DRAIN")
            evidence["liquidation_pct"] = round(drain_pct, 2)
            
        # 3. High risk channel combination
        if t_type in ['TRANSFER', 'CASH_OUT'] and old_dest == 0.0:
            codes.append("RC_HIGH_RISK_CHANNEL_COMBO")
            
        # 4. Destination mule aggregation
        d_data = state_ctx.get('dest')
        if d_data:
            dest_prev_cnt = d_data[0]
            dest_unique_orig = len(d_data[4])
            evidence["dest_prev_in_tx_cnt"] = dest_prev_cnt
            evidence["dest_unique_orig_cnt"] = dest_unique_orig
            if dest_prev_cnt >= 3 and dest_unique_orig >= 2:
                codes.append("RC_DEST_MULE_VELOCITY")
                
        # 5. Cold-start large outflow
        s_data = state_ctx.get('sender')
        if s_data is None:
            evidence["is_sender_cold_start"] = 1
            if amt >= 100000.0:
                codes.append("RC_NEW_ACCOUNT_LARGE_OUTFLOW")
        else:
            evidence["is_sender_cold_start"] = 0
            cnt, cum = s_data[0], s_data[1]
            avg_amt = (cum / cnt) if cnt > 0 else 0.0
            evidence["sender_historical_avg"] = avg_amt
            if avg_amt > 0 and (amt / (avg_amt + 1.0)) > 5.0:
                codes.append("RC_SENDER_AMOUNT_DEVIATION")
                evidence["sender_amount_ratio"] = round(amt / avg_amt, 2)
                
        # Default benign code
        if not codes or (len(codes) == 1 and codes[0] == "RC_FALLBACK_EVALUATION_ACTIVE" and band == RiskBand.LOW_RISK):
            if "RC_BENIGN_BASELINE" not in codes:
                codes.append("RC_BENIGN_BASELINE")
                
        primary_code = codes[0] if codes[0] != "RC_FALLBACK_EVALUATION_ACTIVE" or len(codes) == 1 else codes[1]
        
        # Build narrative
        template = self.templates.get(primary_code, "Risk evaluated as {band} (Score: {score:.4f}).")
        format_kwargs = {
            "amount": amt,
            "oldbalanceOrg": old_orig,
            "channel": t_type,
            "band": band.value if hasattr(band, 'value') else str(band),
            "score": score,
            "drain_pct": evidence.get("liquidation_pct", 0.0),
            "dest_unique_orig_cnt": evidence.get("dest_unique_orig_cnt", 0),
            "dest_prev_in_tx_cnt": evidence.get("dest_prev_in_tx_cnt", 0),
            "ratio": evidence.get("sender_amount_ratio", 1.0),
            "avg": evidence.get("sender_historical_avg", 0.0)
        }
        try:
            narrative = template.format(**format_kwargs)
        except Exception:
            narrative = f"Transaction flagged as {band.value} (Score: {score:.4f}) with reason {primary_code}."
            
        return ReasonDetails(
            primary_code=primary_code,
            all_codes=codes,
            narrative=narrative,
            causal_evidence=evidence
        )

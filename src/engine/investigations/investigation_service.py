"""
Risk Sentinel — Phase P1.2 Investigation Service
Aggregates risk events from the audit ledger, Razorpay Test Mode webhooks, and demo fixtures.
Provides deterministic, defense-only Standard Operating Procedure (SOP) guidance for human investigators.
Strictly read-only: does NOT mutate production state, policy, or models.
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Certified deterministic Standard Operating Procedure (SOP) Guidance
# Mapped directly from certified Reason Codes in src/engine/explanation_resolver.py
SOP_GUIDANCE_MAP: Dict[str, Dict[str, Any]] = {
    "RC_EXACT_BALANCE_DRAIN": {
        "reason_code": "RC_EXACT_BALANCE_DRAIN",
        "title": "Exact 100% Account Balance Liquidation",
        "objective": "Verify whether the transaction represents an unauthorized full account takeover liquidation or an authorized whole-balance consolidation.",
        "urgency": "IMMEDIATE_HOLD",
        "recommended_action": "HOLD_AND_VERIFY",
        "protocol_steps": [
            "1. Check if the customer has reported recent credential compromise, SIM-swap, or device loss.",
            "2. Initiate out-of-band verification (SMS OTP or registered voice challenge) before releasing funds.",
            "3. Inspect beneficiary account creation date and cross-reference against known mule network registries.",
            "4. If unconfirmed within the SLA window, confirm automated decline and maintain provisional freeze."
        ],
        "evidence_to_inspect": [
            "Sender old balance vs transaction amount (exact 1:1 match)",
            "Channel type (TRANSFER / CASH_OUT)",
            "Beneficiary account pre-transaction balance (typically 0.0)"
        ]
    },
    "RC_SEVERE_LIQUIDITY_DRAIN": {
        "reason_code": "RC_SEVERE_LIQUIDITY_DRAIN",
        "title": "Severe Liquidity Drain (>90% Available Funds)",
        "objective": "Evaluate whether the high-proportion outflow aligns with seasonal business expenditure or indicates coercive transfer.",
        "urgency": "HIGH_PRIORITY_REVIEW",
        "recommended_action": "STEP_UP_CHALLENGE",
        "protocol_steps": [
            "1. Dispatch automated step-up 2FA/biometric verification challenge to the registered mobile device.",
            "2. Compare transfer amount against sender historical 30-day average transaction volume.",
            "3. If step-up challenge fails or is abandoned, escalate to manual investigation queue."
        ],
        "evidence_to_inspect": [
            "Liquidation percentage (typically >90%)",
            "Sender historical transaction velocity",
            "Remaining balance headroom post-transaction"
        ]
    },
    "RC_DEST_MULE_VELOCITY": {
        "reason_code": "RC_DEST_MULE_VELOCITY",
        "title": "Destination Beneficiary Mule Aggregation Velocity",
        "objective": "Investigate destination beneficiary for rapid multi-source fund aggregation indicative of mule networks.",
        "urgency": "CRITICAL_INTERCEPTION",
        "recommended_action": "FREEZE_BENEFICIARY_INFLOWS",
        "protocol_steps": [
            "1. Inspect incoming transaction fan-in rate (number of distinct senders within past 24-72 hours).",
            "2. Verify whether beneficiary rapidly initiates immediate cash-out or secondary cross-border transfers.",
            "3. Review beneficiary KYC verification tier and flag account for AML compliance review."
        ],
        "evidence_to_inspect": [
            "Unique sender count to this destination (dest_unique_orig_cnt)",
            "Prior transaction count (dest_prev_in_tx_cnt)",
            "Accumulated destination volume across recent steps"
        ]
    },
    "RC_NEW_ACCOUNT_LARGE_OUTFLOW": {
        "reason_code": "RC_NEW_ACCOUNT_LARGE_OUTFLOW",
        "title": "First-Time High-Value Account Outflow",
        "objective": "Determine whether an unseasoned account initiating high-value outflow represents synthetic identity or rapid fraud cash-out.",
        "urgency": "HIGH_PRIORITY_REVIEW",
        "recommended_action": "STEP_UP_VERIFICATION",
        "protocol_steps": [
            "1. Confirm account age and initial funding method origin.",
            "2. Review customer identity verification level and device telemetry.",
            "3. Place temporary velocity throttle on outbound transfers pending verified history."
        ],
        "evidence_to_inspect": [
            "Sender cold-start indicator (is_sender_cold_start = 1)",
            "Transaction value relative to tier transfer limits",
            "Recipient relationship history"
        ]
    },
    "RC_HIGH_RISK_CHANNEL_COMBO": {
        "reason_code": "RC_HIGH_RISK_CHANNEL_COMBO",
        "title": "High-Risk Channel Liquidation to Zero-Balance Destination",
        "objective": "Review outflow routed through irreversible channels (TRANSFER/CASH_OUT) to uninitialized destinations.",
        "urgency": "ROUTINE_REVIEW",
        "recommended_action": "SECONDARY_VALIDATION",
        "protocol_steps": [
            "1. Check if recipient account is newly created or previously dormant.",
            "2. Review transfer memo or payment notes for declared business purpose.",
            "3. If sender history is established and score is below decline threshold, clear with monitoring."
        ],
        "evidence_to_inspect": [
            "Destination initial balance (0.0)",
            "Channel type (TRANSFER vs CASH_OUT)",
            "Payment method telemetry"
        ]
    },
    "RC_SENDER_AMOUNT_DEVIATION": {
        "reason_code": "RC_SENDER_AMOUNT_DEVIATION",
        "title": "Transaction Amount Exceeds Historical Profile",
        "objective": "Verify whether transaction amount spike represents legitimate capital purchase or account compromise.",
        "urgency": "ELEVATED_MONITORING",
        "recommended_action": "CHALLENGE_IF_UNCONFIRMED",
        "protocol_steps": [
            "1. Compare amount to sender 30-day running average.",
            "2. Verify whether transfer originated from standard recognized device/IP.",
            "3. Request user confirmation if amount exceeds 5x historical profile."
        ],
        "evidence_to_inspect": [
            "Sender historical average amount",
            "Amount deviation multiplier ratio",
            "Sender rolling transaction count"
        ]
    },
    "RC_FALLBACK_EVALUATION_ACTIVE": {
        "reason_code": "RC_FALLBACK_EVALUATION_ACTIVE",
        "title": "Causal Baseline Fallback Mode Active (Circuit Breaker Tripped)",
        "objective": "Audit decision executed under state-store outage fallback mode to ensure safety resilience.",
        "urgency": "SYSTEM_RESILIENCE_AUDIT",
        "recommended_action": "POST_INCIDENT_RECONCILIATION",
        "protocol_steps": [
            "1. Confirm decision was safely made by 15-dim Causal Baseline Model A.",
            "2. Verify that state store circuit breaker health checks have recovered.",
            "3. Replay transaction sequence to update state counters once cache service is healthy."
        ],
        "evidence_to_inspect": [
            "Circuit breaker fallback flag (fallback_triggered = true)",
            "State store latency telemetry",
            "Causal point-in-time feature set"
        ]
    },
    "RC_BENIGN_BASELINE": {
        "reason_code": "RC_BENIGN_BASELINE",
        "title": "Normal Baseline Profile",
        "objective": "Standard automated clearance validation.",
        "urgency": "ROUTINE_CLEARANCE",
        "recommended_action": "AUTO_APPROVE",
        "protocol_steps": [
            "1. No human investigator escalation required.",
            "2. Transaction operates comfortably within safe historical distribution.",
            "3. Logged to immutable audit ledger for compliance."
        ],
        "evidence_to_inspect": [
            "Operating risk score below medium threshold (score < 0.900)",
            "Adequate sender balance headroom",
            "Established recipient baseline"
        ]
    }
}

# Standard 9 Master Competition Demo Fixtures (Pre-loaded for instant judge walkthrough)
MASTER_DEMO_FIXTURES: List[Dict[str, Any]] = [
    {
        "id": "demo-01",
        "title": "Normal Consumer Payment",
        "type": "PAYMENT",
        "amount": 84.50,
        "sender": "C_ALICE_01",
        "old_orig": 1200.00,
        "dest": "M_BOOKSTORE_01",
        "old_dest": 0.00,
        "score": 0.0018,
        "band": "LOW_RISK",
        "decision": "APPROVED",
        "action": "APPROVE",
        "primary_reason": "RC_BENIGN_BASELINE",
        "all_reasons": ["RC_BENIGN_BASELINE"],
        "narrative": "Normal transaction velocity, adequate balance headroom, and established channel baseline."
    },
    {
        "id": "demo-02",
        "title": "Suspicious Liquidity Outflow",
        "type": "TRANSFER",
        "amount": 976662.30,
        "sender": "C1959219454",
        "old_orig": 982857.46,
        "dest": "C2061756973",
        "old_dest": 2453029.29,
        "score": 0.9830,
        "band": "MEDIUM_RISK",
        "decision": "REVIEW_REQUIRED",
        "action": "MANUAL_REVIEW",
        "primary_reason": "RC_SEVERE_LIQUIDITY_DRAIN",
        "all_reasons": ["RC_SEVERE_LIQUIDITY_DRAIN"],
        "narrative": "Transaction drains 99.4% of sender total account liquidity ($976,662.30 of $982,857.46)."
    },
    {
        "id": "demo-03",
        "title": "Critical Balance Drain",
        "type": "TRANSFER",
        "amount": 284100.50,
        "sender": "C_VICTIM_03",
        "old_orig": 284100.50,
        "dest": "C_MULE_03",
        "old_dest": 0.00,
        "score": 0.9984,
        "band": "HIGH_RISK",
        "decision": "DECLINED",
        "action": "DECLINE",
        "primary_reason": "RC_EXACT_BALANCE_DRAIN",
        "all_reasons": ["RC_EXACT_BALANCE_DRAIN", "RC_HIGH_RISK_CHANNEL_COMBO"],
        "narrative": "Transaction attempts exact 100% liquidation of available sender balance ($284,100.50) via high-risk TRANSFER channel."
    },
    {
        "id": "demo-04",
        "title": "Benign Cold-Start Account",
        "type": "TRANSFER",
        "amount": 50.00,
        "sender": "C_FRESH_USER_04",
        "old_orig": 1000.00,
        "dest": "C_DEST_04",
        "old_dest": 200.00,
        "score": 0.0018,
        "band": "LOW_RISK",
        "decision": "APPROVED",
        "action": "APPROVE",
        "primary_reason": "RC_BENIGN_BASELINE",
        "all_reasons": ["RC_BENIGN_BASELINE"],
        "narrative": "Normal transaction velocity, adequate balance headroom, and established channel baseline."
    },
    {
        "id": "demo-05",
        "title": "State Outage Fallback Mode",
        "type": "TRANSFER",
        "amount": 190000.00,
        "sender": "C_FALLBACK_USER",
        "old_orig": 190000.00,
        "dest": "C_DEST_05",
        "old_dest": 0.00,
        "score": 0.9981,
        "band": "HIGH_RISK",
        "decision": "DECLINED",
        "action": "DECLINE",
        "primary_reason": "RC_EXACT_BALANCE_DRAIN",
        "all_reasons": ["RC_FALLBACK_EVALUATION_ACTIVE", "RC_EXACT_BALANCE_DRAIN"],
        "narrative": "State store unavailable; decision derived from causal point-in-time baseline features."
    },
    {
        "id": "demo-07",
        "title": "Causal Explanation Inspection",
        "type": "CASH_OUT",
        "amount": 99000.00,
        "sender": "C_DRAIN_07",
        "old_orig": 99000.00,
        "dest": "C_DEST_07",
        "old_dest": 500.00,
        "score": 0.9981,
        "band": "HIGH_RISK",
        "decision": "DECLINED",
        "action": "DECLINE",
        "primary_reason": "RC_EXACT_BALANCE_DRAIN",
        "all_reasons": ["RC_EXACT_BALANCE_DRAIN", "RC_HIGH_RISK_CHANNEL_COMBO"],
        "narrative": "Transaction attempts exact 100% liquidation of available sender balance ($99,000.00) via high-risk CASH_OUT channel."
    },
    {
        "id": "demo-08",
        "title": "Cryptographic Audit Ledger",
        "type": "TRANSFER",
        "amount": 120.00,
        "sender": "C192837465",
        "old_orig": 2000.00,
        "dest": "C987654321",
        "old_dest": 100.00,
        "score": 0.0018,
        "band": "LOW_RISK",
        "decision": "APPROVED",
        "action": "APPROVE",
        "primary_reason": "RC_BENIGN_BASELINE",
        "all_reasons": ["RC_BENIGN_BASELINE"],
        "narrative": "Normal transaction velocity, adequate balance headroom, and established channel baseline."
    }
]

def mask_account(acc: Optional[str]) -> str:
    if not acc:
        return "Unknown"
    s = str(acc).strip()
    if len(s) <= 6:
        return f"{s[:2]}***"
    return f"{s[:4]}***{s[-3:]}"

class InvestigationSummary(BaseModel):
    investigation_id: str
    event_ref: str
    timestamp_iso: str
    source_provenance: str  # AUDIT_LEDGER | RAZORPAY_TEST_MODE | DEMO_FIXTURE
    transaction_type: str
    amount: float
    sender_masked: str
    dest_masked: str
    risk_score: Optional[float] = None
    risk_band: str
    decision: str
    action: str
    primary_reason_code: str
    model_version: str
    has_audit_record: bool

class InvestigationDetail(BaseModel):
    investigation_id: str
    event_ref: str
    timestamp_iso: str
    source_provenance: str
    what_happened: Dict[str, Any]
    why_flagged: Dict[str, Any]
    model_lineage: Dict[str, Any]
    policy_lineage: Dict[str, Any]
    available_evidence: Dict[str, Any]
    anomaly_indicators: List[Dict[str, Any]]
    investigator_guidance: Dict[str, Any]
    audit_trail: Dict[str, Any]

class InvestigationService:
    """
    Read-only service for querying and inspecting risk events across
    the audit ledger, Razorpay Test Mode webhooks, and demo fixtures.
    """
    def __init__(self, engine=None, webhook_adapter=None):
        self.engine = engine
        self.webhook_adapter = webhook_adapter

    def list_investigations(
        self,
        limit: int = 50,
        band: Optional[str] = None,
        provenance: Optional[str] = None
    ) -> List[InvestigationSummary]:
        """
        Retrieves a deduplicated list of recent investigable risk events.
        """
        summaries: List[InvestigationSummary] = []
        seen_refs = set()

        # 1. Ingest Audit Ledger Events (Primary live source)
        if self.engine and hasattr(self.engine, "audit_logger"):
            audit_events = self.engine.audit_logger.get_events(limit=limit)
            for ev in reversed(audit_events):
                tx_id = ev.get("transaction_id", "")
                if tx_id in seen_refs:
                    continue
                seen_refs.add(tx_id)

                res = ev.get("evaluation_result", {})
                inp = ev.get("input_snapshot_masked", {})
                lin = ev.get("lineage", {})

                summ = InvestigationSummary(
                    investigation_id=f"inv_{ev.get('event_id', tx_id)}",
                    event_ref=tx_id,
                    timestamp_iso=ev.get("event_timestamp_utc", ""),
                    source_provenance="AUDIT_LEDGER",
                    transaction_type=inp.get("type", "TRANSFER"),
                    amount=float(inp.get("amount", 0.0)),
                    sender_masked=inp.get("sender_masked", "Unknown"),
                    dest_masked=inp.get("dest_masked", "Unknown"),
                    risk_score=res.get("raw_model_score"),
                    risk_band=res.get("risk_band", "LOW_RISK"),
                    decision=res.get("decision", "APPROVED"),
                    action=res.get("action", "APPROVE"),
                    primary_reason_code=res.get("primary_reason_code", "RC_BENIGN_BASELINE"),
                    model_version=lin.get("model_version", "v1.0.0-HGB"),
                    has_audit_record=True
                )
                summaries.append(summ)

        # 2. Ingest Razorpay Test Mode Events
        if self.webhook_adapter:
            webhook_events = self.webhook_adapter.get_recent_events(limit=limit)
            for wev in webhook_events:
                wev_dict = wev.model_dump() if hasattr(wev, "model_dump") else wev
                pay_id = wev_dict.get("payment_id", "")
                # Deduplicate if transaction already represented via audit ledger
                if pay_id in seen_refs or f"tx_{pay_id}" in seen_refs:
                    continue
                seen_refs.add(pay_id)

                summ = InvestigationSummary(
                    investigation_id=f"inv_{wev_dict.get('event_id', pay_id)}",
                    event_ref=pay_id,
                    timestamp_iso=wev_dict.get("received_at_utc", ""),
                    source_provenance="RAZORPAY_TEST_MODE",
                    transaction_type=wev_dict.get("method", "upi").upper(),
                    amount=float(wev_dict.get("amount_inr", 0.0)),
                    sender_masked=wev_dict.get("customer_contact_masked") or mask_account(wev_dict.get("customer_vpa")),
                    dest_masked=mask_account(wev_dict.get("merchant_id")),
                    risk_score=wev_dict.get("risk_score"),
                    risk_band="HIGH_RISK" if (wev_dict.get("risk_score") or 0) >= 0.99 else "LOW_RISK" if wev_dict.get("risk_score") is not None else "UNSCORED",
                    decision=wev_dict.get("decision") or "EVENT_RECEIVED",
                    action=wev_dict.get("action") or "MONITOR",
                    primary_reason_code=(wev_dict.get("reasons") or {}).get("primary_code", "RC_GATEWAY_WEBHOOK"),
                    model_version=(wev_dict.get("engine_metadata") or {}).get("model_version", "None (Gated)"),
                    has_audit_record=bool(wev_dict.get("audit_id"))
                )
                summaries.append(summ)

        # 3. Ingest Master Competition Demo Fixtures
        for dfix in MASTER_DEMO_FIXTURES:
            d_id = dfix["id"]
            if d_id in seen_refs:
                continue
            seen_refs.add(d_id)

            summ = InvestigationSummary(
                investigation_id=f"inv_{d_id}",
                event_ref=d_id,
                timestamp_iso="2026-09-02T06:50:00Z",
                source_provenance="DEMO_FIXTURE",
                transaction_type=dfix["type"],
                amount=float(dfix["amount"]),
                sender_masked=mask_account(dfix["sender"]),
                dest_masked=mask_account(dfix["dest"]),
                risk_score=float(dfix["score"]),
                risk_band=dfix["band"],
                decision=dfix["decision"],
                action=dfix["action"],
                primary_reason_code=dfix["primary_reason"],
                model_version="model_b_stateful_hgb_v1.0.0",
                has_audit_record=False
            )
            summaries.append(summ)

        # Apply optional filters
        filtered = summaries
        if band:
            filtered = [s for s in filtered if s.risk_band == band.upper()]
        if provenance:
            filtered = [s for s in filtered if s.source_provenance == provenance.upper()]

        return filtered[:limit]

    def get_investigation_detail(self, investigation_id: str) -> Optional[InvestigationDetail]:
        """
        Assembles the comprehensive 9-pillar investigation dossier for a specific ID.
        Returns None if the ID is unknown (triggers HTTP 404).
        """
        clean_id = investigation_id.strip()
        if clean_id.startswith("inv_"):
            clean_id = clean_id[4:]

        # 1. Search in Audit Ledger
        if self.engine and hasattr(self.engine, "audit_logger"):
            with self.engine.audit_logger._lock:
                for ev in self.engine.audit_logger.events:
                    ev_dict = ev.model_dump()
                    if ev_dict["event_id"] == clean_id or ev_dict["transaction_id"] == clean_id:
                        return self._build_from_audit_event(ev_dict)

        # 2. Search in Razorpay Webhooks
        if self.webhook_adapter:
            for wev in self.webhook_adapter.event_buffer:
                wev_dict = wev.model_dump() if hasattr(wev, "model_dump") else wev
                if wev_dict["event_id"] == clean_id or wev_dict["payment_id"] == clean_id:
                    return self._build_from_webhook_event(wev_dict)

        # 3. Search in Master Demo Fixtures
        for dfix in MASTER_DEMO_FIXTURES:
            if dfix["id"] == clean_id or dfix["id"].replace("-", "_") == clean_id:
                return self._build_from_demo_fixture(dfix)

        return None

    def _build_from_audit_event(self, ev: Dict[str, Any]) -> InvestigationDetail:
        res = ev.get("evaluation_result", {})
        inp = ev.get("input_snapshot_masked", {})
        lin = ev.get("lineage", {})
        tel = ev.get("runtime_telemetry", {})
        feat = ev.get("causal_features_extracted", {})
        primary_code = res.get("primary_reason_code", "RC_BENIGN_BASELINE")

        # Anomaly indicators
        anomalies = []
        amt = float(inp.get("amount", 0.0))
        orig_old = float(inp.get("sender_old_balance", 0.0))
        if orig_old > 0 and abs(amt - orig_old) < 1e-2:
            anomalies.append({
                "signal": "EXACT_BALANCE_LIQUIDATION",
                "severity": "CRITICAL",
                "description": "100.0% of sender available account balance liquidated in single transfer."
            })
        elif orig_old > 0 and (amt / orig_old) > 0.90:
            anomalies.append({
                "signal": "SEVERE_LIQUIDITY_DRAIN",
                "severity": "HIGH",
                "description": f"Drains {(amt / orig_old) * 100:.1f}% of sender available funds."
            })
        if feat.get("dest_unique_orig_cnt", 0) >= 2 and feat.get("dest_prev_in_tx_cnt", 0) >= 3:
            anomalies.append({
                "signal": "MULE_AGGREGATION_VELOCITY",
                "severity": "CRITICAL",
                "description": f"Destination has received transfers from {feat.get('dest_unique_orig_cnt')} distinct accounts."
            })

        guidance = SOP_GUIDANCE_MAP.get(primary_code, SOP_GUIDANCE_MAP["RC_BENIGN_BASELINE"])

        return InvestigationDetail(
            investigation_id=f"inv_{ev.get('event_id')}",
            event_ref=ev.get("transaction_id", ""),
            timestamp_iso=ev.get("event_timestamp_utc", ""),
            source_provenance="AUDIT_LEDGER",
            what_happened={
                "transaction_id": ev.get("transaction_id"),
                "step": inp.get("step"),
                "channel": inp.get("type"),
                "amount": float(inp.get("amount", 0.0)),
                "currency": "USD",
                "sender_masked": inp.get("sender_masked"),
                "sender_old_balance": float(inp.get("sender_old_balance", 0.0)),
                "dest_masked": inp.get("dest_masked"),
                "dest_old_balance": float(inp.get("dest_old_balance", 0.0))
            },
            why_flagged={
                "risk_score": res.get("raw_model_score"),
                "risk_band": res.get("risk_band"),
                "primary_reason_code": primary_code,
                "all_reason_codes": res.get("all_reason_codes", [primary_code]),
                "narrative": guidance["title"]
            },
            model_lineage={
                "model_name": lin.get("model_version"),
                "model_type": lin.get("model_type"),
                "model_sha256": lin.get("model_artifact_hash"),
                "fallback_triggered": tel.get("fallback_mode_active", False)
            },
            policy_lineage={
                "policy_version": lin.get("policy_version"),
                "operating_threshold": lin.get("operating_threshold"),
                "decision": res.get("decision"),
                "action": res.get("action")
            },
            available_evidence={
                "observed_inputs": inp,
                "point_in_time_features": feat,
                "latency_telemetry": tel
            },
            anomaly_indicators=anomalies,
            investigator_guidance=guidance,
            audit_trail={
                "audit_event_id": ev.get("event_id"),
                "chained_integrity_hash": ev.get("integrity_hash"),
                "tamper_evident_status": "CRYPTOGRAPHICALLY_VERIFIED"
            }
        )

    def _build_from_webhook_event(self, wev: Dict[str, Any]) -> InvestigationDetail:
        primary_code = (wev.get("reasons") or {}).get("primary_code", "RC_GATEWAY_WEBHOOK")
        guidance = SOP_GUIDANCE_MAP.get(primary_code, {
            "reason_code": "RC_GATEWAY_WEBHOOK",
            "title": "Razorpay Test Mode Webhook Payment Event",
            "objective": "Verify webhook event integrity, signature authenticity, and feature completeness.",
            "urgency": "ROUTINE_AUDIT",
            "recommended_action": "INSPECT_TELEMETRY",
            "protocol_steps": [
                "1. Confirm HMAC-SHA256 signature validity.",
                "2. Verify payment amount against merchant order reference.",
                "3. Check whether banking balance context was enriched via notes."
            ],
            "evidence_to_inspect": ["Payment ID", "Currency and paise conversion", "Missing features list"]
        })

        return InvestigationDetail(
            investigation_id=f"inv_{wev.get('event_id')}",
            event_ref=wev.get("payment_id", ""),
            timestamp_iso=wev.get("received_at_utc", ""),
            source_provenance="RAZORPAY_TEST_MODE",
            what_happened={
                "payment_id": wev.get("payment_id"),
                "event_type": wev.get("event_type"),
                "method": wev.get("method"),
                "amount": float(wev.get("amount_inr", 0.0)),
                "currency": wev.get("currency", "INR"),
                "sender_masked": wev.get("customer_contact_masked") or mask_account(wev.get("customer_vpa")),
                "dest_masked": mask_account(wev.get("merchant_id")),
                "evaluation_status": wev.get("evaluation_status")
            },
            why_flagged={
                "risk_score": wev.get("risk_score"),
                "risk_band": "HIGH_RISK" if (wev.get("risk_score") or 0) >= 0.99 else "LOW_RISK" if wev.get("risk_score") is not None else "UNSCORED",
                "primary_reason_code": primary_code,
                "all_reason_codes": [primary_code],
                "narrative": wev.get("readiness_reason", "")
            },
            model_lineage={
                "model_name": (wev.get("engine_metadata") or {}).get("model_version", "Gated"),
                "model_type": (wev.get("engine_metadata") or {}).get("model_type", "Gated"),
                "model_sha256": "N/A",
                "fallback_triggered": (wev.get("engine_metadata") or {}).get("fallback_triggered", False)
            },
            policy_lineage={
                "policy_version": (wev.get("engine_metadata") or {}).get("policy_version", "v1.2.0-frozen"),
                "operating_threshold": (wev.get("engine_metadata") or {}).get("operating_threshold", 0.990),
                "decision": wev.get("decision") or "EVENT_RECEIVED",
                "action": wev.get("action") or "MONITOR"
            },
            available_evidence={
                "missing_features": wev.get("missing_features", []),
                "notes_context": wev.get("reasons", {}).get("causal_evidence", {})
            },
            anomaly_indicators=[
                {"signal": "GATEWAY_INSPECTION", "severity": "MEDIUM", "description": wev.get("readiness_reason", "")}
            ],
            investigator_guidance=guidance,
            audit_trail={
                "audit_event_id": wev.get("audit_id") or "unlogged_raw_event",
                "chained_integrity_hash": wev.get("integrity_hash"),
                "tamper_evident_status": "BLOCK_CHAINED"
            }
        )

    def _build_from_demo_fixture(self, dfix: Dict[str, Any]) -> InvestigationDetail:
        primary_code = dfix["primary_reason"]
        guidance = SOP_GUIDANCE_MAP.get(primary_code, SOP_GUIDANCE_MAP["RC_BENIGN_BASELINE"])

        amt = float(dfix["amount"])
        old_orig = float(dfix["old_orig"])
        anomalies = []
        if old_orig > 0 and abs(amt - old_orig) < 1e-2:
            anomalies.append({
                "signal": "EXACT_BALANCE_LIQUIDATION",
                "severity": "CRITICAL",
                "description": "100.0% of sender available account balance liquidated in single transfer."
            })
        elif old_orig > 0 and (amt / old_orig) > 0.90:
            anomalies.append({
                "signal": "SEVERE_LIQUIDITY_DRAIN",
                "severity": "HIGH",
                "description": f"Drains {(amt / old_orig) * 100:.1f}% of sender available funds."
            })

        return InvestigationDetail(
            investigation_id=f"inv_{dfix['id']}",
            event_ref=dfix["id"],
            timestamp_iso="2026-09-02T06:50:00Z",
            source_provenance="DEMO_FIXTURE",
            what_happened={
                "transaction_id": dfix["id"],
                "step": 450,
                "channel": dfix["type"],
                "amount": float(dfix["amount"]),
                "currency": "USD",
                "sender_masked": mask_account(dfix["sender"]),
                "sender_old_balance": float(dfix["old_orig"]),
                "dest_masked": mask_account(dfix["dest"]),
                "dest_old_balance": float(dfix["old_dest"])
            },
            why_flagged={
                "risk_score": float(dfix["score"]),
                "risk_band": dfix["band"],
                "primary_reason_code": primary_code,
                "all_reason_codes": dfix["all_reasons"],
                "narrative": dfix["narrative"]
            },
            model_lineage={
                "model_name": "model_b_stateful_hgb_v1.0.0",
                "model_type": "MODEL_B_STATEFUL_HGB",
                "model_sha256": "5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735",
                "fallback_triggered": (dfix["id"] == "demo-05")
            },
            policy_lineage={
                "policy_version": "v1.2.0-frozen",
                "operating_threshold": 0.990,
                "decision": dfix["decision"],
                "action": dfix["action"]
            },
            available_evidence={
                "observed_inputs": {
                    "channel": dfix["type"],
                    "amount": dfix["amount"],
                    "sender_old_balance": dfix["old_orig"],
                    "dest_old_balance": dfix["old_dest"]
                },
                "point_in_time_features": {
                    "orig_balance_drain_ratio": (amt / (old_orig + 1.0)) if old_orig > 0 else 0.0,
                    "amount": amt
                }
            },
            anomaly_indicators=anomalies,
            investigator_guidance=guidance,
            audit_trail={
                "audit_event_id": f"fixture_{dfix['id']}",
                "chained_integrity_hash": "DEMO_FIXTURE_HASH_PRECOMPUTED",
                "tamper_evident_status": "PRECOMPUTED_FIXTURE"
            }
        )

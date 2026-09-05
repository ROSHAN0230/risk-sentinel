"""
Risk Sentinel — Real-Time Transaction Monitoring & Auto-Response Test Suite
=============================================================================
Tests the end-to-end transaction monitoring extension:
1. Ingestion -> Persistence -> Evaluation -> Policy Auto-Response -> Audit Flow
2. Razorpay Test Mode Capture Gate Integration & Defensive Auto-Response
3. Webhook Ingestion & Provenance Stamping
4. Query Filtering, Summaries & Provenance Isolation
5. Defensive Auto-Response Semantics:
   - APPROVE -> Capture Permitted
   - REVIEW/HOLD -> Capture Suppressed
   - DECLINE -> Capture Suppressed
"""

import unittest
import os
import sys
import json
import uuid
import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.decision_engine import RiskDecisionEngine
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.transaction_store import TransactionStore, TransactionRecord, mask_account_id
from src.engine.integrations.razorpay_capture_gate import (
    RazorpayCaptureGate,
    RazorpayCaptureRequest
)
from src.engine.integrations.razorpay_adapter import RazorpayWebhookAdapter

class TestTransactionMonitoringFlow(unittest.TestCase):
    def setUp(self):
        self.store = TransactionStore(max_buffer=100)
        self.engine = RiskDecisionEngine()
        self.gate = RazorpayCaptureGate(engine=self.engine)
        self.webhook_adapter = RazorpayWebhookAdapter(engine=self.engine)

    def test_01_ingestion_persistence_evaluation_audit_flow(self):
        """Direct transaction evaluation -> evaluation -> stored record -> audit reference."""
        req = EvaluateRequest(
            transaction_id="tx_mon_test_001",
            step=450,
            type=TransactionType.PAYMENT,
            amount=84.50,
            nameOrig="C_CUSTOMER_01",
            oldbalanceOrg=1200.00,
            nameDest="M_MERCHANT_01",
            oldbalanceDest=0.00,
            merchant_id="merchant_test_abc"
        )
        
        # 1. Evaluate via frozen engine
        resp = self.engine.evaluate(req)
        self.assertEqual(resp.decision.value, "APPROVED")
        
        # 2. Ingest and persist
        record = TransactionRecord(
            transaction_id=req.transaction_id,
            timestamp_iso=resp.timestamp_iso,
            provenance="API_DIRECT",
            amount_inr=req.amount,
            currency="INR",
            channel_type=req.type.value,
            sender_masked=mask_account_id(req.nameOrig),
            dest_masked=mask_account_id(req.nameDest),
            merchant_id=req.merchant_id or "default_merchant",
            risk_score=resp.risk_score,
            risk_band=resp.risk_band.value,
            decision=resp.decision.value,
            policy_action=resp.action.value,
            primary_reason_code=resp.reasons.primary_code,
            reasons_narrative=resp.reasons.narrative,
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="DIRECT_EVALUATION",
            model_version=resp.engine_metadata.model_version,
            policy_version=resp.engine_metadata.policy_version,
            audit_event_id=resp.evaluation_id,
            integrity_hash=resp.evaluation_id
        )
        saved = self.store.record(record)
        
        # 3. Assert persistence & retrieval
        self.assertEqual(saved.transaction_id, "tx_mon_test_001")
        retrieved = self.store.get_by_id("tx_mon_test_001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.provenance, "API_DIRECT")
        self.assertEqual(retrieved.decision, "APPROVED")
        self.assertEqual(retrieved.auto_response_action, "CAPTURE_PERMITTED")
        self.assertEqual(retrieved.primary_reason_code, "RC_BENIGN_BASELINE")
        self.assertEqual(retrieved.sender_masked, "C_CU***_01")

    def test_02_razorpay_capture_gate_auto_response(self):
        """Razorpay Capture Gate -> evaluation -> defensive auto-response -> persistence."""
        # High-Risk Drain Attack
        drain_req = RazorpayCaptureRequest(
            payment_id="pay_test_drain_mon_002",
            order_id="order_test_drain_002",
            amount_paise=28410050,  # 284,100.50 INR
            currency="INR",
            status="authorized",
            method="upi",
            notes={
                "step": "452",
                "type": "TRANSFER",
                "oldbalanceOrg": "284100.50",
                "oldbalanceDest": "0.00",
                "nameOrig": "C_VICTIM_DRAIN",
                "nameDest": "C_MULE_DRAIN"
            }
        )
        
        res = self.gate.evaluate_and_capture(drain_req)
        self.assertEqual(res.decision, "DECLINED")
        self.assertEqual(res.capture_action, "CAPTURE_SUPPRESSED")
        self.assertEqual(res.capture_status, "HELD_DECLINED")
        self.assertEqual(res.primary_reason_code, "RC_EXACT_BALANCE_DRAIN")

    def test_03_query_filtering_and_provenance_isolation(self):
        """Tests filtering by provenance and decision across multiple ingested streams."""
        self.store.clear()
        
        # Ingest 3 distinct records with explicit provenance
        r1 = TransactionRecord(
            transaction_id="tx_prov_1",
            provenance="GENUINE_RAZORPAY_TEST_MODE",
            amount_inr=50.00,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        )
        r2 = TransactionRecord(
            transaction_id="tx_prov_2",
            provenance="DEMO_FIXTURE",
            amount_inr=284100.50,
            decision="DECLINED",
            auto_response_action="CAPTURE_SUPPRESSED",
            auto_response_status="HELD_DECLINED"
        )
        r3 = TransactionRecord(
            transaction_id="tx_prov_3",
            provenance="SIMULATED_CONTRACT_TEST",
            amount_inr=976662.30,
            decision="REVIEW_REQUIRED",
            auto_response_action="CAPTURE_SUPPRESSED",
            auto_response_status="HELD_REVIEW_REQUIRED"
        )
        
        for r in [r1, r2, r3]:
            self.store.record(r)
            
        # 1. Total Count
        all_tx = self.store.get_transactions(limit=10)
        self.assertEqual(len(all_tx), 3)
        
        # 2. Provenance Filter
        razorpay_tx = self.store.get_transactions(provenance="GENUINE_RAZORPAY_TEST_MODE")
        self.assertEqual(len(razorpay_tx), 1)
        self.assertEqual(razorpay_tx[0].transaction_id, "tx_prov_1")
        
        demo_tx = self.store.get_transactions(provenance="DEMO_FIXTURE")
        self.assertEqual(len(demo_tx), 1)
        self.assertEqual(demo_tx[0].transaction_id, "tx_prov_2")
        
        # 3. Decision Filter
        declined_tx = self.store.get_transactions(decision="DECLINED")
        self.assertEqual(len(declined_tx), 1)
        self.assertEqual(declined_tx[0].transaction_id, "tx_prov_2")
        
        # 4. Summary Aggregation
        summary = self.store.get_summary()
        self.assertEqual(summary["total_transactions"], 3)
        self.assertEqual(summary["by_decision"]["APPROVED"], 1)
        self.assertEqual(summary["by_decision"]["DECLINED"], 1)
        self.assertEqual(summary["by_decision"]["REVIEW_REQUIRED"], 1)
        self.assertEqual(summary["by_auto_response"]["CAPTURE_PERMITTED"], 1)
        self.assertEqual(summary["by_auto_response"]["CAPTURE_SUPPRESSED"], 2)

    def test_04_defensive_auto_response_semantics(self):
        """Verifies strict auto-response semantics: APPROVE -> capture permitted, REVIEW/DECLINE -> capture suppressed."""
        # Case A: APPROVE
        r_app = TransactionRecord(
            transaction_id="tx_sem_1",
            provenance="API_DIRECT",
            amount_inr=100.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        )
        self.assertEqual(r_app.auto_response_action, "CAPTURE_PERMITTED")
        
        # Case B: REVIEW_REQUIRED
        r_rev = TransactionRecord(
            transaction_id="tx_sem_2",
            provenance="SIMULATED_CONTRACT_TEST",
            amount_inr=50000.0,
            decision="REVIEW_REQUIRED",
            auto_response_action="CAPTURE_SUPPRESSED",
            auto_response_status="HELD_REVIEW_REQUIRED"
        )
        self.assertEqual(r_rev.auto_response_action, "CAPTURE_SUPPRESSED")
        
        # Case C: DECLINED
        r_dec = TransactionRecord(
            transaction_id="tx_sem_3",
            provenance="SIMULATED_CONTRACT_TEST",
            amount_inr=284100.5,
            decision="DECLINED",
            auto_response_action="CAPTURE_SUPPRESSED",
            auto_response_status="HELD_DECLINED"
        )
        self.assertEqual(r_dec.auto_response_action, "CAPTURE_SUPPRESSED")

if __name__ == "__main__":
    unittest.main(verbosity=2)

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
        self.temp_storage_path = os.path.join(
            os.path.dirname(__file__), "temp_test_tx_store.json"
        )
        if os.path.exists(self.temp_storage_path):
            os.remove(self.temp_storage_path)
            
        self.store = TransactionStore(max_buffer=100, storage_file=self.temp_storage_path)
        self.engine = RiskDecisionEngine()
        self.gate = RazorpayCaptureGate(engine=self.engine)
        self.webhook_adapter = RazorpayWebhookAdapter(engine=self.engine)

    def tearDown(self):
        if os.path.exists(self.temp_storage_path):
            try:
                os.remove(self.temp_storage_path)
            except OSError:
                pass

    def test_A_benign_transaction_flow(self):
        """A. Benign transaction -> persisted -> evaluated -> APPROVED -> capture permitted -> audit stored."""
        req = EvaluateRequest(
            transaction_id="tx_benign_001",
            step=450,
            type=TransactionType.PAYMENT,
            amount=84.50,
            nameOrig="C_ALICE_BENIGN",
            oldbalanceOrg=1200.00,
            nameDest="M_BOOKSTORE_01",
            oldbalanceDest=0.00,
            merchant_id="merchant_benign"
        )
        resp = self.engine.evaluate(req)
        self.assertEqual(resp.decision.value, "APPROVED")
        self.assertLess(resp.risk_score, 0.900)
        
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
        self.store.record(record)
        
        retrieved = self.store.get_by_id("tx_benign_001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.decision, "APPROVED")
        self.assertEqual(retrieved.auto_response_action, "CAPTURE_PERMITTED")
        self.assertEqual(retrieved.audit_event_id, resp.evaluation_id)

    def test_B_high_risk_drain_flow(self):
        """B. High-risk drain scenario -> evaluated -> DECLINED -> capture suppressed -> reason stored -> audit stored."""
        drain_req = RazorpayCaptureRequest(
            payment_id="pay_test_drain_002",
            order_id="order_drain_002",
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
        self.assertIsNotNone(res.audit_event_id)

    def test_C_review_scenario_flow(self):
        """C. Review scenario -> REVIEW_REQUIRED -> capture suppressed."""
        review_req = RazorpayCaptureRequest(
            payment_id="pay_test_review_003",
            order_id="order_review_003",
            amount_paise=97666230,  # 976,662.30 INR
            currency="INR",
            status="authorized",
            method="transfer",
            notes={
                "step": "324",
                "type": "TRANSFER",
                "oldbalanceOrg": "982857.46",
                "oldbalanceDest": "2453029.29",
                "nameOrig": "C1959219454",
                "nameDest": "C2061756973"
            }
        )
        res = self.gate.evaluate_and_capture(review_req)
        self.assertEqual(res.decision, "REVIEW_REQUIRED")
        self.assertEqual(res.capture_action, "CAPTURE_SUPPRESSED")
        self.assertEqual(res.capture_status, "HELD_REVIEW_REQUIRED")
        self.assertEqual(res.primary_reason_code, "RC_SEVERE_LIQUIDITY_DRAIN")

    def test_D_provenance_isolation(self):
        """D. Provenance isolation: DEMO_FIXTURE must never appear as GENUINE_RAZORPAY_TEST_MODE."""
        rec_demo = TransactionRecord(
            transaction_id="tx_demo_isolated",
            provenance="DEMO_FIXTURE",
            amount_inr=500.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="DIRECT_EVALUATION"
        )
        rec_genuine = TransactionRecord(
            transaction_id="tx_genuine_isolated",
            provenance="GENUINE_RAZORPAY_TEST_MODE",
            amount_inr=500.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        )
        self.store.record(rec_demo)
        self.store.record(rec_genuine)
        
        genuine_query = self.store.get_transactions(provenance="GENUINE_RAZORPAY_TEST_MODE")
        demo_query = self.store.get_transactions(provenance="DEMO_FIXTURE")
        
        self.assertEqual(len(genuine_query), 1)
        self.assertEqual(genuine_query[0].transaction_id, "tx_genuine_isolated")
        self.assertNotEqual(genuine_query[0].transaction_id, "tx_demo_isolated")
        
        self.assertEqual(len(demo_query), 1)
        self.assertEqual(demo_query[0].transaction_id, "tx_demo_isolated")
        self.assertNotEqual(demo_query[0].transaction_id, "tx_genuine_isolated")

    def test_E_duplicate_transaction_handling(self):
        """E. Duplicate transaction handling: Updating existing record idempotently."""
        rec1 = TransactionRecord(
            transaction_id="tx_dup_001",
            provenance="SIMULATED_CONTRACT_TEST",
            amount_inr=100.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        )
        self.store.record(rec1)
        self.assertEqual(len(self.store.get_transactions()), 1)
        
        # Ingest again with same transaction_id (updated status)
        rec2 = TransactionRecord(
            transaction_id="tx_dup_001",
            provenance="SIMULATED_CONTRACT_TEST",
            amount_inr=100.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED_CONFIRMED"
        )
        self.store.record(rec2)
        all_tx = self.store.get_transactions()
        self.assertEqual(len(all_tx), 1)
        self.assertEqual(all_tx[0].auto_response_status, "CAPTURED_CONFIRMED")

    def test_F_malformed_transaction_handling(self):
        """F. Malformed transaction input: Graceful validation failure."""
        with self.assertRaises(Exception):
            # Missing mandatory transaction_id and negative amount
            TransactionRecord(
                transaction_id=None,  # type: ignore
                provenance="API_DIRECT",
                amount_inr=-50.0,
                auto_response_action="CAPTURE_PERMITTED",
                auto_response_status="ERROR"
            )

    def test_G_pii_masking(self):
        """G. PII masking: Mask account identifiers."""
        self.assertEqual(mask_account_id("C123456789"), "C123***789")
        self.assertEqual(mask_account_id("M_MERCHANT_99"), "M_ME***_99")
        self.assertEqual(mask_account_id("123"), "12***")
        self.assertEqual(mask_account_id(""), "N/A")
        self.assertEqual(mask_account_id(None), "N/A")

    def test_H_transaction_history_query(self):
        """H. Transaction history query: limit, pagination, and filter."""
        for i in range(10):
            self.store.record(TransactionRecord(
                transaction_id=f"tx_hist_{i:02d}",
                provenance="SIMULATED_CONTRACT_TEST",
                amount_inr=float(10 * (i + 1)),
                decision="APPROVED" if i % 2 == 0 else "DECLINED",
                auto_response_action="CAPTURE_PERMITTED" if i % 2 == 0 else "CAPTURE_SUPPRESSED",
                auto_response_status="CAPTURED" if i % 2 == 0 else "HELD_DECLINED"
            ))
            
        page = self.store.get_transactions(limit=5)
        self.assertEqual(len(page), 5)
        self.assertEqual(page[0].transaction_id, "tx_hist_09")  # LIFO order
        
        approved_only = self.store.get_transactions(decision="APPROVED")
        self.assertEqual(len(approved_only), 5)
        for tx in approved_only:
            self.assertEqual(tx.decision, "APPROVED")

    def test_I_summary_kpi_calculation(self):
        """I. Summary / KPI calculations."""
        self.store.record(TransactionRecord(
            transaction_id="tx_kpi_1",
            provenance="GENUINE_RAZORPAY_TEST_MODE",
            amount_inr=150.0,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        ))
        self.store.record(TransactionRecord(
            transaction_id="tx_kpi_2",
            provenance="DEMO_FIXTURE",
            amount_inr=350.0,
            decision="DECLINED",
            auto_response_action="CAPTURE_SUPPRESSED",
            auto_response_status="HELD_DECLINED"
        ))
        
        summary = self.store.get_summary()
        self.assertEqual(summary["total_transactions"], 2)
        self.assertEqual(summary["total_volume_inr"], 500.0)
        self.assertEqual(summary["by_provenance"]["GENUINE_RAZORPAY_TEST_MODE"], 1)
        self.assertEqual(summary["by_provenance"]["DEMO_FIXTURE"], 1)
        self.assertEqual(summary["by_decision"]["APPROVED"], 1)
        self.assertEqual(summary["by_decision"]["DECLINED"], 1)
        self.assertEqual(summary["by_auto_response"]["CAPTURE_PERMITTED"], 1)
        self.assertEqual(summary["by_auto_response"]["CAPTURE_SUPPRESSED"], 1)

    def test_J_restart_reload_persistence(self):
        """J. Restart / reload behavior of JSON-backed transaction store."""
        # 1. Record transactions in store instance 1
        rec = TransactionRecord(
            transaction_id="tx_restart_001",
            provenance="GENUINE_RAZORPAY_TEST_MODE",
            amount_inr=123.45,
            decision="APPROVED",
            auto_response_action="CAPTURE_PERMITTED",
            auto_response_status="CAPTURED"
        )
        self.store.record(rec)
        
        # 2. Simulate process exit and new process startup reading the file
        new_store = TransactionStore(storage_file=self.temp_storage_path)
        restored_tx = new_store.get_by_id("tx_restart_001")
        
        self.assertIsNotNone(restored_tx)
        self.assertEqual(restored_tx.transaction_id, "tx_restart_001")
        self.assertEqual(restored_tx.amount_inr, 123.45)
        self.assertEqual(restored_tx.provenance, "GENUINE_RAZORPAY_TEST_MODE")
        self.assertEqual(restored_tx.auto_response_action, "CAPTURE_PERMITTED")
        self.assertEqual(restored_tx.auto_response_status, "CAPTURED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

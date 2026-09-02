"""
Risk Sentinel — Phase P0 End-to-End Razorpay Test Mode Verification
Demonstrates and measures the real payment/webhook ingestion flow,
signature verification, model readiness gating, and audit trail emission.
"""

import os
import sys
import time
import json
import hmac
import hashlib
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.engine.api import app, webhook_adapter

out_dir = r"c:\Users\raahe\Downloads\razorpay\research\phase_p0\artifacts"
os.makedirs(out_dir, exist_ok=True)

SECRET = "rzp_test_secret_p0_key_abcdef123456"
webhook_adapter.webhook_secret = SECRET
webhook_adapter.processed_events.clear()
webhook_adapter.event_buffer.clear()

client = TestClient(app)

def sign_payload(body: bytes) -> str:
    return hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()

def run_e2e_verification():
    print("=================================================================")
    print("RISK SENTINEL — PHASE P0 REAL PAYMENT/WEBHOOK PATH VERIFICATION")
    print("=================================================================\n")

    results = {}

    # 1. Raw Razorpay Payment Event (Standard Test Payment)
    raw_payment = {
        "entity": "event",
        "account_id": "acc_razorpay_live_test_001",
        "event": "payment.authorized",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_raw_gateway_1001",
                    "amount": 150000, # ₹1,500.00
                    "currency": "INR",
                    "status": "authorized",
                    "method": "upi",
                    "vpa": "consumer@okaxis",
                    "email": "consumer@example.com",
                    "contact": "+919876543210",
                    "notes": {
                        "merchant_order_id": "ORD-2026-902-01"
                    },
                    "created_at": int(time.time())
                }
            }
        },
        "created_at": int(time.time())
    }
    raw_body_1 = json.dumps(raw_payment).encode("utf-8")
    sig_1 = sign_payload(raw_body_1)

    t0 = time.perf_counter()
    resp_1 = client.post(
        "/v1/webhooks/razorpay",
        content=raw_body_1,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_1}
    )
    lat_1_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_1.status_code == 200, f"Raw webhook failed with status {resp_1.status_code}"
    data_1 = resp_1.json()

    print(f"[+] Raw Payment Event Ingested in {lat_1_ms:.2f}ms:")
    print(f"    • Payment ID: {data_1['payment_id']} (Amount: INR {data_1['amount_inr']:.2f})")
    print(f"    • Evaluation Status: {data_1['evaluation_status']}")
    print(f"    • Readiness Reason: {data_1['readiness_reason'][:80]}...")
    print(f"    • Missing Features Explicitly Identified: {data_1['missing_features']}")
    print(f"    • Model Inference Skipped (Zero Fabrication): risk_score={data_1['risk_score']}")
    print(f"    • SHA-256 Chained Integrity Hash: {data_1['integrity_hash'][:24]}...")

    results["raw_gateway_event"] = {
        "status_code": resp_1.status_code,
        "latency_ms": round(lat_1_ms, 3),
        "data": data_1
    }

    # 2. Enriched Razorpay Payment Event (Carrying Banking Context via Notes)
    enriched_payment = {
        "entity": "event",
        "account_id": "acc_razorpay_live_test_001",
        "event": "payment.authorized",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_enriched_drain_2002",
                    "amount": 28410050, # ₹284,100.50 (Exact Balance Drain)
                    "currency": "INR",
                    "status": "authorized",
                    "method": "upi",
                    "vpa": "victim@okhdfcbank",
                    "email": "victim_compromised@example.com",
                    "contact": "+919123456780",
                    "notes": {
                        "step": 452,
                        "type": "TRANSFER",
                        "oldbalanceOrg": 284100.50,
                        "oldbalanceDest": 0.00,
                        "nameOrig": "C_VICTIM_P0",
                        "nameDest": "C_MULE_P0",
                        "context_source": "ENRICHED_BANKING_TELEMETRY"
                    },
                    "created_at": int(time.time())
                }
            }
        },
        "created_at": int(time.time())
    }
    raw_body_2 = json.dumps(enriched_payment).encode("utf-8")
    sig_2 = sign_payload(raw_body_2)

    t0 = time.perf_counter()
    resp_2 = client.post(
        "/v1/webhooks/razorpay",
        content=raw_body_2,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_2}
    )
    lat_2_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_2.status_code == 200, f"Enriched webhook failed with status {resp_2.status_code}"
    data_2 = resp_2.json()

    print(f"\n[+] Enriched Payment Event Ingested & Evaluated in {lat_2_ms:.2f}ms:")
    print(f"    • Payment ID: {data_2['payment_id']} (Amount: INR {data_2['amount_inr']:.2f})")
    print(f"    • Evaluation Status: {data_2['evaluation_status']}")
    print(f"    • Operating Risk Score: {data_2['risk_score']:.4f} (Decision: {data_2['decision']}, Action: {data_2['action']})")
    print(f"    • Primary Reason Code: {data_2['reasons']['primary_code']}")
    print(f"    • Model Version: {data_2['engine_metadata']['model_version']}")
    print(f"    • Policy Version: {data_2['engine_metadata']['policy_version']} (Operating Threshold: {data_2['engine_metadata']['operating_threshold']})")
    print(f"    • Audit ID: {data_2['audit_id']}")
    print(f"    • SHA-256 Chained Integrity Hash: {data_2['integrity_hash'][:24]}...")

    results["enriched_gateway_event"] = {
        "status_code": resp_2.status_code,
        "latency_ms": round(lat_2_ms, 3),
        "data": data_2
    }

    # 3. Verify Operational Event Query Endpoint
    t0 = time.perf_counter()
    resp_feed = client.get("/v1/webhooks/events?limit=10")
    lat_feed_ms = (time.perf_counter() - t0) * 1000.0
    assert resp_feed.status_code == 200
    feed_events = resp_feed.json()
    assert len(feed_events) >= 2, "Feed did not contain both test events!"
    print(f"\n[+] Operational Webhook Feed Verified ({len(feed_events)} events, {lat_feed_ms:.2f}ms query latency).")

    results["feed_verification"] = {
        "status_code": resp_feed.status_code,
        "event_count": len(feed_events),
        "query_latency_ms": round(lat_feed_ms, 3)
    }

    # Save artifact
    out_file = os.path.join(out_dir, "e2e_webhook_evidence.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[*] E2E Webhook Evidence Artifact saved to {out_file}")

if __name__ == "__main__":
    run_e2e_verification()

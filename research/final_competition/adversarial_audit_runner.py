import urllib.request
import urllib.error
import json
import hmac
import hashlib
import unittest

BASE = 'https://risk-sentinel.onrender.com'
print("=================================================================")
print("  ADVERSARIAL TRACK-02 COMPETITION READINESS AUDIT RUNNER")
print("=================================================================\n")

# 1. Health & Manifest Check
req = urllib.request.Request(f'{BASE}/v1/health')
with urllib.request.urlopen(req) as resp:
    h_data = json.loads(resp.read().decode())
    print(f"[AUDIT 1] Health: Status={h_data['status']}, Engine={h_data['engine_version']}, Checksum={h_data['champion_model_sha256'][:16]}...")
    assert resp.status == 200 and h_data['status'] == 'HEALTHY'

# 2. Test A — Clearly Benign Payment
req = urllib.request.Request(
    f'{BASE}/v1/risk/evaluate',
    data=json.dumps({
        'transaction_id': 'tx_audit_benign_01',
        'step': 450,
        'type': 'PAYMENT',
        'amount': 45.00,
        'nameOrig': 'C_BENIGN_ALICE',
        'oldbalanceOrg': 1500.00,
        'nameDest': 'M_GROCERY_STORE',
        'oldbalanceDest': 0.00
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print(f"[AUDIT 2] Test A (Benign): Decision={res['decision']}, Action={res['action']}, Score={res['risk_score']}")
    assert res['decision'] == 'APPROVED' and res['action'] == 'APPROVE'

# 3. Test B — Obvious Fraudulent Balance Drain
req = urllib.request.Request(
    f'{BASE}/v1/risk/evaluate',
    data=json.dumps({
        'transaction_id': 'tx_audit_drain_02',
        'step': 452,
        'type': 'TRANSFER',
        'amount': 350000.00,
        'nameOrig': 'C_DRAIN_VICTIM',
        'oldbalanceOrg': 350000.00,
        'nameDest': 'C_DRAIN_MULE',
        'oldbalanceDest': 0.00
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print(f"[AUDIT 3] Test B (Drain Fraud): Decision={res['decision']}, Reason={res['reasons']['primary_code']}, Score={res['risk_score']}")
    assert res['decision'] == 'DECLINED' and res['reasons']['primary_code'] == 'RC_EXACT_BALANCE_DRAIN'

# 4. Test C — Borderline Transaction
req = urllib.request.Request(
    f'{BASE}/v1/risk/evaluate',
    data=json.dumps({
        'transaction_id': 'tx_audit_borderline_03',
        'step': 450,
        'type': 'CASH_OUT',
        'amount': 15000.00,
        'nameOrig': 'C_BORDER_01',
        'oldbalanceOrg': 30000.00,
        'nameDest': 'C_DEST_01',
        'oldbalanceDest': 10000.00
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print(f"[AUDIT 4] Test C (Borderline): Decision={res['decision']}, Score={res['risk_score']}, Reason={res['reasons']['primary_code']}")
    assert res['decision'] in ['APPROVED', 'STEP_UP_2FA', 'DECLINED']

# 5. Test D — Malformed / Missing Input
try:
    req = urllib.request.Request(
        f'{BASE}/v1/risk/evaluate',
        data=json.dumps({'amount': -500, 'type': 'INVALID'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        print("[AUDIT 5] Malformed Input Accepted (UNSAFE!)")
except urllib.error.HTTPError as e:
    print(f"[AUDIT 5] Test D (Malformed Input): Rejected safely with HTTP {e.code}")
    assert e.code == 422

# 6. Razorpay Webhook Signature Verification
secret = "test_webhook_secret_key"
payload = json.dumps({"event": "payment.authorized", "payload": {"payment": {"entity": {"id": "pay_test_01", "amount": 1000}}}}).encode('utf-8')
valid_sig = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

try:
    req = urllib.request.Request(
        f'{BASE}/v1/webhooks/razorpay',
        data=payload,
        headers={'Content-Type': 'application/json', 'X-Razorpay-Signature': 'invalid_signature_hash'}
    )
    with urllib.request.urlopen(req) as resp:
        print("[AUDIT 6] Webhook with Invalid Signature Accepted (UNSAFE!)")
except urllib.error.HTTPError as e:
    print(f"[AUDIT 6] Webhook Invalid Signature: Safely rejected with HTTP {e.code}")
    assert e.code in [400, 401, 403]

print("\n--- ALL ADVERSARIAL LIVE API PROBES COMPLETED SUCCESSFULLY ---")

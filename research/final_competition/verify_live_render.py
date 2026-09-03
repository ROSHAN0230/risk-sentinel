import urllib.request
import json
import sys

BASE = 'https://risk-sentinel.onrender.com'

def post_json(path, data):
    req = urllib.request.Request(
        f'{BASE}{path}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())

def get_json(path):
    req = urllib.request.Request(f'{BASE}{path}', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())

print("=================================================================")
print("  RISK SENTINEL — LIVE PUBLIC HTTPS VERIFICATION ON RENDER")
print(f"  Target URL: {BASE}")
print("=================================================================\n")

# 1. Health
st, res = get_json('/v1/health')
print(f"[+] 1. Health Check: [{st} OK] Engine: {res['engine_version']} | Status: {res['status']} | State Store Responsive: {res['state_store_responsive']}")
assert st == 200 and res['status'] == 'HEALTHY'

# 2. Model Manifest
st, res = get_json('/v1/model/info')
print(f"[+] 2. Model Manifest: [{st} OK] Champion Model B: {res['model_b']['sha256'][:16]}... (36-dim GBDT)")
print(f"                       Fallback Model A: {res['model_a']['sha256'][:16]}... (15-dim Causal)")
assert st == 200

# 3. Benchmark Summary
st, res = get_json('/v1/analytics/benchmark-summary')
print(f"[+] 3. Benchmark Surface: [{st} OK] Precision: {res['precision_percent']}% | Recall: {res['recall_percent']}% | Intercepted: {res['fraud_dollar_interception_percent']}%")
assert res['precision_percent'] == 96.29 and res['recall_percent'] == 99.65

# 4. Model Drift / PSI
st, res = get_json('/v1/analytics/model-drift')
print(f"[+] 4. Model Drift Engine: [{st} OK] Distribution PSI: {res['psi_results']['psi']} | Status: {res['psi_results']['status']}")
assert res['psi_results']['status'] == 'STABLE'

# 5. Live Inference (Benign vs Drain)
st, res_01 = post_json('/v1/risk/evaluate', {
    'transaction_id': 'tx_live_https_01',
    'step': 450,
    'type': 'PAYMENT',
    'amount': 84.50,
    'nameOrig': 'C_ALICE_01',
    'oldbalanceOrg': 1200.00,
    'nameDest': 'M_BOOKSTORE_01',
    'oldbalanceDest': 0.00
})
print(f"[+] 5A. Benign Payment Bypass: [{st} OK] Decision: {res_01['decision']} | Action: {res_01['action']} | Score: {res_01['risk_score']}")
assert res_01['decision'] == 'APPROVED'

st, res_03 = post_json('/v1/risk/evaluate', {
    'transaction_id': 'tx_live_https_03',
    'step': 452,
    'type': 'TRANSFER',
    'amount': 284100.50,
    'nameOrig': 'C_VICTIM_01',
    'oldbalanceOrg': 284100.50,
    'nameDest': 'C_MULE_01',
    'oldbalanceDest': 0.00
})
print(f"[+] 5B. 100% Balance Drain Fraud: [{st} OK] Decision: {res_03['decision']} | Action: {res_03['action']} | Score: {res_03['risk_score']} | Reason: {res_03['reasons']['primary_code']}")
assert res_03['decision'] == 'DECLINED'
assert res_03['reasons']['primary_code'] == 'RC_EXACT_BALANCE_DRAIN'

# 6. Razorpay Capture Gate
st, gate_a = post_json('/v1/gate/evaluate-and-capture', {
    'payment_id': 'pay_live_https_01',
    'amount_paise': 8450,
    'status': 'authorized',
    'method': 'upi',
    'notes': {'step': 450, 'type': 'PAYMENT', 'nameOrig': 'C_ALICE_01', 'oldbalanceOrg': 1200.00, 'nameDest': 'M_BOOKSTORE_01', 'oldbalanceDest': 0.00}
})
print(f"[+] 6A. Capture Gate Flow A (Approve): [{st} OK] Action: {gate_a['capture_action']} | Status: {gate_a['capture_status']}")
assert gate_a['capture_action'] == 'CAPTURE_CALLED'

st, gate_b = post_json('/v1/gate/evaluate-and-capture', {
    'payment_id': 'pay_live_https_02',
    'amount_paise': 28410050,
    'status': 'authorized',
    'method': 'upi',
    'notes': {'step': 452, 'type': 'TRANSFER', 'nameOrig': 'C_VICTIM_01', 'oldbalanceOrg': 284100.50, 'nameDest': 'C_MULE_01', 'oldbalanceDest': 0.00}
})
print(f"[+] 6B. Capture Gate Flow B (Suppress): [{st} OK] Action: {gate_b['capture_action']} | Status: {gate_b['capture_status']}")
assert gate_b['capture_action'] == 'CAPTURE_SUPPRESSED'

# 7. Decision Replay Studio Sandbox
st, replay = post_json('/v1/replay/evaluate', {
    'baseline_fixture_id': 'DEMO-03',
    'step': 452,
    'type': 'TRANSFER',
    'amount': 284100.50,
    'nameOrig': 'C_VICTIM_01',
    'oldbalanceOrg': 284100.50,
    'nameDest': 'C_MULE_01',
    'oldbalanceDest': 0.00,
    'counterfactual_scenario': 'SAFE_AMOUNT'
})
print(f"[+] 7. Replay Studio Sandbox: [{st} OK] Baseline Score: {replay['baseline_evaluation']['operating_score']} -> Replayed: {replay['replayed_evaluation']['operating_score']}")
assert st == 200

# 8. Cryptographic Audit Ledger
st, audit_events = get_json('/v1/audit/events?limit=3')
print(f"[+] 8. Cryptographic Audit Ledger: [{st} OK] Count: {len(audit_events)} | Latest Block Hash: {audit_events[0]['integrity_hash'][:16]}...")
assert st == 200 and len(audit_events) > 0

# 9. Investigation Dossier
st, dossier = get_json('/v1/investigations/demo-03')
print(f"[+] 9. Investigation Workspace: [{st} OK] 9-Pillar Dossier: Reason '{dossier['why_flagged']['primary_reason_code']}' | Decision: {dossier['policy_lineage']['decision']}")
assert st == 200

# 10. Frontend React 18 SPA
req = urllib.request.Request(f'{BASE}/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8')
    assert '<!doctype html>' in html.lower() or '<html' in html.lower()
    print(f"[+] 10. React SPA Root: [{resp.status} OK] Serving production dist bundle ({len(html)} bytes)")

print("\n>>> ALL 10 LIVE PUBLIC HTTPS ENDPOINTS ARE 100% OPERATIONAL ON RENDER! <<<\n")

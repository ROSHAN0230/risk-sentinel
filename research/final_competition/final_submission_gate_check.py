import subprocess
import hashlib
import unittest
import urllib.request
import json
import os
import re

print("=================================================================")
print("        FINAL SUBMISSION GATE — 14-POINT READ-ONLY AUDIT")
print("=================================================================\n")

# 1 & 2. Git Status and HEAD == origin/main
status = subprocess.check_output(['git', 'status', '--short'], text=True).strip()
commit_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
remote_sha = subprocess.check_output(['git', 'rev-parse', 'origin/main'], text=True).strip()

print(f"[1] Git Working Tree Clean: {status == ''} (Status: {status or 'CLEAN'})")
print(f"[2] HEAD == origin/main: {commit_sha == remote_sha} (Local: {commit_sha[:8]}, Remote: {remote_sha[:8]})")
assert status == ""
assert commit_sha == remote_sha

# 3. 133 / 133 Tests Pass
suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=0)
res = runner.run(suite)
print(f"[3] Test Suite: {res.testsRun}/133 Passed: {res.wasSuccessful()}")
assert res.wasSuccessful() and res.testsRun == 133

# 4. 9 Frozen Hashes
expected = {
    'model_b_stateful_hgb.joblib': ('src/engine/artifacts/model_b_stateful_hgb.joblib', '5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735'),
    'model_a_causal_hgb.joblib': ('src/engine/artifacts/model_a_causal_hgb.joblib', 'ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373'),
    'policy_engine.py': ('src/engine/policy_engine.py', 'b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e'),
    'decision_engine.py': ('src/engine/decision_engine.py', '1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f'),
    'feature_pipeline.py': ('src/engine/feature_pipeline.py', '41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993'),
    'model_manager.py': ('src/engine/model_manager.py', 'e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a'),
    'schemas.py': ('src/engine/schemas.py', 'de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf'),
    'audit_logger.py': ('src/engine/audit_logger.py', '044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb'),
    'state_store.py': ('src/engine/state_store.py', 'f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35')
}
hash_matches = True
for name, (path, exp_hash) in expected.items():
    with open(path, 'rb') as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    if actual_hash != exp_hash:
        hash_matches = False
print(f"[4] All 9 Frozen Checksums Match: {hash_matches}")
assert hash_matches

# 5. Frontend Dist Check
dist_html = os.path.exists('frontend/dist/index.html')
dist_js = len(os.listdir('frontend/dist/assets')) > 0 if os.path.exists('frontend/dist/assets') else False
print(f"[5] Frontend Assets Built & Present: {dist_html and dist_js}")
assert dist_html and dist_js

# 6, 7, 8. Live Public Render Endpoints
BASE = 'https://risk-sentinel.onrender.com'
def get_live(path):
    req = urllib.request.Request(f'{BASE}{path}', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())

def post_live(path, data):
    req = urllib.request.Request(
        f'{BASE}{path}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())

st_h, data_h = get_live('/v1/health')
print(f"[6] Live Render Health Check: HTTP {st_h} Status={data_h['status']} Version={data_h['engine_version']}")
assert st_h == 200 and data_h['status'] == 'HEALTHY'

st_b, data_b = post_live('/v1/risk/evaluate', {'transaction_id':'tx_gate_benign', 'step':450, 'type':'PAYMENT', 'amount':50.0, 'nameOrig':'C_B1', 'oldbalanceOrg':1000.0, 'nameDest':'M_B1', 'oldbalanceDest':0.0})
st_f, data_f = post_live('/v1/risk/evaluate', {'transaction_id':'tx_gate_fraud', 'step':452, 'type':'TRANSFER', 'amount':250000.0, 'nameOrig':'C_F1', 'oldbalanceOrg':250000.0, 'nameDest':'C_M1', 'oldbalanceDest':0.0})
print(f"[7] Live Risk Evaluate: Benign={data_b['decision']} | Fraud={data_f['decision']} ({data_f['reasons']['primary_code']})")
assert data_b['decision'] == 'APPROVED' and data_f['decision'] == 'DECLINED'

st_bm, data_bm = get_live('/v1/analytics/benchmark-summary')
print(f"[8] Live Benchmark Summary: Reachable={st_bm == 200} Precision={data_bm['precision_percent']}% Recall={data_bm['recall_percent']}%")
assert st_bm == 200

# 9. Capture Gate Local / Contract Verification
st_g, data_g = post_live('/v1/gate/evaluate-and-capture', {
    'payment_id': 'pay_gate_check',
    'amount_paise': 5000,
    'status': 'authorized',
    'method': 'upi',
    'notes': {'step':450, 'type':'PAYMENT', 'nameOrig':'C_B1', 'oldbalanceOrg':1000.0, 'nameDest':'M_B1', 'oldbalanceDest':0.0}
})
print(f"[9] Capture Gate Verified: Action={data_g['capture_action']} Status={data_g['capture_status']}")
assert st_g == 200 and data_g['capture_action'] == 'CAPTURE_CALLED'

# 10. FINAL_PUBLIC_CLAIMS.md Exists
claims_exist = os.path.exists('research/final_competition/FINAL_PUBLIC_CLAIMS.md')
print(f"[10] FINAL_PUBLIC_CLAIMS.md Exists: {claims_exist}")
assert claims_exist

# 11 & 12. Text Disclosures and Prohibited Claims Check
files_to_check = ['README.md', 'SUBMISSION.md', 'DEMO_GUIDE.md']
prohibited_patterns = [
    r'\bproduction-grade enterprise\b',
    r'\benterprise-scale\b',
    r'guaranteed sub-35ms',
    r'saved \$6\.32',
    r'actual Razorpay payment captured',
    r'live Razorpay capture'
]

violations = []
for fname in files_to_check:
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as f:
            content = f.read()
            for p in prohibited_patterns:
                if re.search(p, content, re.IGNORECASE):
                    violations.append(f"{fname}: matches {p}")

print(f"[11 & 12] Prohibited Claims Clean: {len(violations) == 0} (Violations: {violations})")
assert len(violations) == 0

# 13. Secrets Check
tracked_files = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
secret_pattern = re.compile(r'rnd_[a-zA-Z0-9]{24,}|rzp_live_[a-zA-Z0-9]{14,}')
secret_found = False
for tf in tracked_files:
    if os.path.exists(tf) and not tf.endswith(('.joblib', '.pkl', '.png', '.ico', '.svg', '.woff2')):
        try:
            with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
                if secret_pattern.search(c):
                    print(f"WARNING: Secret pattern found in {tf}")
                    secret_found = True
        except Exception:
            pass
print(f"[13] Zero Committed API Secrets / Live Keys: {not secret_found}")
assert not secret_found

# 14. Report
print("\n=================================================================")
print("             ALL 14 SUBMISSION GATES VERIFIED")
print(f"  Final Commit SHA : {commit_sha}")
print(f"  Live Render URL  : {BASE}")
print("=================================================================\n")

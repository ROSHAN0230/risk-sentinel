"""
Risk Sentinel — Gate 2 Real Headless Chrome Browser / CDP Verification Script
Executes full browser-level evaluation of /benchmarks, tests dynamic controls,
asserts DOM correctness, truth boundary disclaimers, and captures evidence.
"""

import os
import sys
import time
import json
import base64
import asyncio
import subprocess
import urllib.request
import websockets

PROJECT_ROOT = r"c:\Users\raahe\Downloads\razorpay"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8008
DEBUG_PORT = 9222
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "research", "phase_p1_1", "artifacts")

async def send_cdp(ws, method, params=None):
    msg_id = int(time.time() * 1000) % 10000000
    msg = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id:
            return resp.get("result", {})

async def eval_js(ws, expr):
    res = await send_cdp(ws, "Runtime.evaluate", {
        "expression": expr,
        "returnByValue": True,
        "awaitPromise": True
    })
    val = res.get("result", {}).get("value")
    return val

async def run_browser_verification():
    print("=================================================================")
    print("RISK SENTINEL — GATE 2 REAL HEADLESS CHROME / CDP VERIFICATION")
    print("=================================================================\n")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    evidence = {}

    # 1. Start FastAPI server
    server_cmd = [sys.executable, "-m", "uvicorn", "src.engine.api:app", "--port", str(PORT), "--host", "127.0.0.1"]
    server_proc = subprocess.Popen(server_cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"[*] Started FastAPI backend on port {PORT} (PID: {server_proc.pid})")

    # Wait for server health
    health_url = f"http://127.0.0.1:{PORT}/v1/health"
    ready = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(health_url) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            await asyncio.sleep(0.5)

    if not ready:
        server_proc.kill()
        raise RuntimeError("FastAPI server failed to start within 15 seconds.")
    print("[+] FastAPI server is HEALTHY and responsive.")

    # 2. Start Headless Chrome
    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1440,1080",
        "about:blank"
    ]
    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[*] Started Headless Google Chrome on debug port {DEBUG_PORT} (PID: {chrome_proc.pid})")
    await asyncio.sleep(2.0)

    # 3. Get WebSocket debugger URL
    debugger_url = None
    for _ in range(20):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json") as r:
                pages = json.loads(r.read().decode("utf-8"))
                if pages and "webSocketDebuggerUrl" in pages[0]:
                    debugger_url = pages[0]["webSocketDebuggerUrl"]
                    break
        except Exception:
            await asyncio.sleep(0.5)

    if not debugger_url:
        chrome_proc.kill()
        server_proc.kill()
        raise RuntimeError("Failed to connect to Chrome DevTools WebSocket.")
    print(f"[+] Connected to Chrome CDP: {debugger_url}")

    # 4. Connect via WebSocket
    async with websockets.connect(debugger_url, max_size=50*1024*1024) as ws:
        await send_cdp(ws, "Page.enable")
        await send_cdp(ws, "Runtime.enable")
        await send_cdp(ws, "Network.enable")

        # Track console errors
        console_errors = []
        # Navigate to /benchmarks
        target_url = f"http://127.0.0.1:{PORT}/benchmarks"
        print(f"[*] Navigating to {target_url}...")
        await send_cdp(ws, "Page.navigate", {"url": target_url})
        await asyncio.sleep(3.0) # Allow React bundle hydration and API fetch

        # TEST A: Page Loads Successfully
        title = await eval_js(ws, "document.title")
        body_text = await eval_js(ws, "document.body.innerText")
        has_heading = "Decision Economics & False-Positive Cost Simulator" in body_text
        print(f"[+] Test A (Page Load): Title='{title}', Economics Explorer Visible={has_heading}")
        evidence["test_a_page_load"] = {
            "status": "PASS" if has_heading else "FAIL",
            "title": title,
            "has_heading": has_heading
        }

        # TEST B: Alpha Control Interaction
        alpha_text_before = await eval_js(ws, "document.querySelector('span.text-amber-400.font-bold').innerText")
        # Click 5.0% preset button
        await eval_js(ws, """
            const buttons = Array.from(document.querySelectorAll('button'));
            const b5 = buttons.find(b => b.innerText.includes('5.0%'));
            if (b5) b5.click();
        """)
        await asyncio.sleep(0.5)
        alpha_text_after_5 = await eval_js(ws, "document.querySelector('span.text-amber-400.font-bold').innerText")

        # Click 0.1% preset button
        await eval_js(ws, """
            const buttons = Array.from(document.querySelectorAll('button'));
            const b01 = buttons.find(b => b.innerText.includes('0.1%'));
            if (b01) b01.click();
        """)
        await asyncio.sleep(0.5)
        alpha_text_after_01 = await eval_js(ws, "document.querySelector('span.text-amber-400.font-bold').innerText")

        # Reset to 1.0%
        await eval_js(ws, """
            const buttons = Array.from(document.querySelectorAll('button'));
            const b1 = buttons.find(b => b.innerText.includes('1.0%'));
            if (b1) b1.click();
        """)
        await asyncio.sleep(0.5)

        alpha_success = (alpha_text_after_5 == "5.0%" and alpha_text_after_01 == "0.1%")
        print(f"[+] Test B (Alpha Interaction): Before={alpha_text_before}, After 5%={alpha_text_after_5}, After 0.1%={alpha_text_after_01}")
        evidence["test_b_alpha_interaction"] = {
            "status": "PASS" if alpha_success else "FAIL",
            "initial": alpha_text_before,
            "five_percent": alpha_text_after_5,
            "point_one_percent": alpha_text_after_01
        }

        # TEST C: Threshold Selector Interaction
        options_count = await eval_js(ws, "document.querySelectorAll('select option').length")
        options_list = await eval_js(ws, "Array.from(document.querySelectorAll('select option')).map(o => o.value)")
        expected_thresholds = [
            "0.9", "0.91", "0.92", "0.93", "0.94", "0.95", "0.96", "0.97", "0.975", "0.98", "0.985", "0.99", "0.995", "0.997", "0.999"
        ]
        # Change threshold selection to 0.95
        await eval_js(ws, """
            const sel = document.querySelector('select');
            sel.value = '0.95';
            sel.dispatchEvent(new Event('change', { bubbles: true }));
        """)
        await asyncio.sleep(0.5)
        sel_val = await eval_js(ws, "document.querySelector('select').value")
        # Reset to 0.99
        await eval_js(ws, """
            const sel = document.querySelector('select');
            sel.value = '0.99';
            sel.dispatchEvent(new Event('change', { bubbles: true }));
        """)
        await asyncio.sleep(0.5)

        threshold_success = (options_count == 15 and float(sel_val) == 0.95)
        print(f"[+] Test C (Threshold Selector): Option Count={options_count} (15 expected), Select interaction verified.")
        evidence["test_c_threshold_selector"] = {
            "status": "PASS" if threshold_success else "FAIL",
            "options_count": options_count,
            "options": options_list
        }

        # TEST D: Production Policy Indicator & No Mutation Verbs
        has_prod_badge = "FROZEN PRODUCTION POLICY: θ* = 0.990" in body_text
        has_table_active_badge = "Active Policy (θ*=0.990)" in body_text
        prohibited_verbs = ["apply threshold", "set production threshold", "change live policy", "deploy threshold"]
        found_prohibited = [v for v in prohibited_verbs if v in body_text.lower()]
        prod_indicator_success = has_prod_badge and has_table_active_badge and len(found_prohibited) == 0
        print(f"[+] Test D (Production Policy Indicator): Badge Present={has_prod_badge}, Prohibited Verbs Found={found_prohibited}")
        evidence["test_d_production_policy_indicator"] = {
            "status": "PASS" if prod_indicator_success else "FAIL",
            "has_prod_badge": has_prod_badge,
            "has_table_active_badge": has_table_active_badge,
            "prohibited_verbs_found": found_prohibited
        }

        # TEST E: Validation Split Labeling
        has_validation_badge = "VALIDATION SENSITIVITY" in body_text
        has_steps_label = "PaySim Steps 336–377" in body_text
        val_label_success = has_validation_badge and has_steps_label
        print(f"[+] Test E (Validation Split Labeling): Validation Badge={has_validation_badge}, Steps 336–377={has_steps_label}")
        evidence["test_e_validation_split_labeling"] = {
            "status": "PASS" if val_label_success else "FAIL",
            "has_validation_badge": has_validation_badge,
            "has_steps_label": has_steps_label
        }

        # TEST F: Future-Test Benchmark Separation
        has_future_section = "Future Held-Out PaySim Benchmark Evaluation" in body_text
        has_future_steps = "Steps 378–743" in body_text
        has_future_recall = "99.65%" in body_text
        has_future_prec = "96.29%" in body_text
        future_sep_success = has_future_section and has_future_steps and has_future_recall and has_future_prec
        print(f"[+] Test F (Future-Test Separation): Section Exists={has_future_section}, Recall 99.65%={has_future_recall}")
        evidence["test_f_future_test_separation"] = {
            "status": "PASS" if future_sep_success else "FAIL",
            "has_future_section": has_future_section,
            "has_future_steps": has_future_steps,
            "has_future_precision": has_future_prec,
            "has_future_recall": has_future_recall
        }

        # TEST G: Economic Wording
        has_economic_formula = "Total Cost = Missed Fraud FN Dollars + α × Flagged Non-Fraud Amount" in body_text
        has_disclaimer = "Exploratory scenario sensitivity modeling — does not represent Razorpay unit economics" in body_text
        econ_wording_success = has_economic_formula and has_disclaimer
        print(f"[+] Test G (Economic Wording): Formula Verified={has_economic_formula}, Disclaimer Verified={has_disclaimer}")
        evidence["test_g_economic_wording"] = {
            "status": "PASS" if econ_wording_success else "FAIL",
            "has_economic_formula": has_economic_formula,
            "has_disclaimer": has_disclaimer
        }

        # TEST H: Non-Fraud Terminology
        has_flagged_nonfraud = "Flagged Non-Fraud Amount" in body_text
        has_y0_note = "Non-fraud refers to the PaySim dataset label (y=0)" in body_text
        nonfraud_success = has_flagged_nonfraud and has_y0_note
        print(f"[+] Test H (Non-Fraud Terminology): Flagged Non-Fraud Amount={has_flagged_nonfraud}, y=0 Note={has_y0_note}")
        evidence["test_h_nonfraud_terminology"] = {
            "status": "PASS" if nonfraud_success else "FAIL",
            "has_flagged_nonfraud": has_flagged_nonfraud,
            "has_y0_note": has_y0_note
        }

        # TEST I: Threshold Optimum Wording
        prohibited_optimum_claims = [
            "global optimum", "globally optimal threshold", "economically optimal threshold", "expected loss optimum"
        ]
        found_optimum_claims = [c for c in prohibited_optimum_claims if c in body_text.lower()]
        has_disciplined_wording = "lowest observed validation-split scenario cost across the tested α values" in body_text
        optimum_wording_success = len(found_optimum_claims) == 0 and has_disciplined_wording
        print(f"[+] Test I (Optimum Wording): Disciplined Wording={has_disciplined_wording}, Prohibited Claims Found={found_optimum_claims}")
        evidence["test_i_optimum_wording"] = {
            "status": "PASS" if optimum_wording_success else "FAIL",
            "has_disciplined_wording": has_disciplined_wording,
            "prohibited_claims_found": found_optimum_claims
        }

        # Capture Screenshot
        screenshot_data = await send_cdp(ws, "Page.captureScreenshot", {"format": "png"})
        png_bytes = base64.b64decode(screenshot_data.get("data", ""))
        screenshot_path = os.path.join(ARTIFACTS_DIR, "benchmarks_p1_1_verified.png")
        with open(screenshot_path, "wb") as f:
            f.write(png_bytes)
        print(f"[+] Captured full-page screenshot ({len(png_bytes)} bytes) to {screenshot_path}")

    # 5. Clean teardown
    chrome_proc.terminate()
    server_proc.terminate()
    try:
        chrome_proc.wait(timeout=3)
        server_proc.wait(timeout=3)
    except Exception:
        chrome_proc.kill()
        server_proc.kill()
    print("[*] Chrome and FastAPI server terminated cleanly.")

    # Save evidence json
    evidence_path = os.path.join(ARTIFACTS_DIR, "browser_verification_evidence.json")
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"[*] Gate 2 Evidence JSON saved to {evidence_path}")

    # Summary
    all_pass = all(v.get("status") == "PASS" for v in evidence.values())
    print(f"\n=================================================================")
    print(f"[*] GATE 2 BROWSER VERIFICATION OVERALL STATUS: {'PASS' if all_pass else 'FAIL'}")
    print(f"=================================================================")
    return all_pass

if __name__ == "__main__":
    asyncio.run(run_browser_verification())

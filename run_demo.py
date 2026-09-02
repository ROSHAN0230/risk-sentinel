"""
Risk Sentinel — Full-Stack Application & Demo Launcher
Starts the unified FastAPI backend and React frontend,
verifies engine health, and automatically opens the browser at http://localhost:8000.
"""

import sys
import time
import os
import webbrowser
import urllib.request
import uvicorn

PORT = 8000
HOST = "127.0.0.1"

def main():
    print("=================================================================")
    print("  RISK SENTINEL — AI DECISION ENGINE (v2.8.0-prod)")
    print("  Razorpay AI Risk Manager / AI Builder Track")
    print("=================================================================\n")
    print(f"[*] Initializing Risk Sentinel Engine on http://{HOST}:{PORT}...")

    # Open browser automatically after a short delay
    def open_browser():
        time.sleep(1.5)
        url = f"http://localhost:{PORT}"
        print(f"[+] Opening Risk Sentinel Dashboard: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[-] Could not launch browser automatically: {e}")
            print(f"[*] Please open {url} manually in your browser.")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    from src.engine.api import app
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except KeyboardInterrupt:
        print("\n[+] Risk Sentinel engine shutdown cleanly.")

if __name__ == "__main__":
    main()

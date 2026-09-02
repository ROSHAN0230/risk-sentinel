# Walkthrough — Risk Sentinel Phase 2.11: Product Integration Contract & Demo Experience Freeze

All contracts, UI specifications, consistency audit scripts, and handoff packages for Phase 2.11 have been generated and validated under `research/phase2_11/`.

---

## 1. Directory Structure of Phase 2.11 Deliverables

```
razorpay/
└── research/phase2_11/
    ├── API_CONTRACT.md                        # Strict REST schema, payload constraints, error codes
    ├── POLICY_CONTRACT.md                     # Locked decision thresholds, risk bands, action rules
    ├── MODEL_CONTRACT.md                      # Champion (Model B) & Fallback (Model A) lineage & hashes
    ├── EXPLANATION_CONTRACT.md                # Certified Reason Codes, causal evidence, narrative templates
    ├── DEMO_CONTRACT.md                       # Machine-readable specification for DEMO-01 to DEMO-09
    ├── UI_DATA_CONTRACT.md                    # Data boundary separating live stream, benchmark & disclaimers
    ├── CLAIMS_AND_DISCLAIMERS.md              # Truth boundary: confident facts vs required scenario disclaimers
    ├── STITCH_HANDOFF.md                      # UI/UX information architecture, components, design rules
    ├── ANTIGRAVITY_IMPLEMENTATION_HANDOFF.md  # Backend integration guide with src/engine/api.py
    ├── consistency_audit.py                   # Automated cross-phase consistency verification script
    ├── phase2_11_results.json                 # Machine-readable freeze manifest with hashes & schemas
    ├── FINAL_REPORT.md                        # Master reconciliation and consistency audit report
    └── walkthrough.md                         # Walkthrough guide for Phase 2.11
```

---

## 2. Key Frozen Contracts Summary

1. **API Schema**: Strict Pydantic contracts on `POST /v1/risk/evaluate`, `GET /v1/health`, `GET /v1/model/info`, and `GET /v1/audit/events`.
2. **Policy Thresholds**: $\theta_{\text{high}} = 0.9900$, $\theta_{\text{medium}} = 0.9000$ (with decoupled actions: `APPROVE`, `STEP_UP_CHALLENGE`, `MANUAL_REVIEW`, `DECLINE`).
3. **Model Hierarchy**: Model B (Stateful Champion, 36 features, SHA-256: `5ea59263...`) with automatic circuit-breaker fallback to Model A (Causal Baseline, 15 features, SHA-256: `ea356eb3...`).
4. **Explainability**: Deterministic Reason Codes (`RC_EXACT_BALANCE_DRAIN`, `RC_SEVERE_LIQUIDITY_DRAIN`, `RC_DEST_MULE_VELOCITY`, etc.) backed by causal point-in-time evidence grids.
5. **9 Demo Fixtures**: Fully defined test cases (`DEMO-01` to `DEMO-09`) covering normal payments, suspicious liquidations, cold-start handling, fallback outages, model tamper defense, and audit trails.

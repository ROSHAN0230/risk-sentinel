# Risk Sentinel — Phase 4 Production-Hardening Audit
**Document ID**: `AUDIT-P4-PROD-001`  
**Date**: `2026-09-02`  
**Phase**: `Phase 4 Pre-Implementation Architectural Audit`  
**Status**: `READ-ONLY AUDIT COMPLETE — AWAITING AUTHORIZATION`  

---

## Executive Summary

This audit assesses the evolution of **Risk Sentinel** from a competition-grade fraud decision engine into an enterprise-grade, production-oriented portfolio project.

### Core Non-Negotiable Constraint
The 9 frozen core production components remain **100% byte-for-byte immutable**. Any Phase 4 enhancements must be **strictly additive**, utilizing clean dependency injection and outer boundary adapters without altering model binaries, decision scores, policy thresholds, reason codes, or existing test semantics.

---

## 1. Frozen Core Verification Baseline

All 9 frozen files were verified against their canonical SHA-256 checksums:

```
========================================================================================================================
COMPONENT FILE                        CANONICAL SHA-256 HASH                                            STATUS
========================================================================================================================
model_b_stateful_hgb.joblib           5ea5926344e12215fe6e9fe91b593a99feb581747c2f4272471a773680944735 VERIFIED EXACT
model_a_causal_hgb.joblib             ea356eb3bd713de47c1cdc34389db461a02c95e8c489c5767c396886e65da373 VERIFIED EXACT
policy_engine.py                      b61ab343af0e5aa84726db1d96700b89b8e22b88a597f73c97b8320b430b9b5e VERIFIED EXACT
decision_engine.py                    1b5f1615f90548fa5eba94231e207d43d3e0bf7a6d68d47b802a56daaa747a4f VERIFIED EXACT
feature_pipeline.py                   41b315ed0eaff96321d7dfabab72f5fdd1a254a39604445500d545bc55a7b993 VERIFIED EXACT
model_manager.py                      e2400085415e93554e480d8ff4f78fe22852c007fc5926fc27da0352d5f6899a VERIFIED EXACT
schemas.py                            de16b6bba9d2b235611adf52272ff033cb40eafff6ce92c2b7de56725ff093bf VERIFIED EXACT
audit_logger.py                       044951b6a014a07cd48179cd9d5388373ddd2b4e0dc980934db1d980e4a68afb VERIFIED EXACT
state_store.py                        f7f6615a0277bb11631fe4dbc0be5ddde26a1c28889eff6827243946b2b70d35 VERIFIED EXACT
========================================================================================================================
```

Operating thresholds remain permanently locked at **$\theta^* = 0.990$** and **$\theta_{\text{med}} = 0.900$**.

---

## A. Current Architecture Inventory

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                CURRENT RISK SENTINEL INVENTORY                                    │
├──────────────────────────┬───────────────────────────────────────────┬───────────────────────────┤
│ LAYER                    │ COMPONENT & LOCATION                      │ IMMUTABILITY / SCOPE      │
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ Gateway & Ingestion      │ src/engine/api.py                         │ Modifiable (API routes)   │
│                          │ src/engine/integrations/razorpay_adapter  │ Additive Webhook Adapter  │
│                          │ src/engine/integrations/capture_gate.py   │ Additive Capture Gate     │
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ Decisioning Core         │ src/engine/decision_engine.py             │ FROZEN CORE               │
│                          │ src/engine/model_manager.py               │ FROZEN CORE               │
│                          │ src/engine/policy_engine.py               │ FROZEN CORE               │
│                          │ src/engine/feature_pipeline.py            │ FROZEN CORE               │
│                          │ src/engine/schemas.py                     │ FROZEN CORE               │
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ State & Fault Tolerance  │ src/engine/state_store.py                 │ FROZEN CORE (InMemory)    │
│                          │ StateStoreCircuitBreaker (15ms guard)     │ FROZEN CORE               │
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ Audit & Analytics        │ src/engine/audit_logger.py                │ FROZEN CORE (Chained SHA) │
│                          │ src/engine/analytics/economics_service.py │ Additive (15-pt ladder)   │
│                          │ src/engine/analytics/replay_service.py    │ Additive Sandbox Replay   │
│                          │ src/engine/investigations/                │ Additive 9-Pillar Dossier │
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ User Interface           │ frontend/src/pages/                       │ React 18 + TS Dashboard   │
│                          │ frontend/dist/                            │ Compiled Production Bundle│
├──────────────────────────┼───────────────────────────────────────────┼───────────────────────────┤
│ Testing & Verification   │ tests/ (106 automated tests)              │ 100% Passing Regression   │
└──────────────────────────┴───────────────────────────────────────────┴───────────────────────────┘
```

---

## B. Seven-Area Gap Matrix

```
======================================================================================================================================================
AREA                     EXISTING CAPABILITY            MISSING CAPABILITY              LOCAL/FREE?   EXTERNAL?     CREDS?    DB?    PRIORITY
======================================================================================================================================================
1. Distributed State     InMemoryStateStore + Circuit   Production Redis provider with  YES (mock /   Optional      NO        NO     P1 (High)
                         Breaker with 15ms fallback     piped operations, TTL, retry    local Docker) (Redis/Aero)
------------------------------------------------------------------------------------------------------------------------------------------------------
2. Security & Auth       HMAC-SHA256 signature check    API Key header auth, Bearer     YES (env-var  NO            NO        NO     P1 (High)
                         for webhooks; no route auth    token, in-memory rate limiting  secrets)      (Auth0/Okta)
------------------------------------------------------------------------------------------------------------------------------------------------------
3. Durable Audit/Events  Chained SHA-256 in-memory &    AuditSink interface, JSONL file YES (local    Optional      NO        NO     P2 (Medium)
                         JSONL disk buffer              sink, batch flusher, WORM sim   WORM/files)   (Kafka/S3)
------------------------------------------------------------------------------------------------------------------------------------------------------
4. Model Monitoring      Offline score distribution &   Live Population Stability Index YES (offline  NO            NO        NO     P2 (Medium)
                         threshold sensitivity ladder   (PSI) calculator, drift alert   test slices)  (Arize/Fiddl)
------------------------------------------------------------------------------------------------------------------------------------------------------
5. Auth Lifecycle        Immediate capture or hold in   Formal state machine lifecycle  YES (local    Optional      NO (test  Opt.   P3 (Medium)
                         capture gate                   (Pending, Expired, Voided, Cap) provider)     (RZP Live)    keys opt) (SQLite)
------------------------------------------------------------------------------------------------------------------------------------------------------
6. Richer Risk Signals   36-dim causal/stateful balance Optional telemetry schema ext;  YES (schema   Optional      NO        NO     P4 (Low /
                         and velocity features          no synthetic fake data          hooks only)   (MaxMind/FP)                   Extension)
------------------------------------------------------------------------------------------------------------------------------------------------------
7. Scale / Load Testing  In-process latency benchmark   Multi-worker concurrent load    YES (pytest / NO            NO        NO     P1 (High)
                         (1,000 back-to-back requests)  profiling (Locust/async harness)async harness)
======================================================================================================================================================
```

---

## C. Recommended Phase 4 Implementation Order

Ranking based on **Engineering Value**, **Portfolio ROI**, **Competition Safety**, and **Measurable Benefit**:

### Rank 1: Area 2 — Security & Service Authentication (Highest ROI)
- **Why**: Takes a "hackathon script" and turns it into an enterprise microservice.
- **Value**: Demonstrates defense-in-depth, rate limiting, and API security without adding database complexity.
- **Risk to Core**: Zero (implemented via FastAPI middleware/dependencies).

### Rank 2: Area 7 — Concurrent Load & Scale Testing
- **Why**: Proves that the sub-15ms circuit breaker and async gateway actually handle concurrent spikes under multi-client pressure.
- **Value**: Empirical p50, p95, p99 latency curves under 50–100 concurrent workers.
- **Risk to Core**: Zero (test harness only).

### Rank 3: Area 1 — Distributed-Ready State Layer (Redis Provider)
- **Why**: Decouples in-memory single-process limitations.
- **Value**: Demonstrates multi-node horizontal scalability. Local mode remains 100% functional without Redis.
- **Risk to Core**: Zero (implemented via an additive `RedisStateStoreProvider` injected into `RiskDecisionEngine`).

### Rank 4: Area 4 — Model Monitoring & PSI Drift Engine
- **Why**: Closes the loop on the machine learning lifecycle.
- **Value**: Demonstrates MLOps maturity by detecting concept drift on chronological slices without touching frozen weights.
- **Risk to Core**: Zero (read-only analytical service).

### Rank 5: Area 3 — Durable Audit Event Sink
- **Why**: Provides a clean enterprise abstraction for compliance logging.
- **Value**: Formal `AuditSink` interface supporting local append-only JSONL files with optional streaming hooks.
- **Risk to Core**: Zero (subclasses or wraps existing `AuditLogger`).

### Rank 6: Area 5 — Provider-Agnostic Authorization Lifecycle State Machine
- **Why**: Shows understanding of payment authorization expiry windows.
- **Value**: Tracks authorization states beyond immediate capture (`AUTHORIZED` $\to$ `HELD` $\to$ `EXPIRED`/`VOIDED`).
- **Risk to Core**: Zero (additive module in `src/engine/integrations/`).

### Rank 7: Area 6 — Richer Risk Signals (Documented Extension Points Only)
- **Why**: Adding fake device/IP features without ground-truth labels damages scientific integrity.
- **Value**: Keep as clean, documented schema extension hooks (`Optional[ClientContext]`).

---

## D. Exact File Plan

### 1. New Additive Files Proposed
```
src/engine/infrastructure/
├── security.py                 # API-key, Bearer token & rate-limiting middleware
├── redis_provider.py           # Additive RedisStateStore implementing BaseStateStore
├── audit_sink.py               # Durable AuditSink interface (FileSink, MemorySink)
└── monitoring/
    ├── drift_service.py        # Population Stability Index (PSI) & score drift engine
    └── metrics.py              # In-memory Prometheus-compatible metric counters

src/engine/integrations/
└── lifecycle_manager.py        # Provider-agnostic authorization state machine

tests/
├── test_security_auth.py       # Authentication, bad key rejection, rate limit tests
├── test_redis_state_store.py   # Redis contract, connection failure fallback tests
├── test_drift_monitoring.py    # PSI calculation, drift alert boundary tests
├── test_auth_lifecycle.py      # Authorization state transition & expiry tests
└── test_concurrent_load.py     # Multi-threaded concurrent throughput benchmark
```

### 2. Files to Modify (Non-Core Outer Periphery Only)
- `src/engine/api.py`: Mount authentication dependencies on administrative endpoints; register lifecycle & drift routes.
- `requirements.txt`: Add optional `redis>=5.0.0` and `slowapi>=0.1.9`.
- `README.md`: Document Phase 4 production capabilities and load profiles.

### 3. Frozen Core Files (STRICTLY UNTOUCHED)
- `src/engine/artifacts/model_b_stateful_hgb.joblib` [FROZEN]
- `src/engine/artifacts/model_a_causal_hgb.joblib` [FROZEN]
- `src/engine/policy_engine.py` [FROZEN]
- `src/engine/decision_engine.py` [FROZEN]
- `src/engine/feature_pipeline.py` [FROZEN]
- `src/engine/model_manager.py` [FROZEN]
- `src/engine/schemas.py` [FROZEN]
- `src/engine/audit_logger.py` [FROZEN]
- `src/engine/state_store.py` [FROZEN]

---

## E. Infrastructure Requirements & Database Decision

### The Database Decision: IS A DATABASE NEEDED?
**NO.** Introducing PostgreSQL, MongoDB, or MySQL at this stage is **not justified** and represents classic "resume padding" that introduces unnecessary failure modes:
1. **API Authentication**: Can be implemented via environment secret matching (`secrets.compare_digest`) and signed tokens. No DB required.
2. **Rate Limiting**: Can be implemented via in-memory sliding windows. No DB required.
3. **Audit Ledger**: Local chained SHA-256 JSONL append-only log provides stronger non-repudiation than an open relational database. No DB required.
4. **State Store**: Key-value velocity tracking belongs in Redis/Memory, not in SQL transactions. No relational DB required.
5. **Authorization Lifecycle**: In-memory state with an optional SQLite/file cache is sufficient for a single-node portfolio demo.

### Infrastructure Matrix
- **Zero-Dependency Core**: Risk Sentinel continues to run with `pip install -r requirements.txt` and `python run_demo.py`.
- **Optional Local Docker**: An optional `docker-compose.yml` can spin up a local Redis instance for testing `RedisStateStore`. If Redis is offline, the system seamlessly falls back to `InMemoryStateStore` or trips the Model A circuit breaker.

---

## F. Claim-Safety Audit (Strict Prohibitions)

To maintain absolute technical integrity, the following claims are **strictly forbidden**:
1. ❌ **"Razorpay uses Redis/Aerospike"** $\to$ *Correct*: "A distributed state layer is required in multi-node payment gateways; Redis or Aerospike are viable architectural options."
2. ❌ **"Razorpay 35ms SLA"** $\to$ *Correct*: "35ms is an internal gateway engineering budget / project target."
3. ❌ **"96-hour Razorpay authorization requirement"** $\to$ *Correct*: "Payment card networks enforce provider-specific authorization capture windows (typically 5–7 days before auto-voiding)."
4. ❌ **"Automated online model replacement"** $\to$ *Correct*: "Drift metrics trigger human review and shadow evaluation; models are never replaced automatically without explicit governance."
5. ❌ **"Razorpay production scale"** $\to$ *Correct*: "Benchmarked under simulated concurrent load on local hardware."

---

## G. The "Profit" Analysis (Career & Portfolio ROI)

| Phase 4 Capability | Implementation Effort | Portfolio & Interview ROI | Worth Implementing Now? |
| :--- | :--- | :--- | :--- |
| **API Auth & Security** | ~1.5 hours | **HIGH**: Demonstrates production microservice security practices. | **YES** |
| **Concurrent Load Harness** | ~1 hour | **VERY HIGH**: Provides real p95/p99 concurrency numbers that impress Staff Engineers. | **YES** |
| **Redis Provider Adapter** | ~2 hours | **HIGH**: Proves horizontal scalability while maintaining zero-dependency local mode. | **YES** |
| **Model Drift (PSI Engine)** | ~2 hours | **HIGH**: Shows MLOps maturity without modifying frozen model weights. | **YES** |
| **Auth Lifecycle State Machine** | ~1.5 hours | **MEDIUM**: Deepens payment domain understanding. | **YES** |
| **Richer Risk Signals** | ~3 hours | **LOW**: Adding fake device/IP features without training labels harms scientific honesty. | **NO (Document hooks only)** |
| **PostgreSQL / Mongo DB** | ~4 hours | **NEGATIVE**: Adds container/setup friction with zero architectural necessity. | **NO (Reject DB)** |

---

## H. Final Recommendation & Smallest Path Forward

### Smallest Path to a Genuinely Stronger Portfolio Project:
1. **Security (`src/engine/infrastructure/security.py`)**: Add API key validation (`X-API-Key`) and in-memory rate limiting with public demo exemptions.
2. **Concurrent Load Benchmark (`tests/test_concurrent_load.py`)**: Measure multi-worker throughput and latency under 50+ concurrent requests.
3. **Additive Redis Provider (`src/engine/infrastructure/redis_provider.py`)**: Provide an optional `RedisStateStore` that falls back cleanly to memory if Redis is absent.
4. **MLOps Drift Calculator (`src/engine/infrastructure/monitoring/drift_service.py`)**: Calculate PSI between validation baseline and chronological test slices.
5. **Authorization Lifecycle (`src/engine/integrations/lifecycle_manager.py`)**: Formalize the payment state machine.

**STOP**: No source files were modified during this audit. Awaiting your explicit review and authorization to proceed with any of these additive enhancements.

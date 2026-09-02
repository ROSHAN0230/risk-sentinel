# Risk Sentinel Security Architecture & Trust Boundaries
**Document ID**: `SEC-ARCH-2.8-001`  
**Status**: `FROZEN DESIGN`  

---

## 1. Defensive Security Architecture & Trust Boundaries

```
[Public Internet / Untrusted Client Browser]
                   │  (HTTPS / TLS 1.3)
                   ▼
┌─────────────────────────────────────────────────────────┐
│ TRUST BOUNDARY 1: API Gateway (Edge Reverse Proxy)      │
│  - Rate Limiting (Token Bucket: 100 req/s per API key) │
│  - Mutual TLS / HMAC Signature Verification             │
│  - Schema Validation (Pydantic / Rust Validator)        │
└──────────────────────────┬──────────────────────────────┘
                           │  (mTLS Internal Mesh)
                           ▼
┌─────────────────────────────────────────────────────────┐
│ TRUST BOUNDARY 2: Risk Engine Service (Isolated VPC)    │
│  - Strict Pre-Execution Causal Feature Builder          │
│  - Circuit Breakers & Timeout Handlers                  │
│  - Zero Direct Write Access to Raw Model Binaries       │
└──────────────┬───────────────────────────┬──────────────┘
               │ (Local Memory / Unix Sock)│ (Private VPC)
               ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ TRUST BOUNDARY 3:         │ │ TRUST BOUNDARY 4:         │
│ Model Inference Engine    │ │ Stateful Cache Store      │
│  - Read-Only GBDT Binaries│ │ (Redis Cluster / Aero)    │
│  - SHA-256 Verified Binary│ │  - Ephemeral TTL (30 Days)│
│  - Sandboxed Execution    │ │  - Read-Only During Eval  │
└───────────────────────────┘ └─────────────┬─────────────┘
                                            │ (Post-Eval Write)
                                            ▼
┌─────────────────────────────────────────────────────────┐
│ TRUST BOUNDARY 5: Immutable Audit Ledger (Write-Only)   │
│  - Append-Only Cryptographically Chained Storage        │
│  - PII Masking & Salted Identifier Hashing              │
│  - WORM (Write Once Read Many) Storage Policy           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Defensive Security Principles

1. **Zero Client Trust**: The frontend and payment SDKs never pass computed risk scores, historical counters, or feature values. The Risk Engine accepts only raw transaction metadata and computes all features server-side.
2. **Model Artifact Tamper Resistance**: All GBDT binaries are cryptographically signed with SHA-256 hashes at build time. On startup, the engine verifies the hash before loading. If tampered, the engine refuses to start and alerts security.
3. **Audit Immutability & Anti-Repudiation**: Decisions cannot be retroactively modified or deleted. Each audit event contains an HMAC signature derived from the transaction inputs, decision output, and previous block hash.
4. **Denial-of-Service (DoS) Protection**:
   - Edge rate-limiting (Token bucket per merchant key).
   - Strict payload size limits ($< 64\text{ KB}$).
   - 15ms circuit breaker on state lookups prevents cache latency storms from exhausting worker threads.

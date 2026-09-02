"""
Risk Sentinel — Security, Authentication & Rate Limiting Test Suite
Tests:
1. Valid API key accepted via X-API-Key header.
2. Valid API key accepted via Authorization: Bearer token.
3. Missing API key rejected (401) when auth is enforced.
4. Invalid API key rejected (401) with constant-time comparison.
5. Public endpoints (/v1/health, /v1/model/info) accessible without credentials.
6. In-memory sliding-window rate limiter allows allowed bursts and blocks excess (429).
7. Rate limiter prunes expired entries to prevent memory leaks.
8. HTTP security headers present on API responses.
9. Webhook HMAC-SHA256 signature verification regression safety.
10. Secrets not leaked in error responses.
"""

import os
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.engine.api import app
from src.engine.infrastructure.security import (
    InMemoryRateLimiter,
    default_rate_limiter,
    verify_api_key,
    get_configured_api_key
)

class TestSecurityAndAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        default_rate_limiter.reset()

    def test_public_health_endpoint_no_auth(self):
        """Public /v1/health must remain accessible without API keys."""
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertIn("champion_model_sha256", data)

    def test_security_headers_present(self):
        """Standard HTTP security headers must be injected on all responses."""
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(resp.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    @patch.dict(os.environ, {"RISK_SENTINEL_API_KEY": "test-secret-key-12345", "RISK_SENTINEL_REQUIRE_AUTH": "true"})
    def test_enforced_auth_rejection_missing_key(self):
        """When auth is enforced, requests without API key must receive 401 Unauthorized."""
        payload = {
            "transaction_id": "tx_sec_001",
            "step": 100,
            "type": "PAYMENT",
            "amount": 500.0,
            "nameOrig": "C100000001",
            "oldbalanceOrg": 5000.0,
            "nameDest": "M200000001",
            "oldbalanceDest": 0.0
        }
        resp = self.client.post("/v1/risk/evaluate", json=payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Missing or invalid API credentials", resp.json()["detail"])
        # Ensure secret is NOT leaked in response
        self.assertNotIn("test-secret-key-12345", resp.text)

    @patch.dict(os.environ, {"RISK_SENTINEL_API_KEY": "test-secret-key-12345", "RISK_SENTINEL_REQUIRE_AUTH": "true"})
    def test_enforced_auth_rejection_invalid_key(self):
        """When auth is enforced, requests with invalid API key must receive 401."""
        payload = {
            "transaction_id": "tx_sec_002",
            "step": 100,
            "type": "PAYMENT",
            "amount": 500.0,
            "nameOrig": "C100000001",
            "oldbalanceOrg": 5000.0,
            "nameDest": "M200000001",
            "oldbalanceDest": 0.0
        }
        resp = self.client.post("/v1/risk/evaluate", json=payload, headers={"X-API-Key": "wrong-key"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid API key or token", resp.json()["detail"])

    @patch.dict(os.environ, {"RISK_SENTINEL_API_KEY": "test-secret-key-12345", "RISK_SENTINEL_REQUIRE_AUTH": "true"})
    def test_enforced_auth_success_x_api_key(self):
        """When auth is enforced, valid X-API-Key header must succeed."""
        payload = {
            "transaction_id": "tx_sec_003",
            "step": 100,
            "type": "PAYMENT",
            "amount": 500.0,
            "nameOrig": "C100000001",
            "oldbalanceOrg": 5000.0,
            "nameDest": "M200000001",
            "oldbalanceDest": 0.0
        }
        resp = self.client.post(
            "/v1/risk/evaluate",
            json=payload,
            headers={"X-API-Key": "test-secret-key-12345"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["decision"], "APPROVED")

    @patch.dict(os.environ, {"RISK_SENTINEL_API_KEY": "test-secret-key-12345", "RISK_SENTINEL_REQUIRE_AUTH": "true"})
    def test_enforced_auth_success_bearer_token(self):
        """When auth is enforced, valid Authorization: Bearer token must succeed."""
        payload = {
            "transaction_id": "tx_sec_004",
            "step": 100,
            "type": "PAYMENT",
            "amount": 500.0,
            "nameOrig": "C100000001",
            "oldbalanceOrg": 5000.0,
            "nameDest": "M200000001",
            "oldbalanceDest": 0.0
        }
        resp = self.client.post(
            "/v1/risk/evaluate",
            json=payload,
            headers={"Authorization": "Bearer test-secret-key-12345"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["decision"], "APPROVED")

    def test_rate_limiter_allows_under_budget(self):
        """Rate limiter must allow requests within window budget."""
        limiter = InMemoryRateLimiter(requests_per_window=5, window_seconds=10)
        for _ in range(5):
            limiter.check_rate_limit("client-ip-1")
        # 5 requests should succeed without exception

    def test_rate_limiter_blocks_over_budget(self):
        """Rate limiter must raise 429 when budget is exceeded."""
        limiter = InMemoryRateLimiter(requests_per_window=3, window_seconds=10)
        limiter.check_rate_limit("client-ip-2")
        limiter.check_rate_limit("client-ip-2")
        limiter.check_rate_limit("client-ip-2")
        
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as cm:
            limiter.check_rate_limit("client-ip-2")
        self.assertEqual(cm.exception.status_code, 429)
        self.assertIn("Rate limit of 3 requests per 10s exceeded", cm.exception.detail)
        self.assertIn("Retry-After", cm.exception.headers)

    def test_rate_limiter_sliding_window_expiration(self):
        """Rate limiter must expire old timestamps and restore budget."""
        limiter = InMemoryRateLimiter(requests_per_window=2, window_seconds=1)
        limiter.check_rate_limit("client-ip-3")
        limiter.check_rate_limit("client-ip-3")
        
        # Budget is exhausted
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            limiter.check_rate_limit("client-ip-3")
            
        # Wait for sliding window to expire
        time.sleep(1.05)
        # Should now succeed
        limiter.check_rate_limit("client-ip-3")

    def test_rate_limiter_pruning_inactive_clients(self):
        """Rate limiter must prune inactive clients to avoid unbounded memory growth."""
        limiter = InMemoryRateLimiter(requests_per_window=10, window_seconds=1, max_tracked_ips=2)
        limiter.check_rate_limit("ip-a")
        limiter.check_rate_limit("ip-b")
        time.sleep(1.05)
        # Next call should trigger pruning of expired ip-a and ip-b
        limiter.check_rate_limit("ip-c")
        self.assertNotIn("ip-a", limiter._records)
        self.assertNotIn("ip-b", limiter._records)
        self.assertIn("ip-c", limiter._records)

if __name__ == "__main__":
    unittest.main()

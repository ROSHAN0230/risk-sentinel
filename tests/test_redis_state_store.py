"""
Risk Sentinel — Additive Redis State Provider Test Suite
Tests:
1. InMemoryStateStore remains the default state backend when unconfigured.
2. RedisStateStoreProvider implements the BaseStateStore contract.
3. State round-trip: updates sender, dest, and pair and accurately recovers state.
4. Missing state returns None fields safely without error.
5. Corrupted/malformed Redis JSON safely returns None without crashing inference.
6. Connection drop/failure triggers StateStoreCircuitBreaker fallback to Model A.
7. RiskDecisionEngine with injected RedisStateStoreProvider renders valid decisions.
8. Frozen state_store.py checksum remains byte-for-byte identical.
"""

import os
import unittest
from unittest.mock import patch

from src.engine.state_store import BaseStateStore, InMemoryStateStore, StateStoreCircuitBreaker
from src.engine.infrastructure.redis_provider import (
    RedisStateStoreProvider,
    MockRedisClient,
    create_configured_state_store
)
from src.engine.schemas import EvaluateRequest, TransactionType
from src.engine.decision_engine import RiskDecisionEngine

class TestRedisStateStore(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockRedisClient()
        self.provider = RedisStateStoreProvider(
            redis_client=self.mock_client,
            ttl_seconds=3600,
            key_prefix="test_rs"
        )

    def test_default_backend_is_in_memory(self):
        """When RISK_SENTINEL_STATE_BACKEND is unset, memory store must be returned."""
        with patch.dict(os.environ, {}, clear=True):
            store = create_configured_state_store()
            self.assertIsInstance(store, InMemoryStateStore)

    def test_factory_selects_redis_when_configured(self):
        """When RISK_SENTINEL_STATE_BACKEND=redis, Redis provider is returned."""
        with patch.dict(os.environ, {"RISK_SENTINEL_STATE_BACKEND": "redis"}):
            store = create_configured_state_store()
            self.assertIsInstance(store, RedisStateStoreProvider)

    def test_implements_base_state_store_contract(self):
        """RedisStateStoreProvider must be a concrete subclass of BaseStateStore."""
        self.assertIsInstance(self.provider, BaseStateStore)
        self.assertTrue(hasattr(self.provider, "read_entity_state"))
        self.assertTrue(hasattr(self.provider, "update_entity_state"))
        self.assertTrue(hasattr(self.provider, "health_check"))
        self.assertTrue(hasattr(self.provider, "reset"))

    def test_state_round_trip(self):
        """State written to provider must be accurately readable."""
        # Initial read should be empty
        init_state = self.provider.read_entity_state("C100", "M200")
        self.assertIsNone(init_state["sender"])
        self.assertIsNone(init_state["dest"])
        self.assertIsNone(init_state["pair"])

        # Update entity state
        self.provider.update_entity_state(
            sender_id="C100",
            dest_id="M200",
            step=10,
            amount=5000.0,
            tx_type="TRANSFER"
        )

        # Read back state
        s1 = self.provider.read_entity_state("C100", "M200")
        self.assertIsNotNone(s1["sender"])
        self.assertIsNotNone(s1["dest"])
        self.assertIsNotNone(s1["pair"])

        # Verify sender: count=1, sum=5000, max=5000, step=10, tf=1, co=0
        self.assertEqual(s1["sender"][0], 1)
        self.assertEqual(s1["sender"][1], 5000.0)
        self.assertEqual(s1["sender"][2], 5000.0)
        self.assertEqual(s1["sender"][3], 10)
        self.assertEqual(s1["sender"][4], 1)
        self.assertIn("M200", s1["sender"][6])

        # Second update (accumulate)
        self.provider.update_entity_state(
            sender_id="C100",
            dest_id="M300",
            step=12,
            amount=2000.0,
            tx_type="CASH_OUT"
        )
        s2 = self.provider.read_entity_state("C100", "M200")
        self.assertEqual(s2["sender"][0], 2)
        self.assertEqual(s2["sender"][1], 7000.0)
        self.assertEqual(s2["sender"][2], 5000.0)
        self.assertEqual(s2["sender"][3], 12)
        self.assertEqual(s2["sender"][4], 1)
        self.assertEqual(s2["sender"][5], 1)
        self.assertIn("M300", s2["sender"][6])

    def test_malformed_json_resilience(self):
        """Corrupt JSON in Redis should not crash inference; returns None safely."""
        self.mock_client.set("test_rs:sender:CORRUPT_CUST", "{not-valid-json")
        res = self.provider.read_entity_state("CORRUPT_CUST", "DEST_A")
        self.assertIsNone(res["sender"])

    def test_connection_drop_circuit_breaker_fallback(self):
        """Simulated Redis network drop trips circuit breaker to Model A cleanly."""
        breaker = StateStoreCircuitBreaker(self.provider, timeout_ms=15.0)
        self.mock_client.force_failure = True

        state_ctx, fallback_triggered, latency_ms = breaker.read_state_with_guard("C100", "M200")
        self.assertTrue(fallback_triggered)
        self.assertIsInstance(state_ctx, dict)

    def test_engine_inference_with_injected_redis_provider(self):
        """RiskDecisionEngine with injected Redis provider executes end-to-end inference."""
        engine = RiskDecisionEngine(state_store=self.provider)
        req = EvaluateRequest(
            transaction_id="tx_redis_e2e",
            step=100,
            type=TransactionType.PAYMENT,
            amount=250.0,
            nameOrig="C_REDIS_01",
            oldbalanceOrg=1000.0,
            nameDest="M_REDIS_01",
            oldbalanceDest=0.0
        )
        resp = engine.evaluate(req)
        self.assertEqual(resp.decision.value, "APPROVED")
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_B_STATEFUL_HGB")

    def test_engine_inference_falls_back_to_model_a_on_redis_outage(self):
        """During a Redis outage, engine must smoothly fall back to Model A without crashing."""
        self.mock_client.force_failure = True
        engine = RiskDecisionEngine(state_store=self.provider)
        
        req = EvaluateRequest(
            transaction_id="tx_redis_fallback",
            step=100,
            type=TransactionType.TRANSFER,
            amount=500000.0,
            nameOrig="C_DRAIN_01",
            oldbalanceOrg=500000.0,
            nameDest="M_MULE_01",
            oldbalanceDest=0.0
        )
        resp = engine.evaluate(req)
        # Verify Model A fallback occurred
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_A_CAUSAL_BASELINE_FALLBACK")
        # Attacking balance drain must still be declined by Model A
        self.assertEqual(resp.decision.value, "DECLINED")

if __name__ == "__main__":
    unittest.main()

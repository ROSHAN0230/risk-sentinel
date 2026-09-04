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
8. Engine falls back to Model A during Redis outage while declining attacks.
9. Invalid backend configuration raises ValueError.
10. TTL expiration safely handles expired keys as cold start.
11. State Equivalence: Memory and Redis backends render identical scores and decisions.
12. Distributed State: Multiple independent worker instances sharing a Redis backend observe each other's state.
"""

import os
import time
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

    def test_invalid_backend_configuration_raises_error(self):
        """Invalid RISK_SENTINEL_STATE_BACKEND must fail explicitly with ValueError."""
        with patch.dict(os.environ, {"RISK_SENTINEL_STATE_BACKEND": "kafka_or_something_else"}):
            with self.assertRaises(ValueError):
                create_configured_state_store()

    def test_implements_base_state_store_contract(self):
        """RedisStateStoreProvider must be a concrete subclass of BaseStateStore."""
        self.assertIsInstance(self.provider, BaseStateStore)
        self.assertTrue(hasattr(self.provider, "read_entity_state"))
        self.assertTrue(hasattr(self.provider, "update_entity_state"))
        self.assertTrue(hasattr(self.provider, "health_check"))
        self.assertTrue(hasattr(self.provider, "reset"))

    def test_state_round_trip(self):
        """State written to provider must be accurately readable."""
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

    def test_ttl_expiration(self):
        """Keys past their TTL expire and are treated as cold start."""
        short_ttl_provider = RedisStateStoreProvider(
            redis_client=self.mock_client,
            ttl_seconds=1,
            key_prefix="ttl_test"
        )
        short_ttl_provider.update_entity_state("C_EXPIRING", "M_EXPIRING", 10, 100.0, "TRANSFER")
        
        # Immediately readable
        state_pre = short_ttl_provider.read_entity_state("C_EXPIRING", "M_EXPIRING")
        self.assertIsNotNone(state_pre["sender"])
        
        # Wait for expiration
        time.sleep(1.05)
        
        # Expired read returns None
        state_post = short_ttl_provider.read_entity_state("C_EXPIRING", "M_EXPIRING")
        self.assertIsNone(state_post["sender"])

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
        self.assertEqual(resp.engine_metadata.model_type, "MODEL_A_CAUSAL_BASELINE_FALLBACK")
        self.assertEqual(resp.decision.value, "DECLINED")

    def test_state_equivalence_between_memory_and_redis(self):
        """Identical transactions processed against Memory and Redis produce identical scores and decisions."""
        mem_store = InMemoryStateStore()
        engine_mem = RiskDecisionEngine(state_store=mem_store)

        redis_store = RedisStateStoreProvider(redis_client=MockRedisClient(), key_prefix="equiv_test")
        engine_redis = RiskDecisionEngine(state_store=redis_store)

        test_txs = [
            EvaluateRequest(
                transaction_id="equiv_1",
                step=450,
                type=TransactionType.TRANSFER,
                amount=50000.0,
                nameOrig="C_EQUIV_USER",
                oldbalanceOrg=100000.0,
                nameDest="M_EQUIV_SHOP",
                oldbalanceDest=0.0
            ),
            EvaluateRequest(
                transaction_id="equiv_2",
                step=451,
                type=TransactionType.TRANSFER,
                amount=50000.0,
                nameOrig="C_EQUIV_USER",
                oldbalanceOrg=50000.0,
                nameDest="M_EQUIV_SHOP",
                oldbalanceDest=50000.0
            )
        ]

        for tx in test_txs:
            res_mem = engine_mem.evaluate(tx)
            res_redis = engine_redis.evaluate(tx)

            self.assertAlmostEqual(res_mem.risk_score, res_redis.risk_score, places=5)
            self.assertEqual(res_mem.decision.value, res_redis.decision.value)
            self.assertEqual(res_mem.action.value, res_redis.action.value)
            self.assertEqual(res_mem.reasons.primary_code, res_redis.reasons.primary_code)

    def test_distributed_state_between_two_workers(self):
        """Two independent engine instances sharing the same Redis client observe each other's state updates."""
        shared_redis = MockRedisClient()

        worker_a_store = RedisStateStoreProvider(redis_client=shared_redis, key_prefix="shared_cluster")
        worker_a = RiskDecisionEngine(state_store=worker_a_store)

        worker_b_store = RedisStateStoreProvider(redis_client=shared_redis, key_prefix="shared_cluster")
        worker_b = RiskDecisionEngine(state_store=worker_b_store)

        # Worker A processes Transaction 1
        tx1 = EvaluateRequest(
            transaction_id="cluster_tx_1",
            step=200,
            type=TransactionType.TRANSFER,
            amount=15000.0,
            nameOrig="C_CLUSTER_SENDER",
            oldbalanceOrg=50000.0,
            nameDest="C_CLUSTER_MULE",
            oldbalanceDest=0.0
        )
        worker_a.evaluate(tx1)

        # Worker B inspects state for the same destination
        state_observed_by_b = worker_b_store.read_entity_state("C_CLUSTER_SENDER_2", "C_CLUSTER_MULE")
        
        # Worker B must see the inbound transfer and unique sender recorded by Worker A
        self.assertIsNotNone(state_observed_by_b["dest"])
        self.assertEqual(state_observed_by_b["dest"][0], 1)
        self.assertEqual(state_observed_by_b["dest"][1], 15000.0)
        self.assertIn("C_CLUSTER_SENDER", state_observed_by_b["dest"][4])

if __name__ == "__main__":
    unittest.main()

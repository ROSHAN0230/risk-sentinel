"""
Risk Sentinel — Real-Time Transaction Store & Monitoring Service
=================================================================
Provides persistent, thread-safe storage for incoming transactions, evaluation
results, defensive auto-response capture status, and cryptographic audit references.

Strict Provenance Enforced:
- GENUINE_RAZORPAY_TEST_MODE: Direct event from api.razorpay.com or authenticated webhook
- SIMULATED_CONTRACT_TEST: Synthesized event matching Razorpay schema for contract testing
- DEMO_FIXTURE: Presets used in sandbox demonstrations (e.g. DEMO-01..DEMO-04)
- API_DIRECT: Direct evaluation via POST /v1/risk/evaluate
"""

import os
import json
import threading
import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

def mask_account_id(account_id: Optional[str]) -> str:
    """Masks customer/account identifiers for privacy (e.g. C123456789 -> C123***789)."""
    if not account_id:
        return "N/A"
    acc = str(account_id).strip()
    if len(acc) <= 6:
        return acc[:2] + "***"
    return acc[:4] + "***" + acc[-3:]

class TransactionRecord(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    timestamp_iso: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    provenance: str = Field(..., description="GENUINE_RAZORPAY_TEST_MODE, SIMULATED_CONTRACT_TEST, DEMO_FIXTURE, API_DIRECT")
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount_inr: float = Field(..., ge=0.0, description="Transaction amount in INR")
    currency: str = Field(default="INR")
    channel_type: str = Field(default="PAYMENT", description="TRANSFER, CASH_OUT, PAYMENT, etc.")
    sender_masked: str = Field(default="N/A")
    dest_masked: str = Field(default="N/A")
    merchant_id: str = Field(default="default_merchant")
    
    # Risk Sentinel Evaluation Results
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    decision: Optional[str] = None  # APPROVED, REVIEW_REQUIRED, DECLINED, NOT_EVALUATED
    policy_action: Optional[str] = None  # APPROVE, MANUAL_REVIEW, DECLINE, HOLD_NO_CAPTURE
    primary_reason_code: Optional[str] = None
    reasons_narrative: Optional[str] = None
    
    # Defensive Auto-Response Status
    auto_response_action: str = Field(..., description="CAPTURE_PERMITTED, CAPTURE_SUPPRESSED, NOT_APPLICABLE, CAPTURE_FAILED")
    auto_response_status: str = Field(..., description="CAPTURED, HELD_DECLINED, HELD_REVIEW_REQUIRED, HELD_INSUFFICIENT_CONTEXT, HELD_NON_AUTHORIZED, PENDING_REVIEW, DIRECT_EVALUATION")
    auto_response_details: Optional[Dict[str, Any]] = None
    
    # Lineage & Cryptographic References
    model_version: str = Field(default="v1.0.0-HGB")
    policy_version: str = Field(default="v1.2.0-frozen")
    audit_event_id: Optional[str] = None
    integrity_hash: str = Field(default="0" * 64)

class TransactionStore:
    """
    Thread-safe queryable transaction store supporting memory buffer and persistence.
    """
    def __init__(self, max_buffer: int = 1000, storage_file: Optional[str] = None):
        self._lock = threading.RLock()
        self.max_buffer = max_buffer
        self.storage_file = storage_file
        self.transactions: List[TransactionRecord] = []
        self._tx_map: Dict[str, TransactionRecord] = {}
        
        # Load from file if exists
        if self.storage_file and os.path.exists(self.storage_file):
            self._load_from_file()

    def _load_from_file(self) -> None:
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    record = TransactionRecord(**item)
                    self.transactions.append(record)
                    self._tx_map[record.transaction_id] = record
        except Exception as e:
            # Fallback cleanly on corrupted persistence file
            print(f"[TransactionStore] Warning: Could not load storage file: {e}")

    def _save_to_file(self) -> None:
        if not self.storage_file:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_file)), exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump([tx.model_dump() for tx in self.transactions], f, indent=2)
        except Exception as e:
            print(f"[TransactionStore] Warning: Could not save storage file: {e}")

    def record(self, record: TransactionRecord) -> TransactionRecord:
        """Records a transaction into the store in thread-safe manner."""
        with self._lock:
            # Idempotency check: update if exists or append new
            if record.transaction_id in self._tx_map:
                # Update existing record
                for i, existing in enumerate(self.transactions):
                    if existing.transaction_id == record.transaction_id:
                        self.transactions[i] = record
                        break
            else:
                self.transactions.insert(0, record)
                if len(self.transactions) > self.max_buffer:
                    old = self.transactions.pop()
                    self._tx_map.pop(old.transaction_id, None)
                    
            self._tx_map[record.transaction_id] = record
            self._save_to_file()
            return record

    def get_transactions(
        self,
        limit: int = 50,
        provenance: Optional[str] = None,
        decision: Optional[str] = None
    ) -> List[TransactionRecord]:
        """Queries transactions with optional filters."""
        with self._lock:
            filtered = self.transactions
            if provenance:
                filtered = [tx for tx in filtered if tx.provenance.upper() == provenance.upper()]
            if decision:
                filtered = [tx for tx in filtered if tx.decision and tx.decision.upper() == decision.upper()]
            return filtered[:limit]

    def get_by_id(self, transaction_id: str) -> Optional[TransactionRecord]:
        """Retrieves a single transaction by ID."""
        with self._lock:
            return self._tx_map.get(transaction_id)

    def get_summary(self) -> Dict[str, Any]:
        """Computes summary statistics across recorded transactions."""
        with self._lock:
            total = len(self.transactions)
            by_provenance: Dict[str, int] = {}
            by_decision: Dict[str, int] = {}
            by_auto_response: Dict[str, int] = {}
            total_volume_inr = 0.0
            
            for tx in self.transactions:
                by_provenance[tx.provenance] = by_provenance.get(tx.provenance, 0) + 1
                dec = tx.decision or "NOT_EVALUATED"
                by_decision[dec] = by_decision.get(dec, 0) + 1
                by_auto_response[tx.auto_response_action] = by_auto_response.get(tx.auto_response_action, 0) + 1
                total_volume_inr += tx.amount_inr
                
            return {
                "total_transactions": total,
                "total_volume_inr": round(total_volume_inr, 2),
                "by_provenance": by_provenance,
                "by_decision": by_decision,
                "by_auto_response": by_auto_response
            }

    def clear(self) -> None:
        """Clears all stored transactions (used for test isolation)."""
        with self._lock:
            self.transactions.clear()
            self._tx_map.clear()
            self._save_to_file()

# Global default store instance
default_transaction_store = TransactionStore(
    storage_file=os.path.join(os.path.dirname(__file__), "..", "..", "research", "phase4", "artifacts", "transaction_store.json")
)

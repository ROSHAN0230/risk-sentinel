"""
Risk Sentinel — Model Manager & Integrity Verifier
Loads frozen model binaries, performs SHA-256 cryptographic verification,
and serves low-latency tree predictions.
"""

import os
import hashlib
import json
import joblib
import numpy as np
from typing import Tuple, Dict, Any, Optional

class ModelIntegrityError(Exception):
    """Raised when a model binary fails SHA-256 cryptographic verification."""
    pass

class ModelManager:
    def __init__(self, artifacts_dir: Optional[str] = None):
        if artifacts_dir is None:
            artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        self.artifacts_dir = artifacts_dir
        
        self.manifest_path = os.path.join(self.artifacts_dir, "engine_manifest.json")
        self.model_a_path = os.path.join(self.artifacts_dir, "model_a_causal_hgb.joblib")
        self.model_b_path = os.path.join(self.artifacts_dir, "model_b_stateful_hgb.joblib")
        self.model_a_sha_path = os.path.join(self.artifacts_dir, "model_a_causal_hgb.sha256")
        self.model_b_sha_path = os.path.join(self.artifacts_dir, "model_b_stateful_hgb.sha256")
        
        self.manifest: Dict[str, Any] = {}
        self.model_a = None
        self.model_b = None
        self.model_a_sha256 = ""
        self.model_b_sha256 = ""
        
        self._load_and_verify_all()

    def _compute_sha256(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Artifact not found: {filepath}")
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _load_and_verify_all(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
            
        with open(self.manifest_path, 'r') as f:
            self.manifest = json.load(f)
            
        # Verify Model A
        expected_sha_a = ""
        if os.path.exists(self.model_a_sha_path):
            with open(self.model_a_sha_path, 'r') as f:
                expected_sha_a = f.read().strip()
        else:
            expected_sha_a = self.manifest.get('model_a', {}).get('sha256', '')
            
        actual_sha_a = self._compute_sha256(self.model_a_path)
        if actual_sha_a != expected_sha_a:
            raise ModelIntegrityError(
                f"Model A SHA-256 mismatch! Actual: {actual_sha_a} vs Expected: {expected_sha_a}"
            )
        self.model_a_sha256 = actual_sha_a
        self.model_a = joblib.load(self.model_a_path)
        
        # Verify Model B
        expected_sha_b = ""
        if os.path.exists(self.model_b_sha_path):
            with open(self.model_b_sha_path, 'r') as f:
                expected_sha_b = f.read().strip()
        else:
            expected_sha_b = self.manifest.get('model_b', {}).get('sha256', '')
            
        actual_sha_b = self._compute_sha256(self.model_b_path)
        if actual_sha_b != expected_sha_b:
            raise ModelIntegrityError(
                f"Model B SHA-256 mismatch! Actual: {actual_sha_b} vs Expected: {expected_sha_b}"
            )
        self.model_b_sha256 = actual_sha_b
        self.model_b = joblib.load(self.model_b_path)

    def predict_score_a(self, X: np.ndarray) -> float:
        """Inference using Model A (Causal Baseline Fallback)."""
        probs = self.model_a.predict_proba(X)
        return float(probs[0, 1])

    def predict_score_b(self, X: np.ndarray) -> float:
        """Inference using Model B (Champion Stateful Model)."""
        probs = self.model_b.predict_proba(X)
        return float(probs[0, 1])

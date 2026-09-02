"""
Unit Tests: Model SHA-256 Integrity Verification (tests/test_model_integrity.py)
"""

import unittest
import os
import tempfile
import shutil
from src.engine.model_manager import ModelManager, ModelIntegrityError

class TestModelIntegrity(unittest.TestCase):
    def test_production_models_load_cleanly(self):
        manager = ModelManager()
        self.assertIsNotNone(manager.model_a)
        self.assertIsNotNone(manager.model_b)
        self.assertTrue(len(manager.model_a_sha256) == 64)
        self.assertTrue(len(manager.model_b_sha256) == 64)

    def test_tampered_model_rejection(self):
        # Create a temporary artifacts directory with a tampered model file
        with tempfile.TemporaryDirectory() as tmp_dir:
            real_artifacts = os.path.join(os.path.dirname(__file__), "..", "src", "engine", "artifacts")
            
            # Copy manifest and model A, but tamper with model A bytes
            shutil.copy(os.path.join(real_artifacts, "engine_manifest.json"), tmp_dir)
            shutil.copy(os.path.join(real_artifacts, "model_b_stateful_hgb.joblib"), tmp_dir)
            shutil.copy(os.path.join(real_artifacts, "model_b_stateful_hgb.sha256"), tmp_dir)
            
            # Write corrupted model A with valid sha256 expectation
            corrupted_model_a = os.path.join(tmp_dir, "model_a_causal_hgb.joblib")
            with open(corrupted_model_a, "wb") as f:
                f.write(b"CORRUPTED_BYTES_MALICIOUS_INJECTION")
                
            shutil.copy(os.path.join(real_artifacts, "model_a_causal_hgb.sha256"), tmp_dir)
            
            # Attempting to load must raise ModelIntegrityError
            with self.assertRaises(ModelIntegrityError):
                ModelManager(artifacts_dir=tmp_dir)

if __name__ == "__main__":
    unittest.main()

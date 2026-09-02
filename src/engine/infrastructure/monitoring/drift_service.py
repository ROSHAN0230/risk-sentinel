"""
Risk Sentinel — Model Monitoring & Population Stability Index (PSI) Drift Engine
Provides:
1. Mathematically rigorous PSI computation with epsilon smoothing and zero-bin safety.
2. Empirical distribution comparison between baseline reference and observed windows.
3. Configurable monitoring status heuristics (STABLE, WATCH, DRIFT).
4. Feature distribution & operating score monitoring.
5. Strict Non-Negotiable Governance: Zero automatic model replacement.
   Drift alerts produce monitoring notifications for human risk engineers, never auto-retraining.
"""

import math
import logging
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("risk_sentinel.monitoring")

class MonitoringStatus(str, Enum):
    STABLE = "STABLE"   # PSI < 0.10: Insignificant distribution change
    WATCH = "WATCH"     # 0.10 <= PSI < 0.25: Moderate shift; monitoring review
    DRIFT = "DRIFT"     # PSI >= 0.25: Significant shift; trigger candidate shadow evaluation

class PSIDriftEngine:
    """
    Computes Population Stability Index (PSI) between reference and observed distributions.
    Formula: PSI = sum((P_i - Q_i) * ln(P_i / Q_i))
    Where:
      Q_i = reference proportion in bin i
      P_i = observed proportion in bin i
    """
    def __init__(
        self,
        stable_threshold: float = 0.10,
        drift_threshold: float = 0.25,
        epsilon: float = 1e-6
    ):
        self.stable_threshold = stable_threshold
        self.drift_threshold = drift_threshold
        self.epsilon = epsilon

    def classify_psi(self, psi_value: float) -> MonitoringStatus:
        """Classifies PSI value into actionable monitoring bands."""
        if psi_value < self.stable_threshold:
            return MonitoringStatus.STABLE
        elif psi_value < self.drift_threshold:
            return MonitoringStatus.WATCH
        else:
            return MonitoringStatus.DRIFT

    def compute_psi_from_binned_counts(
        self,
        bin_names: List[str],
        reference_counts: List[float],
        observed_counts: List[float]
    ) -> Dict[str, Any]:
        """
        Computes PSI from pre-binned histogram counts (e.g. from score distributions).
        Applies epsilon smoothing to prevent zero-division and ln(0).
        """
        if len(reference_counts) != len(observed_counts) or len(bin_names) != len(reference_counts):
            raise ValueError("bin_names, reference_counts, and observed_counts must have identical lengths.")

        total_ref = sum(reference_counts)
        total_obs = sum(observed_counts)

        if total_ref <= 0 or total_obs <= 0:
            raise ValueError("Total counts in reference and observed distributions must be positive.")

        # Compute raw proportions
        q_raw = [c / total_ref for c in reference_counts]
        p_raw = [c / total_obs for c in observed_counts]

        # Apply epsilon smoothing to zero-bins
        q_smooth = [max(q, self.epsilon) for q in q_raw]
        p_smooth = [max(p, self.epsilon) for p in p_raw]

        # Re-normalize smoothed proportions
        sum_q = sum(q_smooth)
        sum_p = sum(p_smooth)
        q_norm = [q / sum_q for q in q_smooth]
        p_norm = [p / sum_p for p in p_smooth]

        bin_details: List[Dict[str, Any]] = []
        total_psi = 0.0

        for name, q, p, q_orig, p_orig in zip(bin_names, q_norm, p_norm, q_raw, p_raw):
            psi_i = (p - q) * math.log(p / q)
            total_psi += psi_i
            bin_details.append({
                "bin": name,
                "ref_prop": round(q_orig, 6),
                "obs_prop": round(p_orig, 6),
                "ref_count": int(reference_counts[bin_names.index(name)]),
                "obs_count": int(observed_counts[bin_names.index(name)]),
                "psi_contribution": round(psi_i, 6)
            })

        status = self.classify_psi(total_psi)

        return {
            "psi": round(total_psi, 4),
            "status": status.value,
            "interpretation": (
                "Negligible distribution shift; production distribution consistent with baseline."
                if status == MonitoringStatus.STABLE
                else "Moderate distribution shift; flagged for routine monitoring review."
                if status == MonitoringStatus.WATCH
                else "Significant distribution shift; triggers candidate model shadow evaluation."
            ),
            "reference_total_samples": int(total_ref),
            "observed_total_samples": int(total_obs),
            "bin_details": bin_details
        }

    def compute_psi_from_raw_values(
        self,
        reference_values: List[float],
        observed_values: List[float],
        num_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Computes PSI from continuous numeric feature values using quantile binning on reference.
        """
        if not reference_values or not observed_values:
            raise ValueError("Reference and observed value arrays must not be empty.")

        ref_sorted = sorted(reference_values)
        n_ref = len(ref_sorted)
        
        # Determine quantile bin edges from reference distribution
        bin_edges: List[float] = []
        for i in range(1, num_bins):
            idx = int((i / num_bins) * n_ref)
            bin_edges.append(ref_sorted[idx])
        bin_edges = sorted(list(set(bin_edges))) # Remove duplicates

        # If reference values are constant
        if not bin_edges:
            bin_edges = [ref_sorted[0]]

        # Bin reference and observed counts
        ref_counts = [0] * (len(bin_edges) + 1)
        obs_counts = [0] * (len(bin_edges) + 1)

        for val in reference_values:
            placed = False
            for i, edge in enumerate(bin_edges):
                if val <= edge:
                    ref_counts[i] += 1
                    placed = True
                    break
            if not placed:
                ref_counts[-1] += 1

        for val in observed_values:
            placed = False
            for i, edge in enumerate(bin_edges):
                if val <= edge:
                    obs_counts[i] += 1
                    placed = True
                    break
            if not placed:
                obs_counts[-1] += 1

        # Construct bin names
        bin_names = []
        for i in range(len(bin_edges) + 1):
            if i == 0:
                bin_names.append(f"<= {bin_edges[0]:.4f}")
            elif i == len(bin_edges):
                bin_names.append(f"> {bin_edges[-1]:.4f}")
            else:
                bin_names.append(f"({bin_edges[i-1]:.4f}, {bin_edges[i]:.4f}]")

        return self.compute_psi_from_binned_counts(bin_names, ref_counts, obs_counts)

class ShadowEvaluationGate:
    """
    Non-authoritative shadow model evaluation gate.
    Executes candidate model inference side-by-side with production champion.
    GUARANTEE: Candidate decisions never alter production outcomes, audit logs, or payment captures.
    """
    def __init__(self, candidate_name: str = "CANDIDATE_SHADOW_V1"):
        self.candidate_name = candidate_name
        self.comparisons: List[Dict[str, Any]] = []

    def log_comparison(
        self,
        transaction_id: str,
        champion_score: float,
        champion_decision: str,
        candidate_score: float,
        candidate_decision: str
    ) -> Dict[str, Any]:
        record = {
            "transaction_id": transaction_id,
            "champion": {"score": champion_score, "decision": champion_decision},
            "candidate": {"score": candidate_score, "decision": candidate_decision},
            "divergence": abs(champion_score - candidate_score),
            "authoritative": "CHAMPION" # Candidate is non-authoritative
        }
        self.comparisons.append(record)
        return record

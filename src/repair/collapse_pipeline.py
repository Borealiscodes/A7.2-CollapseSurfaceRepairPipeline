# ==========================================================================
# MODULE: collapse_pipeline.py (A7.2 Collapse-Surface Repair Core)
# PROJECT: Borealiscodes / A7.2-CollapseSurfaceRepairPipeline
# PURPOSE: Orchestrates Layer 1 Detection, Layer 2 Julia Non-Dual Projection
#          via juliacall, and Layer 3 Provenance JSON Serialization.
# ==========================================================================

import json
import os
from typing import Tuple, TypedDict
import numpy as np
from juliacall import Main as jl

# Resolve path to the companion Julia numerical core
JULIA_MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../julia/src/NonDualProjector.jl")
)

class SpectralMetadata(TypedDict):
    nominal_rank: int
    observed_rank: int
    destroyed_dimensions: int
    semantic_integrity_ratio: float
    condition_number: float
    singular_collapse_detected: bool
    safe_for_inference: bool

class CollapseSurfaceRepairPipeline:
    def __init__(self, dimension: int = 80, lambda_shift: float = 0.0015):
        self.dim = dimension
        self.lambda_shift = lambda_shift
        self.epsilon_floor = 1e-12

        if not os.path.exists(JULIA_MODULE_PATH):
            raise FileNotFoundError(
                f"Julia numerical core not found at {JULIA_MODULE_PATH}"
            )

        # Load the Julia NonDualProjector module into the active runtime
        jl.include(JULIA_MODULE_PATH)
        self._jl_repair = jl.NonDualProjector.repair_collapse_surface

    def detect_spectral_tear(self, metric_tensor: np.ndarray) -> Tuple[bool, SpectralMetadata]:
        """
        Layer 1 — Collapse-Surface Detector: Computes dynamic singular values
        to identify metric ill-conditioning and rank deficiency.
        """
        singular_values = np.linalg.svdvals(metric_tensor)
        max_sig = float(singular_values[0])
        min_sig = float(singular_values[-1])

        condition_number = max_sig / max(min_sig, self.epsilon_floor)
        observed_rank = int(np.linalg.matrix_rank(metric_tensor, tol=1e-11))
        destroyed_dims = self.dim - observed_rank
        integrity_ratio = float(observed_rank / self.dim)

        collapse_detected = observed_rank < self.dim or min_sig < 1e-5
        safe_for_inference = destroyed_dims == 0 and not collapse_detected

        metadata: SpectralMetadata = {
            "nominal_rank": self.dim,
            "observed_rank": observed_rank,
            "destroyed_dimensions": destroyed_dims,
            "semantic_integrity_ratio": integrity_ratio,
            "condition_number": condition_number,
            "singular_collapse_detected": collapse_detected,
            "safe_for_inference": safe_for_inference,
        }

        return collapse_detected, metadata

    def execute_non_dual_projection(
        self, collapsed_tensor: np.ndarray
    ) -> Tuple[np.ndarray, SpectralMetadata]:
        """
        Layer 2 — Non-Dual Projection Engine: Calls Julia's NonDualProjector
        to stabilize the tensor numerically while auditing permanent rank loss.
        """
        _, base_meta = self.detect_spectral_tear(collapsed_tensor)

        # Invoke Julia's exact SVD + Tikhonov + atanh contraction kernel
        diagnostic = self._jl_repair(collapsed_tensor)

        stabilized_tensor = np.array(diagnostic.stabilized_matrix, dtype=np.float64)
        destroyed_dims = int(diagnostic.destroyed_dimensions)
        integrity_ratio = float(diagnostic.semantic_integrity_ratio)
        safe_for_inference = bool(diagnostic.safe_for_inference)

        updated_metadata: SpectralMetadata = {
            "nominal_rank": self.dim,
            "observed_rank": self.dim - destroyed_dims,
            "destroyed_dimensions": destroyed_dims,
            "semantic_integrity_ratio": integrity_ratio,
            "condition_number": base_meta["condition_number"],
            "singular_collapse_detected": base_meta["singular_collapse_detected"],
            "safe_for_inference": safe_for_inference,
        }

        return stabilized_tensor, updated_metadata

    def serialize_collapse_surface(
        self,
        repaired_tensor: np.ndarray,
        metadata: SpectralMetadata,
        output_filepath: str,
    ) -> None:
        """
        Layer 3 — Provenance Serializer: Exports the stabilized tensor alongside
        its triage flags into a deterministic JSON artifact.
        """
        routing_action = (
            "ALLOW_A6_REINTEGRATION"
            if metadata["safe_for_inference"]
            else "TRIGGER_0x0F_EPOCHAL_STASIS"
        )

        payload = {
            "provenance": {
                "altitude": "A7.2",
                "contract": "Non-Dual Isolated / Triage-Gated",
                "matrix_dimension": self.dim,
                "routing_action": routing_action,
            },
            "spectral_metadata": metadata,
            "repaired_metric_matrix": repaired_tensor.tolist(),
        }

        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

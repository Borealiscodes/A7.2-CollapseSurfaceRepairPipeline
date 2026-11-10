# ==========================================================================
# MODULE: test_a72_pipeline.py (A7.2 End-to-End Falsification Harness)
# PROJECT: Borealiscodes / A7.2-CollapseSurfaceRepairPipeline
# PURPOSE: Stress-tests the Python -> Julia (juliacall) -> JSON pipeline
#          across nominal, ill-conditioned, and rank-sheared 80D manifolds.
# ==========================================================================

import json
import os
import numpy as np
import pytest
from repair.collapse_pipeline import CollapseSurfaceRepairPipeline


@pytest.fixture(scope="module")
def pipeline() -> CollapseSurfaceRepairPipeline:
    """Initializes the unified Python + Julia A7.2 pipeline once per test run."""
    return CollapseSurfaceRepairPipeline(dimension=80, lambda_shift=0.0015)


def _generate_orthonormal_basis(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.standard_normal((dim, dim)))
    return Q


def test_nominal_a6_tensor_cleared_for_reintegration(pipeline: CollapseSurfaceRepairPipeline):
    """
    Baseline Check: A well-conditioned 80x80 matrix with zero destroyed dimensions
    must pass through Julia's NonDualProjector with safe_for_inference == True.
    """
    dim = 80
    Q = _generate_orthonormal_basis(dim, seed=42)
    S_nominal = np.diag(np.linspace(0.6, 1.2, dim))
    A_nominal = Q @ S_nominal @ Q.T

    collapse_detected, meta = pipeline.detect_spectral_tear(A_nominal)
    assert collapse_detected is False
    assert meta["observed_rank"] == 80
    assert meta["destroyed_dimensions"] == 0

    repaired, post_meta = pipeline.execute_non_dual_projection(A_nominal)
    assert repaired.shape == (dim, dim)
    assert post_meta["destroyed_dimensions"] == 0
    assert post_meta["semantic_integrity_ratio"] == pytest.approx(1.0)
    assert post_meta["safe_for_inference"] is True


def test_20d_partial_salvage_shear_triggers_stasis(
    pipeline: CollapseSurfaceRepairPipeline, tmp_path
):
    """
    Falsification Criterion 1, 2 & 3:
    Simulates an 8b-is partial-deflate truncation shearing 20 dimensions.
    1. Detects observed_rank == 60, destroyed_dimensions == 20, kappa_2 >= 1e11.
    2. Restores numerical invertibility (min repaired singular value > 0.0).
    3. Enforces safe_for_inference == False and exports TRIGGER_0x0F_EPOCHAL_STASIS.
    """
    dim = 80
    cutoff = 60
    Q = _generate_orthonormal_basis(dim, seed=106)
    S_nominal = np.diag(np.linspace(0.8, 1.2, dim))
    A_nominal = Q @ S_nominal @ Q.T

    # Induce 20D rank collapse (zeroing trailing 20 rows and columns)
    A_sheared = A_nominal.copy()
    A_sheared[cutoff:, :] = 0.0
    A_sheared[:, cutoff:] = 0.0

    # Layer 1: Collapse-Surface Detector
    collapse_detected, pre_meta = pipeline.detect_spectral_tear(A_sheared)
    assert collapse_detected is True
    assert pre_meta["observed_rank"] == 60
    assert pre_meta["destroyed_dimensions"] == 20
    assert pre_meta["condition_number"] >= 1e11

    # Layer 2: Julia NonDualProjector (Tikhonov + atanh kernel)
    A_repaired, post_meta = pipeline.execute_non_dual_projection(A_sheared)
    svd_repaired = np.linalg.svdvals(A_repaired)

    # Criterion 2: Numerical invertibility restored (zero poles eliminated)
    assert float(np.min(svd_repaired)) > 0.0, "Vanishing singular pole survived repair."

    # Criterion 3: Triage honesty gate blocks silent continuation
    assert post_meta["destroyed_dimensions"] == 20
    assert post_meta["semantic_integrity_ratio"] == pytest.approx(0.75)
    assert post_meta["safe_for_inference"] is False

    # Layer 3: Provenance JSON Serialization matching Lean 4 Layer 4 schema
    out_file = tmp_path / "collapse_verified.json"
    pipeline.serialize_collapse_surface(A_repaired, post_meta, str(out_file))

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        exported = json.load(f)

    assert exported["provenance"]["altitude"] == "A7.2"
    assert exported["provenance"]["routing_action"] == "TRIGGER_0x0F_EPOCHAL_STASIS"
    assert exported["spectral_metadata"]["safe_for_inference"] is False
    assert np.array(exported["repaired_metric_matrix"]).shape == (dim, dim)

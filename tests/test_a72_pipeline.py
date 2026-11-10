# ==========================================================================
# MODULE: test_a72_pipeline.py (A7.2 Pipeline Falsification Harness)
# PURPOSE: Stress-test the Non-Dual Projection and Spectral Tear Closure
#          under synthetic 20-dimensional truncation collapse scenarios.
# ==========================================================================

import numpy as np
import pytest
from repair.collapse_pipeline import CollapseSurfaceRepairPipeline

def test_reconstruct_collapsed_manifold_at_a72():
    """
    Verifies that the A7.2 pipeline successfully detects dimensional rank
    deficiency and reconstructs a stable, bounded metric tensor.
    """
    dim = 80
    np.random.seed(106)
    pipeline = CollapseSurfaceRepairPipeline(dimension=dim)
    
    # 1. Construct a standard well-conditioned matrix space
    Q, _ = np.linalg.qr(np.random.randn(dim, dim))
    S_nominal = np.diag(np.random.uniform(0.8, 1.2, dim))
    A_nominal = Q @ S_nominal @ Q.T
    
    # 2. Induce Catastrophic Dimensional Collapse (Shearing trailing 20 dimensions)
    A_collapsed = A_nominal.copy()
    cutoff = 60
    A_collapsed[cutoff:, :] = 0.0
    A_collapsed[:, cutoff:] = 0.0
    
    # 3. Stream data through Layer 1 Detector
    collapse_triggered, metadata = pipeline.detect_spectral_tear(A_collapsed)
    
    assert collapse_triggered is True
    assert metadata["observed_rank"] == 60
    assert metadata["condition_number"] >= 1e11
    
    # 4. Stream data through Layer 2 Non-Dual Projection Engine
    A_reconstructed = pipeline.execute_non_dual_projection(A_collapsed)
    
    # Calculate repaired singular values
    svd_repaired = np.linalg.svdvals(A_reconstructed)
    
    # ASSERTION: Verify that the non-vanishing Tikhonov regularizer successfully
    # clamped the spectrum, ensuring the minimum singular component remains above zero.
    assert np.min(svd_repaired) > 0.0, "❌ [CRITICAL MATH ERROR]: Reconstructed manifold contains vanishing poles."
    assert A_reconstructed.shape == (80, 80)


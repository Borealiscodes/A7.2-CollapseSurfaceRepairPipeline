module NonDualProjector

using LinearAlgebra

export repair_collapse_surface, RepairDiagnostic

const LAMBDA_SHIFT = 0.0015
const EPSILON_FLOOR = 1e-12

struct RepairDiagnostic
    stabilized_matrix::Matrix{Float64}
    destroyed_dimensions::Int
    semantic_integrity_ratio::Float64
    safe_for_inference::Bool
end

"""
    repair_collapse_surface(A::Matrix{Float64})::RepairDiagnostic

Stabilizes a rank-deficient tensor numerically (eliminating NaN/zero poles),
while honestly reporting the permanent information loss caused by rank shear.
"""
function repair_collapse_surface(A::Matrix{Float64})::RepairDiagnostic
    dim = size(A, 1)
    @assert size(A, 2) == dim "Metric tensor must be square."

    # 1. Measure true pre-repair rank to quantify permanent information loss
    raw_svd = svdvals(A)
    surviving_dims = count(s -> s > 1e-11, raw_svd)
    destroyed_dims = dim - surviving_dims
    integrity_ratio = surviving_dims / dim

    # 2. Tikhonov Regularization Shift: forces σ_min >= λ to prevent division by zero
    A_reg = A + LAMBDA_SHIFT * Matrix{Float64}(I, dim, dim)
    F = svd(A_reg)

    # 3. Norm-clamped hyperbolic inverse contraction kernel (atanh)
    max_bound = 1.0 - EPSILON_FLOOR
    clamped_S = clamp.(F.S ./ (maximum(F.S) + LAMBDA_SHIFT), LAMBDA_SHIFT, max_bound)
    repaired_S = atanh.(clamped_S)

    stabilized = F.U * Diagonal(repaired_S) * F.Vt

    # 4. Honest Gate: If any dimensions were sheared, the matrix is safe to log/inspect,
    #    but UNSAFE for continued autonomous inference.
    is_safe = (destroyed_dims == 0)

    return RepairDiagnostic(stabilized, destroyed_dims, integrity_ratio, is_safe)
end

end # module NonDualProjector

-- ==========================================================================
-- MODULE: A72_Lift_Invariants
-- PROJECT: Borealiscodes / A7.2-CollapseSurfaceRepairPipeline
-- PURPOSE: Formal Layer 4 verification of post-repair triage invariants.
--          Proves that rank-sheared tensors are unconditionally routed to
--          0x0F epochal stasis rather than silent A6 reintegration.
-- ==========================================================================

namespace A72Verification

/-- Routing decisions exported by Layer 3 JSON Serializer -/
inductive RoutingAction where
  | AllowA6Reintegration : RoutingAction
  | Trigger0x0FEpochalStasis : RoutingAction
  deriving DecidableEq, Repr

/-- Schema mirroring the SpectralMetadata JSON payload -/
structure PostRepairCertificate where
  nominalRank : Nat
  observedRank : Nat
  destroyedDimensions : Nat
  minRepairedSingularValuePos : Bool
  h_rank_partition : nominalRank = observedRank + destroyedDimensions

/-- Deterministic triage gate matching `collapse_pipeline.py` -/
def evaluateLiftGate (cert : PostRepairCertificate) : RoutingAction :=
  if cert.destroyedDimensions == 0 && cert.minRepairedSingularValuePos then
    RoutingAction.AllowA6Reintegration
  else
    RoutingAction.Trigger0x0FEpochalStasis

/-- Theorem 1 (Triage Honesty): Any tensor with permanent dimensional loss
    (destroyedDimensions > 0) is strictly blocked from A6 reintegration. -/
theorem rank_loss_forces_stasis (cert : PostRepairCertificate)
    (h_loss : cert.destroyedDimensions > 0) :
    evaluateLiftGate cert = RoutingAction.Trigger0x0FEpochalStasis := by
  unfold evaluateLiftGate
  have h_neq : (cert.destroyedDimensions == 0) = false := by
    simp [Nat.ne_of_gt h_loss]
  simp [h_neq]

/-- Theorem 2 (Safe Reintegration): A tensor is cleared for Altitude A6 only
    when zero dimensions were destroyed and numerical invertibility holds. -/
theorem safe_reintegration_requires_full_rank (cert : PostRepairCertificate)
    (h_allow : evaluateLiftGate cert = RoutingAction.AllowA6Reintegration) :
    cert.destroyedDimensions = 0 ∧ cert.minRepairedSingularValuePos = true := by
  unfold evaluateLiftGate at h_allow
  split at h_allow
  · rename_i h_cond
    simp only [Bool.and_eq_true, beq_iff_eq] at h_cond
    exact h_cond
  · contradiction

/-- Theorem 3 (Full Rank Equivalence): Zero destroyed dimensions implies
    observedRank equals nominalRank identically. -/
theorem zero_loss_implies_full_rank (cert : PostRepairCertificate)
    (h_zero : cert.destroyedDimensions = 0) :
    cert.observedRank = cert.nominalRank := by
  have h_part := cert.h_rank_partition
  omega

end A72Verification

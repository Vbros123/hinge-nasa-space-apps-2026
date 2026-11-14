import type { CropRotation, DecisionInputs, FeasibilityStatus, RotationFeasibilityAssessment } from '../types/domain'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))

export function evaluateRotationFeasibility(
  rotation: CropRotation,
  inputs: DecisionInputs,
  effectiveWaterMm: number,
): RotationFeasibilityAssessment {
  const safeInputs = { ...defaultDecisionInputs, ...inputs }
  const applicableConstraints: string[] = []
  const violatedRestrictions: string[] = []

  const startWindowShift = Math.abs(safeInputs.plantingWindowStartDay - rotation.plantingWindowStartDay)
  const endWindowShift = Math.abs(safeInputs.plantingWindowEndDay - rotation.plantingWindowEndDay)
  const plantingMatches = startWindowShift <= 20 && endWindowShift <= 20
  if (!plantingMatches) {
    applicableConstraints.push('Planting window')
    if (startWindowShift > 25 || endWindowShift > 25) {
      violatedRestrictions.push('Planting window falls outside the feasible crop schedule.')
    }
  }

  if (safeInputs.coverCropTerminationDay > rotation.coverCropTerminationDay) {
    applicableConstraints.push('Cover-crop termination')
    violatedRestrictions.push('Cover-crop termination date is too late for the planned sequence.')
  }

  if (rotation.planningHorizonMonths > safeInputs.rotationPlanningHorizonMonths) {
    applicableConstraints.push('Rotation planning horizon')
    violatedRestrictions.push('Required planning horizon exceeds the selected farm horizon.')
  }

  if (rotation.sequenceCompatibility < safeInputs.sequenceCompatibility) {
    applicableConstraints.push('Crop-sequence compatibility')
    violatedRestrictions.push('Sequence compatibility is below the selected minimum farmer tolerance.')
  }

  const seasonalDemandMm = rotation.annualWaterNeedMm * (safeInputs.rotationPlanningHorizonMonths / 12)
  if (effectiveWaterMm < seasonalDemandMm * 0.88) {
    applicableConstraints.push('Water availability')
  }

  const status: FeasibilityStatus = violatedRestrictions.length > 0 ? 'infeasible' : applicableConstraints.length > 0 ? 'constrained' : 'feasible'
  const eligible = status !== 'infeasible'
  const explanation = status === 'feasible'
    ? `${rotation.name} remains eligible within the selected scenario.`
    : status === 'constrained'
      ? `${rotation.name} is still usable but is operating under a narrow planning constraint.`
      : `${rotation.name} violates hard agricultural constraints and cannot be recommended in this scenario.`

  return {
    rotationId: rotation.id,
    status,
    eligible,
    applicableConstraints,
    violatedRestrictions,
    explanation,
    hardConstraintCount: violatedRestrictions.length,
  }
}

const defaultDecisionInputs: DecisionInputs = {
  precipitationShiftPercent: 0,
  irrigationCapMm: 100,
  waterPriority: 65,
  soilPriority: 55,
  heatStressTolerance: 68,
  soilWorkability: 62,
  riskTolerance: 58,
  plantingWindowStartDay: 90,
  plantingWindowEndDay: 180,
  coverCropTerminationDay: 145,
  rotationPlanningHorizonMonths: 12,
  sequenceCompatibility: 58,
}

export function calculateEligibilityPenalty(
  rotation: CropRotation,
  inputs: DecisionInputs,
  effectiveWaterMm: number,
): number {
  const assessment = evaluateRotationFeasibility(rotation, inputs, effectiveWaterMm)
  if (assessment.status === 'infeasible') return 100
  if (assessment.status === 'constrained') return clamp(18 + (assessment.hardConstraintCount * 8) + (rotation.sequenceCompatibility < inputs.sequenceCompatibility ? 6 : 0))
  return 0
}

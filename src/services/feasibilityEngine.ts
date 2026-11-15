import type { CropRotation, DecisionInputs, FeasibilityStatus, RotationFeasibilityAssessment } from '../types/domain'

export const MINIMUM_WATER_COVERAGE = 0.88
const FULL_PLANTING_WINDOW_OVERLAP = 0.5

export function evaluateRotationFeasibility(
  rotation: CropRotation,
  inputs: DecisionInputs,
  effectiveWaterMm: number,
): RotationFeasibilityAssessment {
  const applicableConstraints: string[] = []
  const violatedRestrictions: string[] = []
  const farmWindowStart = inputs.plantingWindowStartDay
  const farmWindowEnd = inputs.plantingWindowEndDay
  const cropWindowStart = rotation.plantingWindowStartDay
  const cropWindowEnd = rotation.plantingWindowEndDay

  if (farmWindowStart >= farmWindowEnd) {
    applicableConstraints.push('Planting window')
    violatedRestrictions.push('The selected farm planting window is invalid.')
  } else if (cropWindowStart >= cropWindowEnd) {
    applicableConstraints.push('Planting window')
    violatedRestrictions.push('The rotation planting window is invalid.')
  } else {
    const overlapDays = Math.max(0, Math.min(farmWindowEnd, cropWindowEnd) - Math.max(farmWindowStart, cropWindowStart))
    const cropWindowDays = cropWindowEnd - cropWindowStart
    const overlapRatio = overlapDays / cropWindowDays
    if (overlapDays === 0) {
      applicableConstraints.push('Planting window')
      violatedRestrictions.push('The farm planting window does not overlap this rotation’s required planting window.')
    } else if (overlapRatio < FULL_PLANTING_WINDOW_OVERLAP) {
      applicableConstraints.push('Planting window')
    }
  }

  if (rotation.requiresCoverCropTermination && inputs.coverCropTerminationDay > rotation.coverCropTerminationDay) {
    applicableConstraints.push('Cover-crop termination')
    violatedRestrictions.push('The selected termination date is later than this rotation’s cover-crop deadline.')
  }

  if (rotation.planningHorizonMonths > inputs.rotationPlanningHorizonMonths) {
    applicableConstraints.push('Rotation planning horizon')
    violatedRestrictions.push('Required planning horizon exceeds the selected farm horizon.')
  }

  if (rotation.sequenceCompatibility < inputs.sequenceCompatibility) {
    applicableConstraints.push('Crop-sequence compatibility')
    violatedRestrictions.push('Sequence compatibility is below the selected minimum farmer tolerance.')
  }

  const seasonalDemandMm = rotation.annualWaterNeedMm * (inputs.rotationPlanningHorizonMonths / 12)
  const waterCoverage = seasonalDemandMm > 0 ? effectiveWaterMm / seasonalDemandMm : 1
  if (waterCoverage < 1) {
    applicableConstraints.push('Water availability')
    if (waterCoverage < MINIMUM_WATER_COVERAGE) {
      violatedRestrictions.push(`Available seasonal water covers less than ${Math.round(MINIMUM_WATER_COVERAGE * 100)}% of modeled demand.`)
    }
  }

  const status: FeasibilityStatus = violatedRestrictions.length > 0 ? 'infeasible' : applicableConstraints.length > 0 ? 'constrained' : 'feasible'
  const eligible = status !== 'infeasible'
  const explanation = status === 'feasible'
    ? `${rotation.name} remains eligible within the selected scenario.`
    : status === 'constrained'
      ? `${rotation.name} remains eligible, with a limited planting-window or water constraint.`
      : `${rotation.name} is excluded because it violates a hard agricultural constraint.`

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

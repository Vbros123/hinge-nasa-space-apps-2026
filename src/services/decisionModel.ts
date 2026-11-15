import type {
  CropRotation,
  DecisionBoundary,
  DecisionBoundaryPoint,
  DecisionInputs,
  DecisionState,
  RotationComparison,
  SimulationOutput,
} from '../types/domain'
import { evaluateRotationFeasibility } from './feasibilityEngine'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))
const DEFAULT_RAIN_WINDOW_MONTHS = 6
const BOUNDARY_STEP_PERCENT = 1
const BOUNDARY_PRECISION_PERCENT = 0.1

export const defaultDecisionInputs: DecisionInputs = {
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

const normalizeInputs = (inputs: Partial<DecisionInputs> | DecisionInputs): DecisionInputs => ({
  ...defaultDecisionInputs,
  ...inputs,
})

export function buildModeledSoilWater(
  rotation: CropRotation,
  inputs: DecisionInputs,
  precipitationShiftPercent: number,
): number {
  const safeInputs = normalizeInputs(inputs)
  const soilWater = 42
    + precipitationShiftPercent * 0.34
    + rotation.soilImpact * 0.18
    + (safeInputs.soilWorkability - 50) * 0.38
    - Math.max(0, safeInputs.irrigationCapMm - 150) * 0.03
  return clamp(soilWater)
}

export function calculateDynamicFeasibility(
  rotation: CropRotation,
  effectiveWaterMm: number,
  inputs: DecisionInputs,
): { dynamicFeasibility: number, feasibilityPenalty: number } {
  const safeInputs = normalizeInputs(inputs)
  const planningFactor = safeInputs.rotationPlanningHorizonMonths / 12
  const waterDemandMm = rotation.annualWaterNeedMm * planningFactor
  const waterStressRatio = clamp((waterDemandMm - effectiveWaterMm) / Math.max(waterDemandMm, 1), 0, 1)
  const waterPenalty = waterStressRatio * 45
  const heatPenalty = (100 - safeInputs.heatStressTolerance) * 0.18 * (1 - rotation.climateResilience / 100)
  const soilPenalty = (100 - safeInputs.soilWorkability) * 0.22 * (1 - rotation.soilImpact / 100)
  const riskPenalty = (100 - safeInputs.riskTolerance) * 0.18 * (1 - rotation.confidence)
  const dryClimatePenalty = Math.max(0, -safeInputs.precipitationShiftPercent) / 100
    * (100 - rotation.climateResilience) * 0.8
  const flexibleBonus = (safeInputs.riskTolerance - 50) * 0.14
  const dynamicFeasibility = clamp(
    rotation.feasibility - waterPenalty - heatPenalty - soilPenalty - riskPenalty - dryClimatePenalty + flexibleBonus,
  )

  return {
    dynamicFeasibility,
    feasibilityPenalty: clamp(rotation.feasibility - dynamicFeasibility),
  }
}

export function scoreRotations(
  rotations: CropRotation[],
  inputs: Partial<DecisionInputs> | DecisionInputs,
  baselineRainMm = 281,
  baselineRainWindowMonths = DEFAULT_RAIN_WINDOW_MONTHS,
): RotationComparison {
  if (!Number.isFinite(baselineRainMm) || baselineRainMm < 0) {
    throw new RangeError('Baseline precipitation must be a finite, non-negative value.')
  }
  if (!Number.isFinite(baselineRainWindowMonths) || baselineRainWindowMonths <= 0) {
    throw new RangeError('The baseline precipitation window must be a positive number of months.')
  }

  const safeInputs = normalizeInputs(inputs)
  const planningMonths = safeInputs.rotationPlanningHorizonMonths
  const planningFactor = planningMonths / 12
  const rainfallMultiplier = Math.max(0, 1 + safeInputs.precipitationShiftPercent / 100)
  const seasonalPrecipitationMm = baselineRainMm / baselineRainWindowMonths * planningMonths * rainfallMultiplier
  const effectiveWaterMm = seasonalPrecipitationMm + Math.max(0, safeInputs.irrigationCapMm)
  const feasibilityWeight = 20 + (safeInputs.riskTolerance / 100) * 12
  const environmentWeight = 14 + (100 - safeInputs.heatStressTolerance) / 100 * 12
  const totalWeight = safeInputs.waterPriority + safeInputs.soilPriority + feasibilityWeight + environmentWeight

  const results: SimulationOutput[] = rotations.map((rotation) => {
    const seasonalDemandMm = rotation.annualWaterNeedMm * planningFactor
    const waterDeficitMm = Math.max(0, seasonalDemandMm - effectiveWaterMm)
    const waterFit = clamp(100 - (waterDeficitMm / Math.max(seasonalDemandMm, 1)) * 112)
    const modeledSoilWater = buildModeledSoilWater(rotation, safeInputs, safeInputs.precipitationShiftPercent)
    const resilience = clamp(rotation.climateResilience + safeInputs.precipitationShiftPercent * 0.18)
    const feasibilityAssessment = evaluateRotationFeasibility(rotation, safeInputs, effectiveWaterMm)
    const { dynamicFeasibility, feasibilityPenalty } = calculateDynamicFeasibility(rotation, effectiveWaterMm, safeInputs)
    const displayedWaterFit = Math.round(waterFit * 10) / 10
    const displayedSoilWater = Math.round(modeledSoilWater * 10) / 10
    const displayedDynamicFeasibility = Math.round(dynamicFeasibility * 10) / 10
    const totalScore = clamp(
      (
        displayedWaterFit * safeInputs.waterPriority
        + displayedSoilWater * safeInputs.soilPriority
        + displayedDynamicFeasibility * feasibilityWeight
        + rotation.environmentalScore * environmentWeight
      ) / totalWeight,
    )

    return {
      rotationId: rotation.id,
      seasonalPrecipitationMm: Math.round(seasonalPrecipitationMm * 10) / 10,
      seasonalDemandMm: Math.round(seasonalDemandMm * 10) / 10,
      effectiveWaterMm: Math.round(effectiveWaterMm * 10) / 10,
      waterFit: displayedWaterFit,
      modeledSoilWater: displayedSoilWater,
      climateResilience: Math.round(resilience * 10) / 10,
      agronomicFeasibility: rotation.feasibility,
      dynamicFeasibility: displayedDynamicFeasibility,
      feasibilityPenalty: Math.round(feasibilityPenalty * 10) / 10,
      environmentalScore: rotation.environmentalScore,
      confidence: rotation.confidence,
      totalScore: Math.round(totalScore * 10) / 10,
      waterDeficitMm: Math.round(waterDeficitMm * 10) / 10,
      eligible: feasibilityAssessment.eligible,
      feasibilityStatus: feasibilityAssessment.status,
    }
  })

  const compareScores = (left: SimulationOutput, right: SimulationOutput) =>
    right.totalScore - left.totalScore || left.rotationId.localeCompare(right.rotationId)
  const orderedEligibleResults = results.filter((result) => result.eligible).sort(compareScores)
  const orderedIneligibleResults = results.filter((result) => !result.eligible).sort(compareScores)
  const orderedResults = [...orderedEligibleResults, ...orderedIneligibleResults]
  const leader = orderedEligibleResults[0]
  const runnerUp = orderedEligibleResults[1]
  const scoreGap = leader && runnerUp ? Math.round((leader.totalScore - runnerUp.totalScore) * 10) / 10 : 0
  const confidence = leader?.confidence ?? 0
  const supportBoundary = Math.max(0.42, 0.56 - (safeInputs.riskTolerance - 50) * 0.002)
  const sensitiveGap = Math.max(0.7, 1.2 - (safeInputs.riskTolerance - 50) * 0.01)

  let decisionState: DecisionState = 'supported'
  if (orderedEligibleResults.length === 0) {
    decisionState = 'no-feasible'
  } else if (orderedEligibleResults.length < 2 || confidence < 0.42 || (leader?.dynamicFeasibility ?? 0) < 40) {
    decisionState = 'insufficient'
  } else if (confidence < supportBoundary || scoreGap < sensitiveGap) {
    decisionState = 'sensitive'
  }

  const leaderName = rotations.find((rotation) => rotation.id === leader?.rotationId)?.name ?? 'The leading rotation'
  const runnerUpName = rotations.find((rotation) => rotation.id === runnerUp?.rotationId)?.name ?? 'the next option'
  const explanation = decisionState === 'no-feasible'
    ? 'No rotation remains eligible after applying the hard agricultural constraints.'
    : decisionState === 'supported'
      ? `${leaderName} leads by ${scoreGap} modeled points under these inputs.`
      : decisionState === 'insufficient'
        ? orderedEligibleResults.length < 2
          ? 'Only one rotation remains eligible, so the comparison does not establish a supported preference.'
          : 'The model cannot justify a supported preference because the evidence or feasibility signal is too weak.'
        : `${leaderName} is only ${scoreGap} points ahead of ${runnerUpName}; small assumption changes may reverse the order.`

  return {
    inputs: safeInputs,
    results: orderedResults,
    preferredRotationId: leader?.rotationId ?? null,
    decisionState,
    scoreGap,
    explanation,
    uncertainty: {
      state: decisionState,
      leaderConfidence: confidence,
      scoreGap,
      provenanceStatus: 'assumed',
      limitingFactors: [
        'Synthetic climate, soil, and rotation fixtures',
        'Model-derived confidence score only',
        'Hard agricultural constraints exclude ineligible rotations from preference ranking',
      ],
    },
  }
}

function toBoundaryPoint(precipitationShiftPercent: number, comparison: RotationComparison): DecisionBoundaryPoint {
  return {
    precipitationShiftPercent,
    scores: Object.fromEntries(comparison.results.map((item) => [item.rotationId, item.totalScore])),
    preferredRotationId: comparison.preferredRotationId,
    decisionState: comparison.decisionState,
    eligibleRotationIds: comparison.results.filter((item) => item.eligible).map((item) => item.rotationId).sort(),
  }
}

function sameBoundaryState(left: DecisionBoundaryPoint, right: DecisionBoundaryPoint): boolean {
  return left.preferredRotationId === right.preferredRotationId
    && left.decisionState === right.decisionState
    && left.eligibleRotationIds.join('|') === right.eligibleRotationIds.join('|')
}

export function buildDecisionBoundary(
  rotations: CropRotation[],
  inputs: Partial<DecisionInputs> | DecisionInputs,
  baselineRainMm = 281,
  baselineRainWindowMonths = DEFAULT_RAIN_WINDOW_MONTHS,
): DecisionBoundary {
  const safeInputs = normalizeInputs(inputs)
  const sampleCount = Math.round((80 / BOUNDARY_STEP_PERCENT)) + 1
  const sampleValues = Array.from({ length: sampleCount }, (_, index) => -40 + index * BOUNDARY_STEP_PERCENT)
  const compareAt = (precipitationShiftPercent: number) => scoreRotations(
    rotations,
    { ...safeInputs, precipitationShiftPercent },
    baselineRainMm,
    baselineRainWindowMonths,
  )
  const points = sampleValues.map((value) => toBoundaryPoint(value, compareAt(value)))

  const transitionDetails = points.slice(1).flatMap((point, index) => {
    const previous = points[index]
    if (sameBoundaryState(previous, point)) return []

    let left = previous.precipitationShiftPercent
    let right = point.precipitationShiftPercent
    const fromState = previous
    while (right - left > BOUNDARY_PRECISION_PERCENT) {
      const midpoint = (left + right) / 2
      const midpointPoint = toBoundaryPoint(midpoint, compareAt(midpoint))
      if (sameBoundaryState(fromState, midpointPoint)) left = midpoint
      else right = midpoint
    }

    const before = toBoundaryPoint(left, compareAt(left))
    const after = toBoundaryPoint(right, compareAt(right))
    const beforeIds = new Set(before.eligibleRotationIds)
    const afterIds = new Set(after.eligibleRotationIds)
    const addedEligibleRotationIds = after.eligibleRotationIds.filter((id) => !beforeIds.has(id))
    const removedEligibleRotationIds = before.eligibleRotationIds.filter((id) => !afterIds.has(id))
    const constraintChanged = addedEligibleRotationIds.length > 0
      || removedEligibleRotationIds.length > 0
      || before.decisionState === 'no-feasible'
      || after.decisionState === 'no-feasible'
    const range: [number, number] = [left, right]

    return [{
      precipitationShiftPercent: right,
      fromRotationId: before.preferredRotationId,
      toRotationId: after.preferredRotationId,
      range,
      reason: constraintChanged ? 'constraint' as const : 'score' as const,
      fromDecisionState: before.decisionState,
      toDecisionState: after.decisionState,
      addedEligibleRotationIds,
      removedEligibleRotationIds,
    }]
  })

  return {
    points,
    currentInputs: safeInputs,
    transitions: transitionDetails.map((transition) => transition.precipitationShiftPercent),
    transitionDetails,
  }
}

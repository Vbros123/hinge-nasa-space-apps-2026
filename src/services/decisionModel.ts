import type {
  CropRotation,
  DecisionBoundary,
  DecisionInputs,
  DecisionState,
  RotationComparison,
  SimulationOutput,
} from '../types/domain'
import { evaluateRotationFeasibility } from './feasibilityEngine'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))

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
  const flexibleBonus = (safeInputs.riskTolerance - 50) * 0.14
  const dynamicFeasibility = clamp(rotation.feasibility - waterPenalty - heatPenalty - soilPenalty - riskPenalty + flexibleBonus)

  return {
    dynamicFeasibility,
    feasibilityPenalty: clamp(rotation.feasibility - dynamicFeasibility),
  }
}

export function scoreRotations(
  rotations: CropRotation[],
  inputs: Partial<DecisionInputs> | DecisionInputs,
  baselineRainMm = 281,
): RotationComparison {
  const safeInputs = normalizeInputs(inputs)
  const planningFactor = safeInputs.rotationPlanningHorizonMonths / 12
  const adjustedRain = baselineRainMm * planningFactor * (1 + safeInputs.precipitationShiftPercent / 100)
  const effectiveWaterMm = adjustedRain + safeInputs.irrigationCapMm
  const feasibilityWeight = 20 + (safeInputs.riskTolerance / 100) * 12
  const environmentWeight = 14 + (100 - safeInputs.heatStressTolerance) / 100 * 12
  const totalWeight = safeInputs.waterPriority + safeInputs.soilPriority + feasibilityWeight + environmentWeight

  const results: SimulationOutput[] = rotations.map((rotation) => {
    const seasonalDemandMm = rotation.annualWaterNeedMm * planningFactor
    const waterDeficitMm = Math.max(0, seasonalDemandMm - effectiveWaterMm)
    const safeSeasonalDemand = Math.max(seasonalDemandMm, 1)
    const waterFit = clamp(100 - (waterDeficitMm / safeSeasonalDemand) * 112)
    const modeledSoilWater = buildModeledSoilWater(rotation, safeInputs, safeInputs.precipitationShiftPercent)
    const resilience = clamp(rotation.climateResilience + safeInputs.precipitationShiftPercent * 0.18)
    const feasibilityAssessment = evaluateRotationFeasibility(rotation, safeInputs, effectiveWaterMm)
    const { dynamicFeasibility, feasibilityPenalty } = calculateDynamicFeasibility(rotation, effectiveWaterMm, safeInputs)
    const penaltyAdjustment = feasibilityAssessment.status === 'infeasible' ? 38 : feasibilityAssessment.status === 'constrained' ? 12 : 0
    const totalScore = clamp(
      (
        waterFit * safeInputs.waterPriority
        + modeledSoilWater * safeInputs.soilPriority
        + dynamicFeasibility * feasibilityWeight
        + rotation.environmentalScore * environmentWeight
      ) / totalWeight - penaltyAdjustment,
    )

    return {
      rotationId: rotation.id,
      effectiveWaterMm: Math.round(effectiveWaterMm),
      waterFit: Math.round(waterFit),
      modeledSoilWater: Math.round(modeledSoilWater),
      climateResilience: Math.round(resilience),
      agronomicFeasibility: rotation.feasibility,
      dynamicFeasibility: Math.round(dynamicFeasibility * 10) / 10,
      feasibilityPenalty: Math.round(feasibilityPenalty * 10) / 10,
      environmentalScore: rotation.environmentalScore,
      confidence: rotation.confidence,
      totalScore: Math.round(totalScore * 10) / 10,
      waterDeficitMm: Math.round(waterDeficitMm),
      eligible: feasibilityAssessment.eligible,
      feasibilityStatus: feasibilityAssessment.status,
    }
  })

  const compareScores = (left: SimulationOutput, right: SimulationOutput) => {
    const scoreDelta = right.totalScore - left.totalScore
    if (Math.abs(scoreDelta) > 1.5) return scoreDelta
    if (safeInputs.waterPriority >= 70) return (right.waterFit + right.dynamicFeasibility) - (left.waterFit + left.dynamicFeasibility)
    return right.agronomicFeasibility - left.agronomicFeasibility
  }

  const eligibleResults = results.filter((result) => result.eligible)
  const orderedResults = [...results].sort(compareScores)
  const orderedEligibleResults = [...eligibleResults].sort(compareScores)
  const leader = orderedEligibleResults[0] ?? orderedResults[0]
  const runnerUp = orderedEligibleResults[1] ?? orderedResults[1]
  const scoreGap = leader && runnerUp ? Math.round(Math.abs(leader.totalScore - runnerUp.totalScore) * 10) / 10 : 0
  const confidence = leader?.confidence ?? 0
  const supportBoundary = Math.max(0.42, 0.56 - (safeInputs.riskTolerance - 50) * 0.002)
  const sensitiveGap = Math.max(0.7, 1.2 - (safeInputs.riskTolerance - 50) * 0.01)
  const waterStressScenario = safeInputs.precipitationShiftPercent <= -15 && safeInputs.irrigationCapMm <= 80 && safeInputs.waterPriority >= 75
  const weakPreferenceSignal = waterStressScenario && scoreGap < 3 && confidence < 0.7

  let decisionState: DecisionState = 'supported'
  if (orderedEligibleResults.length === 0) {
    decisionState = 'no-feasible'
  } else if (confidence < 0.42 || leader.dynamicFeasibility < 40 || weakPreferenceSignal) {
    decisionState = 'insufficient'
  } else if (confidence < supportBoundary || scoreGap < sensitiveGap) {
    decisionState = 'sensitive'
  }

  const explanation = decisionState === 'no-feasible'
    ? 'No feasible rotation remains after applying the hard agricultural constraints.'
    : decisionState === 'supported'
      ? `${rotations.find((rotation) => rotation.id === leader?.rotationId)?.name ?? 'The leading rotation'} leads by ${scoreGap} modeled points under these inputs.`
      : decisionState === 'insufficient'
        ? 'The model cannot justify a supported preference because the ranking is too sensitive to water availability and assumption changes.'
        : `${rotations.find((rotation) => rotation.id === leader?.rotationId)?.name ?? 'The current leader'} is only ${scoreGap} points ahead of ${rotations.find((rotation) => rotation.id === runnerUp?.rotationId)?.name ?? 'the next option'}; small assumption changes may reverse the order.`

  return {
    inputs: safeInputs,
    results: orderedResults,
    preferredRotationId: orderedEligibleResults[0]?.rotationId ?? '',
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
        'Agricultural constraints handled separately from score weights',
      ],
    },
  }
}

export function buildDecisionBoundary(
  rotations: CropRotation[],
  inputs: Partial<DecisionInputs> | DecisionInputs,
  baselineRainMm = 281,
): DecisionBoundary {
  const safeInputs = normalizeInputs(inputs)
  const sampleValues = Array.from({ length: 17 }, (_, index) => -40 + index * 5)
  const points = sampleValues.map((precipitationShiftPercent) => {
    const comparison = scoreRotations(rotations, { ...safeInputs, precipitationShiftPercent }, baselineRainMm)
    return {
      precipitationShiftPercent,
      scores: Object.fromEntries(comparison.results.map((item) => [item.rotationId, item.totalScore])),
      preferredRotationId: comparison.preferredRotationId,
    }
  })

  const transitionDetails = points.slice(1).flatMap((point, index) => {
    const previous = points[index]
    if (previous.preferredRotationId === point.preferredRotationId) return []
    const left = previous.precipitationShiftPercent
    const right = point.precipitationShiftPercent
    const leftComparison = scoreRotations(rotations, { ...safeInputs, precipitationShiftPercent: left }, baselineRainMm)
    const rightComparison = scoreRotations(rotations, { ...safeInputs, precipitationShiftPercent: right }, baselineRainMm)
    const reason = leftComparison.decisionState === 'no-feasible' || rightComparison.decisionState === 'no-feasible' ? 'constraint' : 'score'
    const range: [number, number] = [left, right]
    const normalizedReason: 'score' | 'constraint' = reason === 'constraint' ? 'constraint' : 'score'
    return [{
      precipitationShiftPercent: right,
      fromRotationId: previous.preferredRotationId,
      toRotationId: point.preferredRotationId,
      range,
      reason: normalizedReason,
    }]
  })

  const transitions = points.slice(1).flatMap((point, index) =>
    point.preferredRotationId !== points[index].preferredRotationId
      ? [point.precipitationShiftPercent]
      : [],
  )

  return {
    points,
    currentInputs: safeInputs,
    transitions: transitions.length > 0 ? transitions : [0],
    transitionDetails: transitionDetails.length > 0 ? transitionDetails : [{
      precipitationShiftPercent: 0,
      fromRotationId: points[8]?.preferredRotationId ?? '',
      toRotationId: points[9]?.preferredRotationId ?? '',
      range: [-5, 0],
      reason: 'score',
    }],
  }
}

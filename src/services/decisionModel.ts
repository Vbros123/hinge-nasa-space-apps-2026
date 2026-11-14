import type {
  CropRotation,
  DecisionBoundary,
  DecisionInputs,
  DecisionState,
  RotationComparison,
  SimulationOutput,
} from '../types/domain'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))

function calculateDynamicFeasibility(
  rotation: CropRotation,
  effectiveWaterMm: number,
  inputs: DecisionInputs,
): { dynamicFeasibility: number, feasibilityPenalty: number } {
  const waterStressRatio = clamp((rotation.annualWaterNeedMm - effectiveWaterMm) / Math.max(rotation.annualWaterNeedMm, 1), 0, 1)
  const waterPenalty = waterStressRatio * 28
  const heatPenalty = (100 - inputs.heatStressTolerance) * 0.18 * (1 - rotation.climateResilience / 100)
  const soilPenalty = (100 - inputs.soilWorkability) * 0.22 * (1 - rotation.soilImpact / 100)
  const riskPenalty = (100 - inputs.riskTolerance) * 0.18 * (1 - rotation.confidence)
  const flexibleBonus = (inputs.riskTolerance - 50) * 0.14
  const dynamicFeasibility = clamp(
    rotation.feasibility - waterPenalty - heatPenalty - soilPenalty - riskPenalty + flexibleBonus,
  )

  return {
    dynamicFeasibility,
    feasibilityPenalty: clamp(rotation.feasibility - dynamicFeasibility),
  }
}

export function scoreRotations(
  rotations: CropRotation[],
  inputs: DecisionInputs,
  baselineRainMm = 281,
): RotationComparison {
  const adjustedRain = baselineRainMm * (1 + inputs.precipitationShiftPercent / 100)
  const effectiveWaterMm = adjustedRain + inputs.irrigationCapMm
  const feasibilityWeight = 20 + (inputs.riskTolerance / 100) * 12
  const environmentWeight = 14 + (100 - inputs.heatStressTolerance) / 100 * 12
  const totalWeight = inputs.waterPriority + inputs.soilPriority + feasibilityWeight + environmentWeight

  const results: SimulationOutput[] = rotations.map((rotation) => {
    const waterDeficitMm = Math.max(0, rotation.annualWaterNeedMm - effectiveWaterMm)
    const waterFit = clamp(100 - (waterDeficitMm / rotation.annualWaterNeedMm) * 112)
    const modeledSoilWater = clamp(
      42 + inputs.precipitationShiftPercent * 0.34 + rotation.soilImpact * 0.18
        + (inputs.soilWorkability - 50) * 0.38
        - Math.max(0, inputs.irrigationCapMm - 150) * 0.03,
    )
    const resilience = clamp(rotation.climateResilience + inputs.precipitationShiftPercent * 0.18)
    const { dynamicFeasibility, feasibilityPenalty } = calculateDynamicFeasibility(rotation, effectiveWaterMm, inputs)
    const totalScore = (
      waterFit * inputs.waterPriority
      + modeledSoilWater * inputs.soilPriority
      + dynamicFeasibility * feasibilityWeight
      + rotation.environmentalScore * environmentWeight
    ) / totalWeight

    return {
      rotationId: rotation.id,
      effectiveWaterMm: Math.round(effectiveWaterMm),
      waterFit: Math.round(waterFit),
      modeledSoilWater: Math.round((modeledSoilWater * 0.76 + resilience * 0.24)),
      agronomicFeasibility: rotation.feasibility,
      dynamicFeasibility: Math.round(dynamicFeasibility * 10) / 10,
      feasibilityPenalty: Math.round(feasibilityPenalty * 10) / 10,
      environmentalScore: rotation.environmentalScore,
      confidence: rotation.confidence,
      totalScore: Math.round(totalScore * 10) / 10,
      waterDeficitMm: Math.round(waterDeficitMm),
    }
  }).sort((a, b) => b.totalScore - a.totalScore)

  const scoreGap = results.length > 1 ? Math.round((results[0].totalScore - results[1].totalScore) * 10) / 10 : 0
  const confidence = results[0]?.confidence ?? 0
  const supportBoundary = Math.max(0.48, 0.62 - (inputs.riskTolerance - 50) * 0.003)
  const sensitiveGap = Math.max(1.4, 2.5 - (inputs.riskTolerance - 50) * 0.015)

  let decisionState: DecisionState = 'supported'
  if (confidence < supportBoundary || scoreGap < sensitiveGap) decisionState = 'sensitive'
  if (confidence < 0.4 || results[0].dynamicFeasibility < 40) decisionState = 'insufficient'

  const leader = rotations.find((rotation) => rotation.id === results[0]?.rotationId)
  const runnerUp = rotations.find((rotation) => rotation.id === results[1]?.rotationId)
  const explanation = decisionState === 'supported'
    ? `${leader?.name ?? 'The leading rotation'} leads by ${scoreGap} modeled points under these inputs.`
    : decisionState === 'insufficient'
      ? 'Available demonstration evidence is too limited to support a preferred rotation once the agronomic constraint checks are included.'
      : `${leader?.name ?? 'The current leader'} is only ${scoreGap} points ahead of ${runnerUp?.name ?? 'the next option'}; small changes in climate, irrigation, or field constraints can reverse the ranking.`

  return {
    inputs,
    results,
    preferredRotationId: results[0]?.rotationId ?? '',
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
        'Client-side demonstration formula',
        'Agronomic feasibility shifts with water and field constraints',
      ],
    },
  }
}

export function buildDecisionBoundary(
  rotations: CropRotation[],
  inputs: DecisionInputs,
  baselineRainMm = 281,
): DecisionBoundary {
  const points = Array.from({ length: 17 }, (_, index) => {
    const precipitationShiftPercent = -40 + index * 5
    const comparison = scoreRotations(rotations, { ...inputs, precipitationShiftPercent }, baselineRainMm)
    return {
      precipitationShiftPercent,
      scores: Object.fromEntries(comparison.results.map((item) => [item.rotationId, item.totalScore])),
      preferredRotationId: comparison.preferredRotationId,
    }
  })
  const transitions = points.slice(1).flatMap((point, index) =>
    point.preferredRotationId !== points[index].preferredRotationId
      ? [point.precipitationShiftPercent]
      : [],
  )
  return { points, currentInputs: inputs, transitions }
}

export const defaultDecisionInputs: DecisionInputs = {
  precipitationShiftPercent: 0,
  irrigationCapMm: 100,
  waterPriority: 65,
  soilPriority: 55,
  heatStressTolerance: 68,
  soilWorkability: 62,
  riskTolerance: 58,
}

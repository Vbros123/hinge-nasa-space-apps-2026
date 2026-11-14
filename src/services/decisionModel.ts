import type {
  CropRotation,
  DecisionBoundary,
  DecisionInputs,
  DecisionState,
  RotationComparison,
  SimulationOutput,
} from '../types/domain'

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value))

export function scoreRotations(
  rotations: CropRotation[],
  inputs: DecisionInputs,
  baselineRainMm = 281,
): RotationComparison {
  const adjustedRain = baselineRainMm * (1 + inputs.precipitationShiftPercent / 100)
  const effectiveWaterMm = adjustedRain + inputs.irrigationCapMm
  const fixedFeasibilityWeight = 22
  const fixedEnvironmentWeight = 14
  const totalWeight = inputs.waterPriority + inputs.soilPriority + fixedFeasibilityWeight + fixedEnvironmentWeight

  const results: SimulationOutput[] = rotations.map((rotation) => {
    const waterDeficitMm = Math.max(0, rotation.annualWaterNeedMm - effectiveWaterMm)
    const waterFit = clamp(100 - (waterDeficitMm / rotation.annualWaterNeedMm) * 112)
    const modeledSoilWater = clamp(
      42 + inputs.precipitationShiftPercent * 0.34 + rotation.soilImpact * 0.27
        - Math.max(0, inputs.irrigationCapMm - 130) * 0.035,
    )
    const resilience = clamp(rotation.climateResilience + inputs.precipitationShiftPercent * 0.18)
    const totalScore = (
      waterFit * inputs.waterPriority
      + modeledSoilWater * inputs.soilPriority
      + rotation.feasibility * fixedFeasibilityWeight
      + rotation.environmentalScore * fixedEnvironmentWeight
    ) / totalWeight

    return {
      rotationId: rotation.id,
      effectiveWaterMm: Math.round(effectiveWaterMm),
      waterFit: Math.round(waterFit),
      modeledSoilWater: Math.round((modeledSoilWater * 0.76 + resilience * 0.24)),
      agronomicFeasibility: rotation.feasibility,
      environmentalScore: rotation.environmentalScore,
      confidence: rotation.confidence,
      totalScore: Math.round(totalScore * 10) / 10,
      waterDeficitMm: Math.round(waterDeficitMm),
    }
  }).sort((a, b) => b.totalScore - a.totalScore)

  const scoreGap = results.length > 1 ? Math.round((results[0].totalScore - results[1].totalScore) * 10) / 10 : 0
  const confidence = results[0]?.confidence ?? 0
  let decisionState: DecisionState = 'supported'
  if (confidence < 0.6 || scoreGap < 2) decisionState = 'sensitive'
  if (confidence < 0.4) decisionState = 'insufficient'

  const leader = rotations.find((rotation) => rotation.id === results[0]?.rotationId)
  const runnerUp = rotations.find((rotation) => rotation.id === results[1]?.rotationId)
  const explanation = decisionState === 'supported'
    ? `${leader?.name ?? 'The leading rotation'} leads by ${scoreGap} modeled points under these inputs.`
    : decisionState === 'insufficient'
      ? 'Available demonstration evidence is too limited to support a preferred rotation.'
      : `${leader?.name ?? 'The current leader'} is only ${scoreGap} points ahead of ${runnerUp?.name ?? 'the next option'}; small assumption changes may reverse the order.`

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
}

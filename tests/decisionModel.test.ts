import { describe, expect, it } from 'vitest'
import { demoDashboard } from '../src/fixtures/demo'
import {
  buildDecisionBoundary,
  defaultDecisionInputs,
  scoreRotations,
} from '../src/services/decisionModel'
import { evaluateRotationFeasibility } from '../src/services/feasibilityEngine'

describe('synthetic rotation decision model', () => {
  it('updates the leader and evidence state when the water scenario changes', () => {
    const baseline = scoreRotations(demoDashboard.rotations, defaultDecisionInputs)
    const dryWaterPriority = scoreRotations(demoDashboard.rotations, {
      precipitationShiftPercent: -40,
      irrigationCapMm: 0,
      waterPriority: 100,
      soilPriority: 0,
      heatStressTolerance: 20,
      soilWorkability: 25,
      riskTolerance: 15,
    }, 181, 6)

    expect(baseline.results).toHaveLength(3)
    expect(dryWaterPriority.preferredRotationId).toBe('sorghum-legume')
    expect(dryWaterPriority.decisionState).toBe('insufficient')
    expect(dryWaterPriority.results.every((result) => result.totalScore >= 0 && result.totalScore <= 100)).toBe(true)
  })

  it('scales rainfall and crop demand to the same planning window', () => {
    const rotation = demoDashboard.rotations.find((item) => item.id === 'wheat-fallow')!
    const sixMonth = scoreRotations([rotation], {
      ...defaultDecisionInputs,
      rotationPlanningHorizonMonths: 6,
      irrigationCapMm: 0,
    }, 180, 6).results[0]
    const twelveMonth = scoreRotations([rotation], {
      ...defaultDecisionInputs,
      rotationPlanningHorizonMonths: 12,
      irrigationCapMm: 0,
    }, 180, 6).results[0]

    expect(sixMonth.seasonalPrecipitationMm).toBe(180)
    expect(sixMonth.seasonalDemandMm).toBe(124)
    expect(sixMonth.effectiveWaterMm).toBe(180)
    expect(twelveMonth.seasonalPrecipitationMm).toBe(360)
    expect(twelveMonth.seasonalDemandMm).toBe(248)
    expect(twelveMonth.effectiveWaterMm).toBe(360)
  })

  it('sorts by the displayed score and never ranks an ineligible rotation ahead of eligible options', () => {
    const comparison = scoreRotations(demoDashboard.rotations, defaultDecisionInputs)
    const eligible = comparison.results.filter((result) => result.eligible)

    expect(eligible.map((result) => result.totalScore)).toEqual(
      [...eligible].map((result) => result.totalScore).sort((left, right) => right - left),
    )
    expect(comparison.preferredRotationId).toBe(eligible[0]?.rotationId)
    expect(comparison.results.slice(0, eligible.length).every((result) => result.eligible)).toBe(true)
  })

  it('uses the displayed component weights without hidden feasibility deductions', () => {
    const rotation = demoDashboard.rotations.find((item) => item.id === 'wheat-fallow')!
    const comparison = scoreRotations([rotation], defaultDecisionInputs, 181, 6)
    const result = comparison.results[0]
    const feasibilityWeight = 20 + comparison.inputs.riskTolerance * 0.12
    const environmentWeight = 14 + (100 - comparison.inputs.heatStressTolerance) * 0.12
    const totalWeight = comparison.inputs.waterPriority + comparison.inputs.soilPriority + feasibilityWeight + environmentWeight
    const expectedScore = Math.round((
      result.waterFit * comparison.inputs.waterPriority
      + result.modeledSoilWater * comparison.inputs.soilPriority
      + result.dynamicFeasibility * feasibilityWeight
      + result.environmentalScore * environmentWeight
    ) / totalWeight * 10) / 10

    expect(result.totalScore).toBe(expectedScore)
  })

  it('hard-excludes rotations with non-overlapping planting windows and late cover termination', () => {
    const coverRotation = demoDashboard.rotations.find((item) => item.id === 'wheat-cover')!
    const plantingMismatch = evaluateRotationFeasibility(
      { ...coverRotation, plantingWindowStartDay: 200, plantingWindowEndDay: 220 },
      { ...defaultDecisionInputs, coverCropTerminationDay: 120 },
      500,
    )
    const lateTermination = evaluateRotationFeasibility(
      coverRotation,
      { ...defaultDecisionInputs, coverCropTerminationDay: 150 },
      500,
    )

    expect(plantingMismatch.eligible).toBe(false)
    expect(plantingMismatch.violatedRestrictions).toContain(
      'The farm planting window does not overlap this rotation’s required planting window.',
    )
    expect(lateTermination.eligible).toBe(false)
    expect(lateTermination.violatedRestrictions).toContain(
      'The selected termination date is later than this rotation’s cover-crop deadline.',
    )
  })

  it('keeps partial planting overlap and moderate water shortage constrained but eligible', () => {
    const fallowRotation = demoDashboard.rotations.find((item) => item.id === 'wheat-fallow')!
    const partialPlanting = evaluateRotationFeasibility(
      fallowRotation,
      { ...defaultDecisionInputs, plantingWindowStartDay: 70, plantingWindowEndDay: 120 },
      500,
    )
    const moderateWaterShortage = evaluateRotationFeasibility(
      fallowRotation,
      defaultDecisionInputs,
      0.9 * fallowRotation.annualWaterNeedMm,
    )

    expect(partialPlanting.status).toBe('constrained')
    expect(partialPlanting.eligible).toBe(true)
    expect(moderateWaterShortage.status).toBe('constrained')
    expect(moderateWaterShortage.eligible).toBe(true)
  })

  it('does not apply cover termination constraints to rotations without a cover crop', () => {
    const fallowRotation = demoDashboard.rotations.find((item) => item.id === 'wheat-fallow')!
    const assessment = evaluateRotationFeasibility(
      fallowRotation,
      { ...defaultDecisionInputs, coverCropTerminationDay: 210 },
      500,
    )

    expect(assessment.applicableConstraints).not.toContain('Cover-crop termination')
  })

  it('hard-excludes severe seasonal water deficits from the preferred rotation', () => {
    const rotation = demoDashboard.rotations.find((item) => item.id === 'wheat-fallow')!
    const comparison = scoreRotations([rotation], {
      ...defaultDecisionInputs,
      irrigationCapMm: 0,
      plantingWindowStartDay: 90,
      plantingWindowEndDay: 180,
    }, 0, 6)

    expect(comparison.results[0].feasibilityStatus).toBe('infeasible')
    expect(comparison.results[0].eligible).toBe(false)
    expect(comparison.preferredRotationId).toBeNull()
    expect(comparison.decisionState).toBe('no-feasible')
  })

  it('reports real score and feasibility transitions with a refined precipitation interval', () => {
    const boundary = buildDecisionBoundary(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      irrigationCapMm: 0,
    }, 181, 6)

    expect(boundary.points).toHaveLength(81)
    expect(boundary.transitions.length).toBeGreaterThan(0)
    expect(boundary.transitionDetails).toHaveLength(boundary.transitions.length)
    expect(boundary.transitionDetails.some((transition) => transition.reason === 'constraint')).toBe(true)
    expect(boundary.points[0].precipitationShiftPercent).toBe(-40)
    expect(boundary.points.at(-1)?.precipitationShiftPercent).toBe(40)
    expect(boundary.transitionDetails.every((transition) => transition.range[1] - transition.range[0] <= 0.1)).toBe(true)
  })

  it('does not invent a transition when all candidates remain infeasible', () => {
    const boundary = buildDecisionBoundary(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      plantingWindowStartDay: 60,
      plantingWindowEndDay: 80,
    }, 0, 6)

    expect(boundary.points.every((point) => point.preferredRotationId === null)).toBe(true)
    expect(boundary.transitions).toEqual([])
    expect(boundary.transitionDetails).toEqual([])
  })

  it('can represent supported, sensitive, insufficient, and no-feasible outcomes', () => {
    const observedStates = new Set<string>()
    for (const precipitationShiftPercent of [-40, -20, 0, 20, 40]) {
      for (const irrigationCapMm of [0, 100, 220]) {
        for (const waterPriority of [0, 20, 65, 100]) {
          for (const soilPriority of [0, 50, 100]) {
            for (const heatStressTolerance of [20, 60, 100]) {
              for (const soilWorkability of [20, 60, 100]) {
                for (const riskTolerance of [15, 50, 100]) {
                  observedStates.add(scoreRotations(demoDashboard.rotations, {
                    precipitationShiftPercent,
                    irrigationCapMm,
                    waterPriority,
                    soilPriority,
                    heatStressTolerance,
                    soilWorkability,
                    riskTolerance,
                  }, 181, 6).decisionState)
                }
              }
            }
          }
        }
      }
    }

    expect(observedStates).toEqual(new Set(['supported', 'sensitive', 'insufficient']))
  })

  it('adjusts dynamic feasibility when agronomic assumptions tighten', () => {
    const baseline = scoreRotations(demoDashboard.rotations, defaultDecisionInputs, 181, 6)
    const constrained = scoreRotations(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      heatStressTolerance: 20,
      soilWorkability: 20,
      riskTolerance: 15,
    }, 181, 6)
    const baselineRotation = baseline.results.find((result) => result.rotationId === 'wheat-fallow')!
    const constrainedRotation = constrained.results.find((result) => result.rotationId === 'wheat-fallow')!

    expect(constrainedRotation.dynamicFeasibility).toBeLessThan(baselineRotation.dynamicFeasibility)
    expect(constrainedRotation.feasibilityPenalty).toBeGreaterThan(baselineRotation.feasibilityPenalty)
  })
})

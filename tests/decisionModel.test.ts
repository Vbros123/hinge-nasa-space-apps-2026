import { describe, expect, it } from 'vitest'
import { demoDashboard } from '../src/fixtures/demo'
import {
  buildDecisionBoundary,
  defaultDecisionInputs,
  scoreRotations,
} from '../src/services/decisionModel'

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
    })

    expect(baseline.results).toHaveLength(3)
    expect(dryWaterPriority.preferredRotationId).not.toBe(baseline.preferredRotationId)
    expect(dryWaterPriority.preferredRotationId).toBe('sorghum-legume')
    expect(dryWaterPriority.decisionState).toBe('insufficient')
    expect(dryWaterPriority.results.every((result) => result.totalScore >= 0 && result.totalScore <= 100)).toBe(true)
  })

  it('exposes score transitions across precipitation assumptions', () => {
    const boundary = buildDecisionBoundary(demoDashboard.rotations, defaultDecisionInputs)

    expect(boundary.points).toHaveLength(17)
    expect(boundary.transitions.length).toBeGreaterThan(0)
    expect(boundary.points[0].precipitationShiftPercent).toBe(-40)
    expect(boundary.points.at(-1)?.precipitationShiftPercent).toBe(40)
  })

  it('can represent supported, sensitive, and insufficient outcomes', () => {
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
                  }).decisionState)
                }
              }
            }
          }
        }
      }
    }

    expect(observedStates).toEqual(new Set(['supported', 'sensitive', 'insufficient']))
  })

  it('adjusts feasibility dynamically when agronomic constraints tighten', () => {
    const baseline = scoreRotations(demoDashboard.rotations, defaultDecisionInputs)
    const constrained = scoreRotations(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      heatStressTolerance: 20,
      soilWorkability: 20,
      riskTolerance: 15,
    })

    expect(constrained.results[0].dynamicFeasibility).toBeLessThan(baseline.results[0].dynamicFeasibility)
    expect(constrained.results[0].feasibilityPenalty).toBeGreaterThan(baseline.results[0].feasibilityPenalty)
  })

  it('keeps irrigation and preference weights in the same score calculation', () => {
    const lowIrrigation = scoreRotations(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      irrigationCapMm: 0,
    })
    const highIrrigation = scoreRotations(demoDashboard.rotations, {
      ...defaultDecisionInputs,
      irrigationCapMm: 220,
    })

    expect(lowIrrigation.results.find((result) => result.rotationId === 'wheat-cover')?.waterFit)
      .toBeLessThan(highIrrigation.results.find((result) => result.rotationId === 'wheat-cover')?.waterFit ?? 0)
    expect(lowIrrigation.inputs.irrigationCapMm).toBe(0)
    expect(highIrrigation.inputs.irrigationCapMm).toBe(220)
  })
})

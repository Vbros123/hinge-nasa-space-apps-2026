export type EvidenceStatus = 'observed' | 'modeled' | 'assumed' | 'unavailable'
export type DecisionState = 'supported' | 'sensitive' | 'insufficient' | 'no-feasible'
export type FeasibilityStatus = 'feasible' | 'constrained' | 'infeasible'

export interface FarmLocation {
  id: string
  name: string
  region: string
  latitude: number
  longitude: number
  areaHectares: number
  elevationMeters: number
}

export interface ClimateObservation {
  id: string
  farmId: string
  date: string
  precipitationMm: number
  temperatureC: number
  soilMoisturePercent: number | null
  source: string
  status: EvidenceStatus
}

export interface NasaClimateObservation extends ClimateObservation {
  productId?: string
  collection?: string
}

export interface SoilCharacteristics {
  farmId: string
  texture: string
  organicCarbonPercent: number
  availableWaterCapacityMmPerM: number
  ph: number
  status: EvidenceStatus
}

export interface VegetationObservation {
  farmId: string
  date: string
  ndvi: number | null
  source: string
  status: EvidenceStatus
}

export interface CropRotation {
  id: string
  name: string
  sequence: string[]
  annualWaterNeedMm: number
  soilImpact: number
  climateResilience: number
  feasibility: number
  environmentalScore: number
  confidence: number
  color: string
  description: string
  plantingWindowStartDay: number
  plantingWindowEndDay: number
  coverCropTerminationDay: number
  planningHorizonMonths: number
  sequenceCompatibility: number
}

export interface DecisionInputs {
  precipitationShiftPercent: number
  irrigationCapMm: number
  waterPriority: number
  soilPriority: number
  heatStressTolerance: number
  soilWorkability: number
  riskTolerance: number
  plantingWindowStartDay: number
  plantingWindowEndDay: number
  coverCropTerminationDay: number
  rotationPlanningHorizonMonths: number
  sequenceCompatibility: number
}

export interface RotationFeasibilityAssessment {
  rotationId: string
  status: FeasibilityStatus
  eligible: boolean
  applicableConstraints: string[]
  violatedRestrictions: string[]
  explanation: string
  hardConstraintCount: number
}

export interface SimulationOutput {
  rotationId: string
  effectiveWaterMm: number
  waterFit: number
  modeledSoilWater: number
  climateResilience: number
  agronomicFeasibility: number
  dynamicFeasibility: number
  feasibilityPenalty: number
  environmentalScore: number
  confidence: number
  totalScore: number
  waterDeficitMm: number
  eligible: boolean
  feasibilityStatus: FeasibilityStatus
}

export interface RotationComparison {
  inputs: DecisionInputs
  results: SimulationOutput[]
  preferredRotationId: string
  decisionState: DecisionState
  scoreGap: number
  explanation: string
  uncertainty: UncertaintyAssessment
}

export interface UncertaintyAssessment {
  state: DecisionState
  leaderConfidence: number
  scoreGap: number
  provenanceStatus: EvidenceStatus
  limitingFactors: string[]
}

export interface DecisionBoundaryTransition {
  precipitationShiftPercent: number
  fromRotationId: string
  toRotationId: string
  range: [number, number]
  reason: 'score' | 'constraint'
}

export interface DecisionBoundaryPoint {
  precipitationShiftPercent: number
  scores: Record<string, number>
  preferredRotationId: string
}

export interface DecisionBoundary {
  points: DecisionBoundaryPoint[]
  currentInputs: DecisionInputs
  transitions: number[]
  transitionDetails: DecisionBoundaryTransition[]
}

export interface EvidenceItem {
  id: string
  label: string
  status: EvidenceStatus
  source: string
  detail: string
  updatedAt?: string
}

export interface FarmDashboardData {
  farm: FarmLocation
  climate: NasaClimateObservation[]
  soil: SoilCharacteristics
  vegetation: VegetationObservation[]
  rotations: CropRotation[]
  evidence: EvidenceItem[]
}

export interface HistoricalScenario {
  year: number
  precipitationMm: number
  temperatureC: number
  dryDays: number
  modeledYieldIndex: number
  note: string
}

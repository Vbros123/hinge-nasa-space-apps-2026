export type EvidenceStatus = 'observed' | 'modeled' | 'assumed' | 'unavailable'
export type DecisionState = 'supported' | 'sensitive' | 'insufficient'

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
}

export interface DecisionInputs {
  precipitationShiftPercent: number
  irrigationCapMm: number
  waterPriority: number
  soilPriority: number
  heatStressTolerance: number
  soilWorkability: number
  riskTolerance: number
}

export interface SimulationOutput {
  rotationId: string
  effectiveWaterMm: number
  waterFit: number
  modeledSoilWater: number
  agronomicFeasibility: number
  dynamicFeasibility: number
  feasibilityPenalty: number
  environmentalScore: number
  confidence: number
  totalScore: number
  waterDeficitMm: number
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

export interface DecisionBoundaryPoint {
  precipitationShiftPercent: number
  scores: Record<string, number>
  preferredRotationId: string
}

export interface DecisionBoundary {
  points: DecisionBoundaryPoint[]
  currentInputs: DecisionInputs
  transitions: number[]
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

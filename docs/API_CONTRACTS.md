# HINGE frontend data and integration contracts

This document describes the interfaces expected by the frontend. The HTTP routes below are **proposals only**: no server, NASA connector, authentication flow, or endpoint is included in this repository.

## Frontend mode selection

`src/services/api.ts` defines `HingeDataService`, `DemoDataService`, and an optional `HttpDataService`. The app uses deterministic synthetic fixtures when `VITE_HINGE_API_BASE_URL` is absent. If the variable is present, the HTTP adapter requests:

- `GET {baseUrl}/farms/{farmId}/dashboard` → `FarmDashboardData`
- `GET {baseUrl}/farms/{farmId}/history` → `HistoricalScenario[]`

These are not live endpoints. An integration owner should align route names, authentication, CORS, pagination, versioning, and failure semantics with Persons 1, 2, and 4 before enabling the HTTP adapter. Non-2xx responses are surfaced as errors; this frontend does not substitute fake success data after a server failure.

## Shared response models

The canonical TypeScript declarations are in `src/types/domain.ts`.

| Contract | Fields / intent |
| --- | --- |
| `FarmLocation` | `id`, `name`, `region`, `latitude`, `longitude`, `areaHectares`, `elevationMeters` |
| `NasaClimateObservation` | farm ID, date, precipitation (mm), temperature (°C), optional soil moisture, NASA product / collection identifiers when applicable, source, and `EvidenceStatus` |
| `SoilCharacteristics` | texture, organic carbon (%), available water capacity (mm/m), pH, farm ID, evidence status |
| `VegetationObservation` | farm ID, date, optional NDVI, source, evidence status |
| `CropRotation` | ID, display name, crop sequence, annual water demand, soil impact, climate resilience, feasibility, environmental score, confidence, planting window, whether cover-crop termination applies, and the termination deadline |
| `DecisionInputs` | precipitation shift (%), irrigation cap (mm over the planning period), water and soil priorities, heat/soil/risk tolerances, planting-window bounds, cover-crop termination date, planning horizon (months), and sequence-compatibility minimum |
| `SimulationOutput` | rotation ID, seasonal precipitation and demand, effective water supply, water fit, modeled soil-water indicator, dynamic feasibility, environmental indicator, confidence, total score, water deficit, feasibility status, and eligibility |
| `RotationComparison` | exact input snapshot, simulation outputs, nullable preferred rotation ID (`null` when no candidate is eligible), decision state, score gap, human-readable explanation |
| `UncertaintyAssessment` | decision state, leader confidence, score gap, provenance status, and limiting factors |
| `DecisionBoundary` | sampled precipitation assumptions, scores, preferred option, decision state and eligible rotations at each sample, plus refined score/feasibility transition intervals |
| `EvidenceItem` | label, evidence status, source, explanation, optional update time |
| `HistoricalScenario` | year label, precipitation, temperature, dry-day indicator, simulated response index, narrative note |

`EvidenceStatus` is `observed | modeled | assumed | unavailable`. The UI labels fixture climate, soil, vegetation, and locations as synthetic assumptions; client calculations are modeled; real data connections are marked unavailable. An integration must keep provenance and status alongside every value rather than presenting estimates as observations.

## Example dashboard payload shape

```json
{
  "farm": {
    "id": "farm-123",
    "name": "Example field",
    "region": "Region label",
    "latitude": 39.7,
    "longitude": -103.1,
    "areaHectares": 486,
    "elevationMeters": 1512
  },
  "climate": [
    {
      "id": "climate-1",
      "farmId": "farm-123",
      "date": "2025-05-01",
      "precipitationMm": 42,
      "temperatureC": 15.8,
      "soilMoisturePercent": null,
      "source": "Dataset identifier and version",
      "status": "observed"
    }
  ],
  "soil": {
    "farmId": "farm-123",
    "texture": "Silt loam",
    "organicCarbonPercent": 1.8,
    "availableWaterCapacityMmPerM": 148,
    "ph": 6.7,
    "status": "observed"
  },
  "vegetation": [],
  "rotations": [],
  "evidence": []
}
```

The example numbers are illustrative schema values, not real data or a recommended response. `vegetation`, `rotations`, and `evidence` use the matching interfaces above.

## Calculation ownership and assumptions

The current frontend derives `RotationComparison` and `DecisionBoundary` locally in `src/services/decisionModel.ts`; these formulas are synthetic demonstration logic, not an agronomic model. `baselineRainMm` is the accumulated precipitation over `baselineRainWindowMonths`. The monthly mean is extended over the selected planning horizon, multiplied by `1 + precipitationShiftPercent / 100` (floored at zero), and then added to `irrigationCapMm`. Rotation demand for that same period is `annualWaterNeedMm * planningHorizonMonths / 12`. Irrigation is a total millimeter amount for the selected planning period, not an annual rate. The demo adapter derives the source-window month count from distinct climate observation months; its six-month fallback is only for fixtures without dated observations. Scaling a partial historical window across a longer horizon is an explicit illustrative assumption and must not be used as a scientific forecast.

Water fit is `clamp(100 - (waterDeficitMm / seasonalDemandMm) * 112, 0, 100)`. Dynamic feasibility is the 0–100 clamp of base agronomic feasibility minus: water deficit ratio × 45; `(100 - heatStressTolerance) × 0.18 × (1 - climateResilience / 100)`; `(100 - soilWorkability) × 0.22 × (1 - soilImpact / 100)`; `(100 - riskTolerance) × 0.18 × (1 - confidence)`; and the dry-climate term `max(0, -precipitationShiftPercent) / 100 × (100 - climateResilience) × 0.8`, plus `(riskTolerance - 50) × 0.14`. Component values are rounded to one decimal before the total is calculated.

The model score is the normalized weighted mean of water fit, modeled soil-water, dynamic feasibility, and environmental score; there is no hidden feasibility subtraction. The weights are water priority, soil priority, `20 + riskTolerance * 0.12`, and `14 + (100 - heatStressTolerance) * 0.12`. Modeled soil-water is `clamp(42 + precipitationShiftPercent * 0.34 + soilImpact * 0.18 + (soilWorkability - 50) * 0.38 - max(0, irrigationCapMm - 150) * 0.03)`. The exact same rounded `totalScore` determines visible ordering and preference, with rotation ID as the deterministic tie-break. Ineligible scores remain available as diagnostics but are placed below eligible options and cannot be selected as the preference. The confidence and gap thresholds only choose the presentation state; they do not adjust the numeric score.

`src/services/feasibilityEngine.ts` applies the explicit constraints before preference ranking. A non-overlapping or invalid planting window, missed termination deadline for a rotation marked `requiresCoverCropTermination`, too-short planning horizon, sequence compatibility below the selected minimum, or modeled water coverage below 88% makes a rotation ineligible. A partial planting-window overlap or water coverage from 88% to below 100% is constrained but remains eligible. Rotations without a cover crop do not receive a termination check. The 88% threshold and window interpretation are provisional demo assumptions; Person 4 and the agronomy owner must confirm or replace them.

The boundary samples precipitation shifts at 1 percentage-point steps, detects changes in the leader, eligible set, or decision state, then bisects each detected interval until its width is at most 0.1 percentage points. No transition is fabricated when none occurs in the sampled range. Decision states use synthetic confidence and score-gap thresholds and are not scientifically validated uncertainty estimates. Replace `scoreRotations` only after agreeing who owns weights, units, constraint thresholds, missing-value behavior, and uncertainty communication.

For production integration, Person 4 should return the agreed simulation/comparison payload rather than silently changing the meaning of these demo fields. Include formula/model version, input snapshot, unit metadata, evidence provenance, constraint outcomes, uncertainty, and eligibility with each result. Keep the frontend calculation as an explicit demo adapter until the backend contract is approved.

## Integration checklist

1. Agree on data sources, units, coordinate reference, timestamps, quality flags, and provenance with the data/backend owners.
2. Map server payloads into these frontend contracts in `HttpDataService` or a dedicated adapter; validate external JSON at runtime before trusting it.
3. Keep unavailable values explicit (`null` where permitted plus an evidence item); do not infer missing NASA observations from demo fixtures.
4. Confirm the real simulation owner and uncertainty semantics. The frontend demo formula is not a substitute for the project model.
5. Add contract fixtures and adapter tests before enabling the HTTP base URL in a deployed build.

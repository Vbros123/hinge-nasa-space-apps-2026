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
| `CropRotation` | ID, display name, crop sequence, annual water demand, soil impact, climate resilience, feasibility, environmental score, confidence, display color, description |
| `DecisionInputs` | precipitation shift (%), irrigation cap (mm), water priority (0–100), soil priority (0–100) |
| `SimulationOutput` | rotation ID, effective water, water fit, modeled soil-water indicator, feasibility, environment indicator, confidence, total score, water deficit |
| `RotationComparison` | exact input snapshot, simulation outputs, preferred rotation ID, decision state, score gap, human-readable explanation |
| `UncertaintyAssessment` | decision state, leader confidence, score gap, provenance status, and limiting factors |
| `DecisionBoundary` | sampled precipitation assumptions, scores by rotation, preferred option at each sample, current inputs, transition locations |
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

Today the frontend derives `RotationComparison` and `DecisionBoundary` locally in `src/services/decisionModel.ts`. It uses the selected farm's synthetic growing-season precipitation total as baseline, applies the user precipitation shift, adds irrigation availability, and compares effective water with each rotation's annual water-demand proxy. Water fit is clamped to 0–100. The soil-water indicator combines a baseline term, precipitation shift, rotation soil-impact attribute, irrigation adjustment, and climate-resilience attribute. The total is a normalized weighted mean of water fit, soil-water score, feasibility, and environmental score. A grid samples the same calculation at 5% precipitation increments.

The decision state is a presentation aid over synthetic confidence and score separation: confidence below 0.4 is insufficient; otherwise confidence below 0.6 or a score gap below 2 points is sensitive; a wider gap and confidence of at least 0.6 are marked supported. It must not be interpreted as a scientifically validated uncertainty method. Real model outputs should be added to `SimulationOutput` (or a versioned server-side result contract) and passed to the shared comparison UI. Replace `scoreRotations` only after agreeing who owns weights, units, thresholds, missing-value behavior, and uncertainty communication.

## Integration checklist

1. Agree on data sources, units, coordinate reference, timestamps, quality flags, and provenance with the data/backend owners.
2. Map server payloads into these frontend contracts in `HttpDataService` or a dedicated adapter; validate external JSON at runtime before trusting it.
3. Keep unavailable values explicit (`null` where permitted plus an evidence item); do not infer missing NASA observations from demo fixtures.
4. Confirm the real simulation owner and uncertainty semantics. The frontend demo formula is not a substitute for the project model.
5. Add contract fixtures and adapter tests before enabling the HTTP base URL in a deployed build.

# Person 4 backend integration handoff

This handoff describes what the frontend can consume and what the backend still needs to provide. It does **not** assert that a backend, NASA data connector, model service, or endpoint exists. The only runnable data source in this repository is the explicitly synthetic `DemoDataService`.

## Current frontend seam

`src/services/api.ts` exports `HingeDataService`, `DemoDataService`, and an optional `HttpDataService`. With `VITE_HINGE_API_BASE_URL` unset, the app uses synthetic fixtures. When set, the current adapter proposes these routes:

| Method and proposed route | Response |
| --- | --- |
| `GET /farms/{farmId}/dashboard` | `FarmDashboardData` |
| `GET /farms/{farmId}/history` | `HistoricalScenario[]` |

These are frontend route proposals only. Before enabling the HTTP adapter, Person 4 must confirm route ownership, API versioning, authentication, CORS, error format, retry/rate-limit behavior, and whether the client or server owns the rotation calculation. Non-2xx responses currently surface as errors; the client does not silently fall back to demo values.

## Required data and provenance

Use the canonical TypeScript declarations in `src/types/domain.ts` and the detailed field table in `docs/API_CONTRACTS.md`. In particular:

- Farm IDs must be stable and all observations must reference the matching `farmId`. Coordinates use decimal latitude/longitude.
- Climate observations carry dates, precipitation in millimeters, temperature in Celsius, optional soil moisture, source/product/collection metadata where available, and an evidence status. Report the accumulation interval and quality flags; do not make a partial interval look like a full season.
- Soil and vegetation values include their units, source, timestamp or period, and evidence status. Use `null` for unavailable measurements where the contract permits it; attach an `EvidenceItem` describing what is unavailable.
- Rotations provide annual water demand in mm/year, explicit planting-window bounds, planning-horizon requirement, sequence compatibility, and `requiresCoverCropTermination`. A termination date is meaningful only when that flag is true.
- Model outputs identify the model/version, input snapshot, unit basis, constraints evaluated, eligibility, uncertainty, and provenance. Do not label predictions as observations.

The UI currently labels fixture values as assumed and frontend calculations as modeled. If the backend returns observed data, preserve its actual product/source and status; never copy fixture provenance into live responses.

## Water window and comparison semantics

The demo expects `baselineRainMm` to be a total over `baselineRainWindowMonths`. It extends the observed-window monthly mean to the selected `rotationPlanningHorizonMonths`, applies the precipitation-shift assumption, and adds `irrigationCapMm`, which is a total allocation over that same planning period. Rotation water need is `annualWaterNeedMm * planningHorizonMonths / 12`. This is a transparent synthetic extrapolation, not a defensible climatology method.

Person 4 should provide either:

1. A climate summary explicitly aggregated to the model's requested planning window, with the interval and accumulation method in metadata; or
2. A versioned simulation result that owns the climate-window calculation and returns seasonal precipitation, demand, effective water, water deficit, feasibility status, and eligibility together.

Do not combine a six-month precipitation sum with a twelve-month demand, apply a second horizon multiplier to already seasonal data, or reinterpret irrigation as an annual rate without changing the contract and frontend labels.

The current scoring formula and 88% minimum water-coverage threshold are demonstration assumptions. If the backend owns scoring, the API response should include its `modelVersion`, total score, component scores, configured weights, thresholds, selected preference, decision state, and explanation. The frontend should render these outputs rather than recompute a competing ranking. If the frontend continues to own scoring, Person 4 must explicitly approve the formula, units, constraint boundaries, tie behavior, missing-data behavior, and sensitivity semantics.

## Hard feasibility behavior

The current demo excludes, rather than merely penalizes, a rotation with an invalid/non-overlapping planting window, an unmet cover-crop termination deadline when applicable, insufficient planning horizon, sequence compatibility below the selected minimum, or less than 88% of modeled seasonal water demand. Partial planting-window overlap and water coverage of at least 88% but below 100% are labeled constrained and remain eligible. The comparison and boundary screens share this eligibility decision; ineligible score values are diagnostic only.

These thresholds and the overlap policy need agronomic review. Backend constraints must be returned per rotation with stable IDs, eligibility, violated constraint codes, human-readable messages, and the inputs/window used. A `no-feasible` result should contain no preferred rotation ID, not a fallback winner.

## Integration steps

1. Agree with Persons 1, 2, and 4 on service ownership, product identifiers, dates/time zones, units, source periods, quality flags, model version, and constraint semantics.
2. Freeze a versioned OpenAPI/JSON Schema contract for dashboard, history, and simulation/comparison payloads. Treat the current `/farms/...` routes as proposals until the backend owner confirms them.
3. Add runtime response validation in `HttpDataService` (TypeScript interfaces alone do not validate JSON), including finite numeric values, allowed evidence/decision states, valid coordinate ranges, matching farm IDs, and explicit handling for missing fields.
4. Add sanitized contract fixtures and adapter tests for observed, modeled, assumed, unavailable, partial-period, and error responses. Do not use production observations as synthetic demo fixtures.
5. Keep `DemoDataService` behind an explicit demo configuration. Do not switch a deployment into live mode merely because a base URL is present unless the response schema and provenance have been validated.
6. Confirm a response end to end with Person 4 and label any unavailable integration in the Evidence & Uncertainty screen until it is genuinely connected.

## Proposed simulation response (illustrative schema only)

The following is not an implemented endpoint or an agreed backend payload:

```json
{
  "modelVersion": "backend-owned-version",
  "farmId": "farm-identifier",
  "planningWindow": {
    "start": "2026-04-01",
    "end": "2026-09-30",
    "precipitationMm": 181,
    "irrigationMm": 35,
    "units": "mm"
  },
  "comparison": {
    "decisionState": "insufficient",
    "preferredRotationId": null,
    "scoreGap": 0,
    "results": [
      {
        "rotationId": "rotation-id",
        "seasonalDemandMm": 124,
        "effectiveWaterMm": 126,
        "totalScore": 61.2,
        "eligible": true,
        "feasibilityStatus": "constrained",
        "violatedConstraintCodes": [],
        "uncertainty": {
          "confidence": null,
          "status": "unavailable"
        }
      }
    ]
  },
  "evidence": [
    {
      "label": "Climate input",
      "status": "observed",
      "source": "product and collection identifier",
      "detail": "Server-supplied aggregation interval and quality summary."
    }
  ]
}
```

In the final contract, use the shared domain types or introduce a versioned API DTO and an explicit adapter into those types. `null` in the illustrative `preferredRotationId` represents no supported preference; map the exact server semantics before implementation.

# HINGE · Land Systems Intelligence

An interactive React + TypeScript frontend concept for comparing crop rotations under changing climate assumptions. This is a standalone Person 3 demonstration repository for NASA Space Apps Challenge 2026.

> **Synthetic demo only.** Every farm, climate, soil, vegetation, and rotation value in the default demo is illustrative. No authentic NASA observations, field measurements, validated agronomic predictions, or live backend services are connected.

## Run locally

Requires Node.js 20.19+ or 22.12+ and npm.

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). To create and check the production build:

```bash
npm run build
npm test
npm run lint
npm run preview
```

## What is included

- **Farm intelligence:** interactive Leaflet location map, selectable synthetic farms, soil profile, seasonal rainfall / vegetation chart, and current model readout.
- **Rotation comparison:** ranked crop rotations, indicator table, score chart, and trade-off radar.
- **Decision boundary explorer:** responsive scenario controls, explicit agronomic constraint sliders (heat stress tolerance, soil workability, and risk tolerance), quick presets, a live multi-rotation sensitivity plot with decision transitions, score ranking, and a live explanation of the current lead. The same calculation powers the comparison view.
- **Historical climate replay:** interactive year timeline, year-to-year comparison, synthetic climate assumptions, and a separately labeled simulated response index.
- **Evidence & uncertainty:** provenance register with filtering, explicit unavailable data, and supported / sensitive / insufficient / no-feasible decision states.
- **Integration seams:** shared TypeScript contracts, an API adapter interface, a mock service, and an opt-in HTTP adapter. Proposed routes are not implemented backend endpoints.

The interface is responsive down to mobile widths and uses accessible labels on navigation and controls. Map tiles require an internet connection and are served by OpenStreetMap; farm coordinates and markers remain synthetic.

Verification details and tool limitations are recorded in [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Data mode and integrations

By default the app uses `DemoDataService`. The HTTP adapter is selected only when `VITE_HINGE_API_BASE_URL` is set in the environment. The intended response shapes, example payloads, and assumptions are documented in [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) and the Person 4 action checklist in [`docs/PERSON4_INTEGRATION_HANDOFF.md`](docs/PERSON4_INTEGRATION_HANDOFF.md).

```bash
cp .env.example .env.local
# Set VITE_HINGE_API_BASE_URL only when a compatible service is available.
```

There is no guarantee that a compatible API exists at any URL. The current proposed paths (`/farms/{farmId}/dashboard` and `/farms/{farmId}/history`) are integration contracts for the team to agree on, not claims about an existing service.

## Model and interpretation

The client-side demonstration formula is in `src/services/decisionModel.ts`. It scales the precipitation total and annual crop demand to the same selected planning window, then calculates one weighted score used by both displayed sorting and the preferred rotation. `src/services/feasibilityEngine.ts` excludes rotations that violate hard planting-window, cover-crop deadline, horizon, sequence, or severe water-coverage constraints. The boundary samples score, eligibility, and decision-state changes and refines each transition interval.

The water-window scaling, 88% minimum water-coverage threshold, constraint rules, confidence gates, and decision states are provisional synthetic assumptions, not scientific confidence or validated agronomic thresholds. Rotation scores are relative and must not be interpreted as yields, measured water balances, or recommendations. Read the assumptions before adapting the formula.

## Repository layout

```text
src/
  components/  reusable shell, map, and UI primitives
  fixtures/    clearly labeled synthetic demo data
  hooks/       frontend data loading
  pages/       the five primary screens
  services/    API adapters and decision calculation
  types/       shared domain contracts
  styles/      reserved for future modular styles
tests/         focused model behavior tests
docs/          integration contracts and assumptions
```

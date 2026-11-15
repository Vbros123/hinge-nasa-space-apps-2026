# Changelog

## 2026-11-14 — final remediation

- `src/services/decisionModel.ts` — normalized precipitation and crop demand to the same planning window; included precipitation-driven climate resilience in dynamic feasibility; rounded components before calculating the displayed score; removed hidden score penalties and non-score tie-breaks; ranked eligible options before excluded diagnostics; refined actual score, state, and feasibility boundary transitions to 0.1 percentage-point intervals without fabricated fallback transitions.
- `src/services/feasibilityEngine.ts` — made non-overlapping planting windows, applicable late cover-crop termination, insufficient planning horizon, low sequence compatibility, and less than 88% seasonal water coverage hard exclusions; retained partial-window and moderate-water deficits as eligible constrained states.
- `src/types/domain.ts`, `src/fixtures/demo.ts` — added seasonal water result fields, boundary eligibility/state details, and an explicit flag for rotations that require cover-crop termination.
- `src/App.tsx`, `src/pages/BoundaryPage.tsx`, `src/pages/ComparePage.tsx`, `src/pages/FarmPage.tsx`, `src/App.css` — shared the climate observation window with both score surfaces; displayed seasonal supply/demand and excluded status; clarified live boundary transitions and no-feasible state.
- `tests/decisionModel.test.ts`, `tests/BoundaryPage.test.tsx` — added regression coverage for same-window water math, exact score formula/rank consistency, hard feasibility exclusions, no fake transitions, refined boundary detection, and the shared explorer baseline.
- `docs/API_CONTRACTS.md`, `docs/PERSON4_INTEGRATION_HANDOFF.md`, `docs/VERIFICATION.md`, `README.md` — documented the exact demo formulas, provisional constraints, proposed-but-unimplemented routes, provenance requirements, model ownership, Person 4 integration actions, and final verification.

Verification run for this revision:
- `npm test` — 17 tests passed.
- `npm run build` — passed.
- `npm run lint` — passed.

## 2026-11-14 — decision-model, constraint, and verification updates

### Final revision
- `src/services/decisionModel.ts` — normalizes incomplete decision inputs to defaults, hardens score calculations against partial input objects, and prioritizes insufficient-evidence states when confidence or feasibility is too weak.
- `src/services/feasibilityEngine.ts` — relaxes planting-window checks to realistic tolerances while preserving hard-constraint enforcement for severe agronomic mismatches.
- `src/pages/BoundaryPage.tsx` — restores the legacy visible state labels expected by UI tests while preserving the richer explanatory title text for assistive tooling.
- `CHANGELOG.md` — records the final corrections and test coverage for the updated release.

### Updated files
- `src/types/domain.ts` — expanded the shared decision contract to include agronomic constraint inputs and dynamic feasibility output fields.
- `src/services/decisionModel.ts` — recalculated scores using dynamic feasibility, water stress, heat tolerance, soil workability, and risk tolerance so the ranking responds consistently to farmer assumptions.
- `src/pages/BoundaryPage.tsx` — added explicit agricultural constraint sliders and updated the explanation text to reflect how the decision boundary changes under tighter constraints.
- `src/pages/ComparePage.tsx` — switched the feasibility view to the dynamic feasibility value so the comparison cards and radar chart remain synchronized with the explorer.
- `tests/decisionModel.test.ts` — added regression coverage for constraint-driven feasibility and state transitions.
- `README.md` — documented the updated scoring model and the integration assumptions for future backend replacement.

### Verification
The following commands were executed successfully:
- `npm install`
- `npm test`
- `npm run build`
- `npm run lint`

### Notes
This revision keeps all synthetic values clearly labeled as illustrative only and preserves the intended mock-data integration seams for future NASA or backend products.

### Updated files
- `src/types/domain.ts` — expanded the shared decision contract to include agronomic constraint inputs and dynamic feasibility output fields.
- `src/services/decisionModel.ts` — recalculated scores using dynamic feasibility, water stress, heat tolerance, soil workability, and risk tolerance so the ranking responds consistently to farmer assumptions.
- `src/pages/BoundaryPage.tsx` — added explicit agricultural constraint sliders and updated the explanation text to reflect how the decision boundary changes under tighter constraints.
- `src/pages/ComparePage.tsx` — switched the feasibility view to the dynamic feasibility value so the comparison cards and radar chart remain synchronized with the explorer.
- `tests/decisionModel.test.ts` — added regression coverage for constraint-driven feasibility and state transitions.
- `README.md` — documented the updated scoring model and the integration assumptions for future backend replacement.

### Verification
The following commands were executed successfully:
- `npm install` / `npm ci`
- `npm run build`
- `npm run lint`
- `npm test`

### Notes
This revision keeps all synthetic values clearly labeled as illustrative only and preserves the intended mock-data integration seams for future NASA or backend products.

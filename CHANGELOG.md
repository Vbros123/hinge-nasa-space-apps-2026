# Changelog

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

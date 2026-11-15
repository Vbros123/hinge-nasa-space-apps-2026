# HINGE production scientific walkthrough

**Verdict — READY_WITH_NONBLOCKING_LIMITATIONS**

## Production identity

- Public URL — [HINGE](https://hinge-nasa-space-apps-2026.vercel.app/)
- Verified — November 15, 2026, approximately 1:02–1:05 p.m. EST
- GitHub main — `f6fdc496111b507fc4f5843c3591c87affd901ef`. Audited application code, catalog and lockfile hashes matched the browser-tested build inputs. All 65 public build files, including all 41 scientific JSON files, matched the tested release build byte for byte.
- Public status — HTTP 200 and usable in a fresh Chromium context without authentication.
- Vercel target — public production alias. The connected account returned HTTP 403 for deployment listing and HTTP 404 for deployment and alias lookups. The Vercel deployment ID, dashboard state and Git SHA label could not be read independently. The public-file comparison verifies the served build contents.

## Live results

| Screen | Result | Evidence |
| --- | --- | --- |
| Farm Intelligence | PASS | Science mode opened by default. The provisional study polygon rendered and four OpenStreetMap tiles returned HTTP 200. The page showed 42 accepted NASA POWER years (1984–2025), survey-derived SSURGO estimates including 129.3 mm medium storage, and 94 usable HLS acquisitions out of 191. |
| Rotation Comparison | PASS | All three rotations appeared. The six reference spot checks below matched their archive values at display precision. Both objectives worked, and the interface applied physical metrics. |
| Decision Explorer | PASS | All 40 windows and 24 parameter choices were available. Tested five windows, the reference and three alternatives, and both objectives. For the earliest reference case, Baseline led on water deficit and Rye cover led on low-cover rainfall exposure. |
| Historical Climate Replay | PASS | Checked earliest/latest navigation limits, window updates, annual reference outcomes, and 2025 precipitation and mean temperature against the archived aggregates. Historical windows are labeled overlapping. |
| Evidence & Uncertainty | PASS | The page rendered source classifications and model caveats. The checksum disclosure opened, the FAO-56 explanation was visible, and the GitHub and methodology links pointed to the corresponding repository resources. GitHub requires reviewer access because the repository is private. |

### 1984–1986 reference case

The source values come from `scenario_metrics.json`. The original archive's eight SHA-256 checks passed independently.

| Rotation | Water deficit source → browser (mm) | Low-cover rainfall exposure source → browser (mm) |
| --- | --- | --- |
| Baseline | 72.605162 → 72.61 | 1731.392222 → 1,731.39 |
| Rye cover | 73.252013 → 73.25 | 1131.272222 → 1,131.27 |
| Wheat + double-crop soybean | 174.977936 → 174.98 | 1350.901333 → 1,350.9 |

The other reference windows checked were 2023–2025, 2003–2005, 1986–1988 (driest by three-year NASA POWER precipitation total, 3,175.64 mm), and 2018–2020 (wettest, 4,377.77 mm). All three displayed water-deficit values matched for each tested window. Low storage, high storage, and early corn planting were sampled against the archived runs.

## Browser and network

Chromium ran at 1440 × 900, 768 × 1024 and 390 × 844. Navigation, mobile layout, keyboard tab order, refresh and the science/demo labels worked. The application emitted no uncaught page errors during the walkthrough. The initial farm load requested the science catalog. Historical JSON loaded on demand.

Controlled HTTP 503 failures on both the catalog and a window produced an error with retry. The window failure removed the previous results while the requested case was unavailable. Both retries recovered without a synthetic fallback. The expected injected 503s were excluded from the ordinary asset check. A separate live map check demonstrated successful external tile requests. The shell verified HTTPS with normal certificate checks. Chromium used a certificate exception for the execution proxy.

## Issue found and correction

- **Low severity — mode switching reset scientific selections.** On live production, select a historical window and low storage in Rotation Comparison, switch to the synthetic demo, then return. Science restored the reference parameter instead of retaining the user's choice. Values remained valid for the case shown, and scientific and synthetic data remained isolated.
- The proposed fix keeps the scientific session mounted while its UI is inactive. Changes are limited to `src/App.tsx`, `src/science/ScienceWorkspace.tsx`, and `tests/scienceWorkspace.test.tsx`. All 23 frontend tests passed, lint and production build passed, and local Chromium confirmed that the alternate parameter survived a round trip. The fix is proposed alongside this report and awaits merge, Vercel deployment, and live retest.

## Recommendation

HINGE can be submitted on the currently tested deployment. The mode-switching issue is a convenience defect and does not change the archived scientific results. If the proposed fix is deployed before submission, rerun the mode round trip against the production alias.

The study area is provisional. NASA POWER is gridded weather, SSURGO is survey-derived, and HLS observations have no hypothetical rotation attribution. The engine provides modeled screening outcomes under documented assumptions. Grant reviewers repository access if they need the scientific source.

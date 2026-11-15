# Verification record

Checked on 2026-11-14 after final remediation.

## Automated

- `npm run build` — passed; TypeScript project build and Vite production bundling completed.
- `npm test` — passed; 3 test files and 17 tests cover seasonal water-window consistency, exact score/component consistency, eligible ranking, planting and cover-crop exclusions, hard water feasibility, refined/no-op boundary behavior, decision states, explorer presets, primary navigation, historical year comparison, API base-path construction, and surfaced HTTP failures.
- `npm run lint` — passed.
- Loaded the Vite development page at `http://127.0.0.1:5173/` in the embedded browser.

## Browser checks

- Opened Farm Intelligence and verified synthetic provenance labels, map, climate/vegetation chart, soil assumptions, and current model readout.
- Navigated among all five primary screens.
- Applied the Dry year preset in the Decision Boundary Explorer; precipitation and irrigation controls updated to −40% and 0 mm, the eligible set changed, and the explorer reported an insufficient state with a refined feasibility-boundary interval.
- Opened Rotation Comparison under the dry preset and verified seasonal water need/supply values and explicit exclusion badges match the explorer's eligibility and scores.
- Changed the farm selector to North Bench; the selected farm changed and its synthetic rainfall summary updated from 181 mm to 205 mm.
- At an embedded viewport width of 419 px, verified the mobile two-column metric grid and bottom-tab navigation; selecting Explorer changed the active screen.

## Limitations

- Browser text and interaction snapshots were available; no screenshot is included as visual evidence.
- The embedded browser preview uses a narrow side panel (419 px). A separate wide desktop viewport was not available for a visual comparison.
- OpenStreetMap tile loading depends on network access. No NASA products, field data, validated predictions, or backend service were available for verification.

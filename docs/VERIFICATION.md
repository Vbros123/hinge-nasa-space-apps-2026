# Verification record

Checked on 2026-11-14.

## Automated

- `npm run build` — passed; TypeScript project build and Vite production bundling completed.
- `npm test` — passed; 3 test files and 9 tests cover score changes, ranking transitions, supported/sensitive/insufficient states, explorer presets, primary navigation, historical year comparison, API base-path construction, and surfaced HTTP failures.
- `npm run lint` — passed.
- `curl --fail http://127.0.0.1:5173/` — Vite development page returned HTTP 200.

## Browser checks

- Opened Farm Intelligence and verified synthetic provenance labels, map, climate/vegetation chart, soil assumptions, and current model readout.
- Navigated among all five primary screens.
- Applied the Dry year preset in the Decision Boundary Explorer; sliders, score ordering, boundary transition message, and decision state updated consistently.
- Changed the farm selector to North Bench; the selected farm changed and its synthetic rainfall summary updated from 181 mm to 205 mm.
- At an embedded viewport width of 419 px, verified the mobile two-column metric grid and bottom-tab navigation; selecting Explorer changed the active screen.

## Limitations

- Browser canvas text and interaction snapshots were available, but its screenshot action returned a black image; no screenshot is included as visual evidence.
- The embedded browser preview uses a narrow side panel (419 px). A separate wide desktop viewport was not available for a visual comparison.
- OpenStreetMap tile loading depends on network access. No NASA products, field data, validated predictions, or backend service were available for verification.

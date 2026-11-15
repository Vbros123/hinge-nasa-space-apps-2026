# Person 4: real environmental result contract

Read `output/real_environment` directly. All eight files are UTF-8 JSON with stable `rotation_a` baseline, `rotation_b` rye cover, and `rotation_c` wheat/double-crop soybean identifiers. Values are numbers or `null` for unavailable results; JSON NaN/Infinity are invalid. Each 3-year `scenario_id` identifies an overlapping historical replay, not a future forecast or independent trial. The eight files:

| File | Main field | Meaning |
|---|---|---|
| `feasible_rotations.json` | `rotations[].reference` | Calendar/management feasibility; assumed constraints remain marked |
| `simulation_results.json` | `results[]` | One reference-parameter record per rotation/window; `metrics` and `by_year` are modeled |
| `scenario_metrics.json` | `rows[]`, `metric_units` | All sensitivity records; canonical units and source classifications in record provenance |
| `sensitivity_results.json` | `results[].delta_vs_reference` | Within-rotation change under a parameter change |
| `robustness_summary.json` | `summary` | Paired historical comparisons and assumption sensitivity; inspect nulls |
| `explanations.json` | structured explanation object | Deterministic comparisons, warnings and limitations |
| `model_manifest.json` | `input_sha256`, `config_sha256`, `excluded_years`, `site`, `soil_scenarios` | Input identity, accepted/excluded years, assumptions and dependency versions |
| `vegetation_context.json` | `observations`, `seasonal_summaries` | 2025 observed HLS NDVI, separate from hypothetical rotation |

`water_deficit_mm` means modeled unmet crop-day ET demand, in mm over three years; `crop_water_demand_mm` is modeled crop-day ET demand. `rainfall_on_crop_days_mm` is observed rain falling during *planned* crop-active days, not infiltrated water. `rainfall_low_cover_index_mm = Σ rain × (1 - modeled living-cover fraction)` is an exposure proxy, not soil loss. `eta_total_mm` and `drainage_mm` cover all days, including fallow; do not subtract them from crop-day demand. All differences must compare the same scenario and parameter set. Show quality/provenance and assumed status with comparisons. Do not label any result field-validated, predict yield/profitability, equate NDVI with ground-cover percent, or use a composite performance score. The previous Phase 2 output lacked crop-day demand/rainfall and HLS context; these are additive fields.

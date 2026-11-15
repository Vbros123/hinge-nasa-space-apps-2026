# Data contract the engine requires (proposed; Person 1's final schema may differ)

All fixtures in `tests/fixtures/mock_environment/` are **MOCK/synthetic**. Nothing here shows that real NASA POWER, HLS or SSURGO data have been integrated.
Compatibility conversions live in one file, `engine/compat.py` (column aliases only). If the final schema differs, change that file and this document.

## 1. weather.parquet (or weather.csv)
One row per calendar day, local date, no time-of-day, no timezone, no duplicates (order irrelevant; the engine sorts).

| Canonical column | Required | Unit (after normalisation) | Accepted aliases (engine/compat.py) |
|---|---|---|---|
| date | yes | calendar date | DATE, day, time, YYYYMMDD |
| temperature_max_c | yes | degC | T2M_MAX, tmax |
| temperature_min_c | yes | degC | T2M_MIN, tmin |
| temperature_mean_c | no (derived as (max+min)/2) | degC | T2M, tmean |
| precipitation_mm | yes | mm/day | PRECTOTCORR, precip_mm |
| relative_humidity_pct | yes for Penman-Monteith | % | RH2M |
| solar_radiation | yes for Penman-Monteith | MJ m-2 day-1 (kWh m-2 day-1 and W m-2 converted if declared) | ALLSKY_SFC_SW_DWN |
| wind_speed | yes for Penman-Monteith | m s-1 at 2 m (km/h, mph, other heights converted if declared) | WS2M |
| data_quality_flags | no | text; any flag containing MISSING or FILL marks the whole year incomplete | quality_flags |

Missing values: NaN or the NASA fill values -999 / -99 become missing. They are never replaced by zero or interpolated. A calendar year is usable only if all 365/366 days are present with no missing or flagged required value; blocks need 3 consecutive usable years. 2026 (partial) is excluded automatically.

Rejected as InvalidInputError: duplicate or unparseable dates, timezone-aware or sub-daily timestamps, negative precipitation, Tmax < Tmin, RH outside 0-100, negative solar or wind, and implausible values (precip > 1000 mm/day, temperature outside -90..60 C, solar > 45 MJ m-2 day-1, wind > 75 m/s). Ambiguous aliases (two candidate columns for one field) are rejected.

## 2. manifest.json
```json
{"provenance": "...", "units": {"temperature": "degC", "precipitation": "mm", "solar_radiation": "MJ/m2/day", "wind_speed": "m/s", "wind_height_m": 2.0},
 "site": {"latitude_deg": 35.51, "elevation_m": 50}}
```
- `units.solar_radiation` and `units.wind_speed` are mandatory (the engine never guesses them; aliases do not imply units). Recognised: temperature degC/K/degF; precipitation mm/in; solar MJ/m2/day, kWh/m2/day, W/m2; wind m/s, km/h, mph; wind_height_m in 0.1..100 (FAO-56 Eq. 47 applied if not 2 m).
- `site` optional; if absent, config defaults are used and the output manifest says `site_from: model_parameters.yaml (assumed)`. latitude must be within +-66 degrees, elevation -400..6000 m.
- `provenance` containing "SYNTHETIC" or "MOCK" triggers `DATA_SYNTHETIC` warnings in explanations.

## 3. soils.json
Preferred: `{"available_water_storage_mm": {"low": 70, "medium": 105, "high": 140}}` (or `available_water_storage_cm`, converted x10). Rules: keys limited to low/medium/high, numeric > 0, low <= medium <= high. Partial information is accepted: parameter sets whose storage scenario is absent are skipped and listed in `model_manifest.json.skipped_parameter_sets`; the `reference` set requires `medium`. If the file has no storage key, illustrative storage (60/100/140 mm) is used and labelled "illustrative". The engine does **not** compute storage from SSURGO horizons/components; that derivation (with its root-depth and component-weighting assumptions) must be supplied by the pipeline.

## 4. vegetation.parquet
Not consumed by this engine. Living cover is a planned-calendar quantity, not NDVI.

## Acceptance criteria for integration with real data
1. `python run_evaluation.py --data data/demo --out output` exits 0 and writes 7 files.
2. `model_manifest.json.data_provenance` names NASA POWER (not SYNTHETIC/MOCK) and lists input SHA-256 hashes.
3. `usable_weather_years` covers the intended record; every excluded year has a reason; `n_historical_blocks` >= 10 (report the actual number).
4. `soil_source` is `soils.json` and storage status is `soil_derived`, not `illustrative`.
5. `site_from` is `data manifest` with Johnston County coordinates and elevation.
6. No `SPINUP_UNAVAILABLE` or `skipped_parameter_sets` entries unless explained.
7. Unit declarations spot-checked by a human against the POWER request (solar radiation unit and wind height especially).
8. Two consecutive runs give byte-identical outputs.
9. Parquet is read with pyarrow in an environment where `tests/test_integration_contract.py::test_parquet_ingestion_matches_csv` is not skipped and passes.
10. A human agronomist has reviewed `config/evidence_register.yaml` before any `feasible` status is shown to a farmer without caveats.

## Command
`python tools/run_mock_pipeline.py` (regenerates the mock inputs, runs the engine, checks that all 7 outputs exist).

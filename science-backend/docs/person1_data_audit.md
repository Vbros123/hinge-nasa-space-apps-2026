# Final environmental bundle audit

The audited input is `data/real_environment`, copied unchanged from Person 1 `runs/final`. `run_integrated.verify` independently recomputes SHA-256 for **all 1,265** paths in the source manifest before modeling; all passed on 2026-11-15. The manifest reports 11/11 automated gates and three real-source integration tests. Those gates do not validate agronomic predictions.

## Inventory and provenance

`weather.parquet`, `weather.json`, `weather_metadata.json`, `soils.json`, `soil_horizons.parquet/json`, `vegetation.parquet/json`, `vegetation_seasonal.parquet/json`, `vegetation_metadata.json`, `vegetation_scenes.parquet/json`, `field.geojson`, `validation_report.json`, `validation_evidence.json`, `integration_tests.txt`, `manifest.json`, archived `raw/power`, `raw/hls`, `raw/ssurgo`, and supporting validation references. The exact file hashes and archived request/response hashes remain in the unmodified source manifest and weather metadata. AOI hash is `ab85b416d2cb42cc36bbf1ebde8d622b35679ff154b3c764cb4eba63ba1fc314`.

POWER daily source-grid reanalysis/satellite products are not station or field measurements. 16,436 calendar rows cover 1981-01-01 through 2025-12-31. Solar radiation is missing on every day in 1981–1983; 42 complete model-ready years remain (1984–2025). No missing values were interpolated. Source flags `[]` mean no recorded flag; 1,095 rows carry missing solar flags and `model_ready=false`. The model rejects any nonempty flag in a candidate year. POWER metadata independently declares °C, mm/day, %, MJ/m²/day, m/s at 2 m, and Local Solar Time.

SSURGO covers 16 mapped units, 36 components; mapunit AOI fractions sum to approximately one, while component fractions sometimes sum below one. All 36 delivered component storage estimates exist, but approximately 10.76% AOI/component mass lacks assignment. Estimates integrate survey AWC to an assumed 100 cm or reported restriction; restrictions and incomplete horizons require review. Capacity is neither measured initial moisture nor crop-specific rooting depth.

HLS has 191 2025 acquisition-date aggregates; 94 are usable, 86 have no valid pixels, and 11 have low valid fraction. Seasonal summaries report median NDVI and gaps. These observations do not identify which crop was planted and cannot validate hypothetical rotations or a historical NDVI series.

Top-level `README.md` and `DELIVERY_STATUS.json` describe the earlier blocked phase; `runs/final/manifest.json` and final validation evidence describe the later populated run. The latter is used after independent hash and schema checks. The original manifest lacks the modeling engine's `units`/`site` contract. `run_integrated.py` derives a separate adapter from archived POWER metadata, preserving the original manifest. Site elevation comes from source grid geometry (50.19 m), not a surveyed field elevation.

**Verdict:** automated source-product readiness for a qualified numerical screening replay; field agronomy and source-grid applicability remain unvalidated.

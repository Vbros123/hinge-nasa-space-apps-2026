# Limitations

- Not a crop model. No yield, nutrient cycling, soil carbon, disease, root growth or long-term soil structure.
- Water deficit is modeled unmet demand in millimetres. It is not crop damage and is not convertible to percent yield loss.
- The rainfall-low-cover index is not rainfall erosivity, runoff or soil loss. Dead residue is not credited. L_t is a planned-calendar function, not NDVI or measured cover.
- Heat exposure counts are descriptive; no sourced crop-specific thresholds are used.
- Legume nitrogen fixation, crop diversification and pest effects are described qualitatively in `warnings` only. No fertilizer credit is computed.
- Historical blocks are stress-test scenarios, not a probability distribution of future weather. Overlapping blocks are not independent.
- Parameter-set comparisons are sensitivity analysis, not confidence intervals, and say nothing about forecast accuracy.
- SSURGO describes mapped components, not field sensors. Storage values here are illustrative until derived from soils.json.
- Bucket model has one layer, no root-depth dynamics, no soil-water stress function, no runoff, no capillary rise or water table.
- Single weather point; no spatial variability. NASA POWER is gridded reanalysis/satellite-derived data, not a field station.
- Crop calendars are one fixed schedule per template; real planting dates vary with weather.
- Several crop windows are assumptions pending verification (agricultural_sources.md).
- Not validated against field observations. Validation here is numerical (conservation, hand calculation, FAO example) only.

## Added in Phase 2
- Calendar `feasible` rests on statewide NASS usual dates and NC State tables read by the build agent; no human review; AG-850 and the NC State Soybean Production Guide were not read directly (see crop_calendar_verification.md).
- Winter wheat Kc stage lengths are unverified; corn and soybean stage rows are non-NC rows from secondary transcriptions of FAO-56 Table 11.
- FAO-56 Kc values are for sub-humid conditions; the humid adjustment is run only as a sensitivity with an assumed RHmin. Kc ini wetting-frequency dependence and the dual-Kc method are not implemented.
- Spin-up is a one-year rotation-independent fallow run (optional); on synthetic weather it changes drainage but not unmet demand.
- Parquet ingestion was NOT tested in the build environment (pyarrow unavailable); the CSV path and the error path were tested.
- The soil contract expects pre-derived low/medium/high storage; deriving it from SSURGO is not implemented.
- All robustness and sensitivity numbers in this repository come from synthetic weather.

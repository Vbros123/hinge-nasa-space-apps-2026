# Scientific methodology (screening-v2; Phase 1 text, see Phase 2 docs for changes)

## What the model is
A transparent daily soil-water bucket driven by FAO-56 reference evapotranspiration and FAO-56 single crop coefficients,
replayed over contiguous historical 3-year weather blocks for three rotation templates. It is a screening comparison tool.
It is not APSIM or DSSAT and makes no yield, nutrient, carbon, disease or erosion prediction.

## Processes represented, and the method used for each
| Process | Method | Reference |
|---|---|---|
| Reference ET | FAO-56 Penman-Monteith, daily, G = 0, RH-mean vapor pressure (Eq. 19) or RHmax/RHmin (Eq. 17) if supplied | FAO-56 Ch. 2 Eq. 6; Ch. 3 Eqs. 7, 8, 11-13, 17, 19, 21-25, 34, 37-40, 47 |
| Crop water demand | ETd = Kc x ET0, piecewise single Kc curve (initial / development / mid / late) | FAO-56 Ch. 6 Eq. 58, Fig. 34; Tables 11-12 |
| Soil water | Bounded bucket: A = max(0, S+P+I-Q); ETa = min(ETd, A); D = max(0, A-ETa-Smax); S' = A-ETa-D | brief C.2-C.3 |
| Fallow / residue | Kc fallow = 0.30 (assumed) x 0.75 residue multiplier (assumed); never zero | model_parameters.yaml |
| Phase 2 additions | winter wheat Kc ini 0.7 (FAO-56 non-frozen); evidence classes in feasibility; optional spin-up; robustness and explainability layers | crop_water_parameter_validation.md, robustness_methodology.md |
| Cover crop demand | Kc 0.40 / 1.00 / 0.40 with wheat-like phenology (ASSUMED; FAO-56 has no cereal-rye cover Kc) | model_parameters.yaml |
| Living cover L_t | Planned calendar: linear 0-1 over 45 days after planting; 0 at harvest; linear decline over 10 days after cover termination | assumed |

Kc stage lengths in FAO-56 Table 11 are generic. The code rescales their proportions to the modeled planting-to-harvest span.

## Daily order of operations
rain and irrigation added, runoff removed (default 0), demand computed, extraction limited by available water, drainage of anything above Smax, storage updated.
Mass balance and 0 <= S <= Smax are asserted every day; a violation raises MassBalanceError and nothing is exported.

## Historical replay
- Source: normalized NASA POWER daily records supplied by the data pipeline. Preferred 1981-2025, using only complete years.
- A year is usable only if every calendar day is present, no required value is missing (-999 fill values become missing), and no quality flag reports missing or filled data.
- Blocks are contiguous overlapping 3-year windows. Days are never shuffled or resampled.
- Every rotation and parameter set sees byte-identical weather in a block (fingerprint `weather_sha256_16` is exported).
- Soil water starts each block at 50% of Smax (assumption; no spin-up). Because all rotations share it, it cancels in paired differences but not in absolute levels.
- Overlapping blocks are correlated. `n_nonoverlapping_blocks_max` in the manifest gives the independent-sample ceiling.

## Metrics (names and units fixed; see `engine/objectives.py`)
`water_deficit_mm` (sum over crop-active days of ETd - ETa), cash/cover subsets, `eta_total_mm`, `drainage_mm`,
`heat_exposure_days_tmax_gt30_cash` and `_gt35_cash` (descriptive, no sourced crop threshold), `living_cover_days`,
`living_cover_equivalent_days`, `rainfall_low_cover_index_mm` (= sum P x (1 - L), exposure proxy only),
`calendar_slack_days_min`. Raw metrics only: no weighting, ranking or probabilities.

## What the model can conclude
Relative, paired differences in modeled water demand satisfaction, drainage and rainfall-during-low-living-cover between rotation
schedules under the same historical weather, and which schedules are calendar-feasible on cited windows.

## What it cannot conclude
Yield, profit, fertilizer savings, soil carbon, pest or disease outcomes, erosion or runoff, or any future probability. See limitations.md.

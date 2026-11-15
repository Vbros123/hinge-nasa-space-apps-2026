# Hinge: scientific explanation for NASA Space Apps judges

## Executive summary
Choosing a crop rotation under changing weather is hard to compare by eye: every option has a calendar, a water budget and a weather history behind it. Hinge's engine puts three rotations (corn-soybean-corn; the same with a cereal-rye winter cover; corn-wheat-double-crop soybean) on **identical historical weather** and reports, for each, whether its schedule is feasible on cited North Carolina calendars, how much crop-water demand a simple soil bucket could not meet, how much rain fell while living cover was low, and whether those comparisons survive changes in uncertain assumptions. It is a transparent screening tool. It does not predict yield, guarantee outcomes, or replace calibrated models such as APSIM or DSSAT.

**Status of this build:** the engine is complete and tested (117 tests; one Parquet test skipped because pyarrow was unavailable in the build environment). It has been exercised only on synthetic and mock inputs. Integration with real NASA POWER, HLS and SSURGO data is pending, and no number in this repository is a Johnston County result.

## Why NASA data
NASA POWER provides gap-free daily weather (temperature, precipitation, humidity, solar radiation, wind) from 1981, which is exactly what a replay of historical stress years needs, and it supplies the radiation and wind that FAO-56 Penman-Monteith requires. HLS vegetation observations can later compare planned with observed living cover. These data are model inputs, not field measurements.

## Method
1. **Feasibility.** Each planting, harvest and cover-termination date is checked against a window from the evidence register. Hard rules (cover-crop tables, the 7-14 day cover-to-corn gap, equipment, markets) can reject a rotation; descriptive windows (USDA NASS usual dates) only raise flags. Rejections come with codes and sources.
2. **Reference ET (FAO-56 Penman-Monteith).**
   ET0 = [0.408 Delta (Rn - G) + gamma (900 / (T + 273)) u2 (es - ea)] / [Delta + gamma (1 + 0.34 u2)]
3. **Crop demand.** ETd = Kc x ET0 with a four-stage piecewise Kc curve (FAO-56 Tables 11-12), fallow Kc never zero.
4. **Soil-water bucket, daily.**
   A = max(0, S + P + I - Q); ETa = min(ETd, A); D = max(0, A - ETa - Smax); S' = A - ETa - D, with 0 <= S <= Smax and mass balance checked every day.
5. **Metrics.** Unmet demand W = sum over crop-active days of (ETd - ETa); rainfall-low-cover index E = sum of P x (1 - L), where L is a planned-calendar living-cover fraction; heat-exposure day counts; planned living-cover days; drainage; calendar slack.
6. **Replay and uncertainty.** Contiguous 3-year blocks of real daily weather, never shuffled; every rotation sees the same block. Twenty-four parameter sets vary storage, planting and termination dates, Kc and stage lengths, fallow/residue/cover assumptions and initial conditions. Results are paired differences and direction counts, not probabilities.
7. **Explanations.** Deterministic templates fill in numbers from the outputs; there is no language model.

## Inputs and outputs
Inputs: weather (daily), manifest (units, site), soil storage (low/medium/high mm), crop and rotation configuration. Outputs: feasibility with reasons, per-block metrics, parameter-set sensitivity, a robustness summary, and per-rotation explanations (seven JSON files).

## Interpreting results
Read paired differences between rotations, not absolute millimetres: absolute demand shifts by +-50 to +-120 mm with storage, planting date and Kc assumptions, while rotation differences are tens of millimetres. Report trade-offs as trade-offs: a cover crop that lowers rainfall-on-low-cover may raise modeled water demand. "Feasible" means calendar-feasible on statewide usual practice and NC State tables, not a field guarantee.

## Why uncertainty matters
The model's own comparisons are cheap to flip if an input is wrong: soil storage is illustrative until SSURGO-derived, cover-crop Kc has no published value, wheat stage lengths are unverified. Hinge shows which conclusions survive those changes and which do not, instead of presenting one number.

## Verification performed
FAO-56 Examples 17 and 18 reproduced (ET0 3.880 vs published 3.9 and independent 3.880142; 5.718 vs 5.7 and independent 5.718284); daily mass conservation to 1e-9 mm on 500 random and several designed stress series; a hand-calculated case; a Phase 1 regression; byte-identical repeat runs. See numerical_validation_phase2.md.

## What it does not do
No yield or profit prediction, no erosion or runoff estimate, no nitrogen credit or soil-carbon change, no forecast, no field validation, no crop-disease modelling.

## What real-world validation would need
1. NASA POWER weather for Johnston County and SSURGO-derived plant-available water capacity with a justified root-zone depth.
2. Review of the evidence register by an NC State agronomist; the AG-850 start-date map and Soybean Production Guide read directly.
3. Comparison of modeled soil-water or ET against local observations (e.g. a lysimeter, eddy-covariance or soil-moisture network) and of planned against HLS-observed cover.
4. Calibration or replacement of the cover-crop Kc, fallow and residue parameters with measurements.
5. For yield or erosion claims, a calibrated crop model or erosion model, which Hinge deliberately does not attempt.

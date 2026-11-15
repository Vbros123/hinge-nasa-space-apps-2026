# Crop water parameter validation (Phase 2, Task 2)

Scope: ETd = Kc x ET0 with the FAO-56 single, piecewise-linear Kc curve. Values were compared with FAO-56 Tables 11 and 12 as reproduced by secondary sources (Clemson LGP, an ASABE irrigation-design chapter, calculators) because the FAO tables themselves could not be page-checked here.

## Kc values (FAO-56 Table 12)
| Crop | Kc ini / mid / end in config | FAO-56 value found | Verdict |
|---|---|---|---|
| Corn (grain) | 0.30 / 1.20 / 0.60 | 0.30 / 1.20 / 0.60 (0.35 if field-dried) | confirmed |
| Soybean | 0.40 / 1.15 / 0.50 | 0.4 / 1.15 / 0.50 | confirmed |
| Winter wheat | **0.7** / 1.15 / 0.25 | ini 0.4 for frozen soils, **0.7 for non-frozen soils**; mid 1.15; end 0.25-0.40 | **Phase 1 error corrected**: 0.4 is the frozen-soil value. Non-frozen assumed for Johnston County (inferred); 0.4 run as sensitivity |

Climate caveat: Table 12 is for sub-humid climates (RHmin about 45%, u2 about 2 m/s). FAO-56 Eq. 62 lowers Kc mid in more humid conditions. Johnston County RHmin is not in our data contract. A humid adjustment set (`kc_mid_humid_adj`: corn 1.165, soybean 1.124, wheat 1.121, assuming u2 = 2 m/s, RHmin = 55%) is run as a sensitivity (labelled `inferred_fao56_eq62`; the RHmin value is an assumption).
Kc ini in FAO-56 also depends on wetting frequency (Fig. 29-30); this is not implemented (limitation).

## Stage lengths (FAO-56 Table 11) and interpolation
| Crop | In config | Retrieved FAO-56 rows | Verdict |
|---|---|---|---|
| Corn | 30/40/50/50 (Phase 2) | Idaho April 30/40/50/50 (170 d); also 20/35/40/30 | Phase 1 value 30/40/50/30 matched no retrieved row; replaced. Alternative 20/35/40/30 run as `corn_stage_alt` |
| Soybean | 20/30/60/25 | Central USA May 20/30-35/60/25 (140 d) | consistent |
| Winter wheat | 30/140/40/30 (`unverified_generic`) | Idaho October 160/75/75/25 (335 d); teaching note citing FAO-56: 20/60/70/30 | **not matched to any retrieved row**; kept for continuity, flagged; both retrieved alternatives run as sensitivities |

None are North Carolina rows. Rows are rescaled proportionally to the modeled planting-to-harvest span (corn 143 d, wheat about 228 d). Because FAO stage lengths include a mid-season plateau at day-centre sampling, a one-day crop evaluates inside the mid stage; tests cover boundaries (first day equals Kc ini, plateau equals Kc mid, no jumps, development rises, late declines, scaling 60-400 d, invalid lengths rejected).

## Fallow, residue, cover crop (no empirical calibration)
| Parameter | Value | Evidence | Status |
|---|---|---|---|
| Fallow Kc | 0.30 | FAO-56 says Kc ini ranges from about 0.1 (dry soil) to above 1 (frequently wetted); 0.30 is a mid value | assumed |
| Residue multiplier | 0.75 | none found | assumed |
| Cover (rye) Kc | 0.40 / 1.00 / 0.40, wheat-like phenology | no published cereal-rye cover Kc found; FAO winter cereals (0.3-0.7 / 1.15 / 0.25) are an analogue, not a measurement | assumed |
| Cover phenology | 30/140/40/30, decoupled from the wheat crop stage override | | assumed |
| Living-cover ramp / decline | 45 d / 10 d | | assumed |
These must not be described as calibrated. Each has a sensitivity parameter set.

## Sensitivity of the comparisons (synthetic weather, 43 blocks; regenerate with `tools/validate_phase2.py`)
Change in each rotation's own mean 3-year modeled unmet demand (mm) relative to the reference set (reference mean about 940 mm):

| Parameter set | rotation_a | rotation_b | rotation_c |
|---|---|---|---|
| low_storage / high_storage (60 / 140 mm vs 100) | +121 / -120 | +123 / -119 | +129 / -116 |
| corn_plant_early / late (-10 / +10 d) | +49 / -52 | +49 / -52 | +49 / -52 |
| kc_mid_humid_adj | -43 | -43 | -48 |
| kc_end_sourced_alt | -35 | -35 | -24 |
| corn_stage_alt | +11 | +12 | +11 |
| wheat_stage_idaho / winter_cereal | 0 | +3 / -2 | +19 / -13 |
| wheat_kc_ini_frozen | 0 | 0 | -3.5 |
| fallow_kc_low / high | -3 / +9 | -7 / +13 | -4 / +7 |
| residue_mult_none / strong | +4 / -2 | +6 / -5 | +4 / -3 |
| cover_kc_low / high | 0 | -5 / +6 | 0 |
| rye_terminate_early / late | 0 | -6 / +11 | 0 |

Findings (model behaviour on synthetic weather, not field evidence):
1. Absolute deficits move by +-50 to +-120 mm with storage, planting date and Kc, an order of magnitude more than the paired differences between rotations (rotation_b +9.7 mm, rotation_c +47 mm vs baseline).
2. The direction of every paired comparison (deficit higher than baseline; rainfall-on-low-cover lower than baseline) did not change under any of the 24 parameter sets. The size of rotation_b's deficit difference is comparable to the rye termination-date effect (-6 to +11 mm), so its magnitude, not its sign, is uncertain.
3. Wheat Kc ini and wheat/corn stage rows matter mostly to rotation_c (up to 19 mm).
4. Cover Kc and ramp assumptions affect rotation_b's deficit by about 5 mm and its living-cover exposure index only through the ramp.

# Model assumptions (screening-v2)

Every assumption is overridable in `config/`. "Covered by" names the parameter set(s) in `config/model_parameters.yaml` that vary it.

| # | Assumption | Value | Status | Covered by sensitivity set |
|---|---|---|---|---|
| 1 | Rainfed; irrigation 0 | | assumed | (not varied) |
| 2 | Runoff not modeled | runoff_fraction 0 | not modeled | (not varied; limitation) |
| 3 | Initial storage at block start | 50% of Smax | assumed | init_storage_25, init_storage_75, spinup_1yr |
| 4 | Soil storage Smax | 60 / 100 / 140 mm, or soils.json values | illustrative until SSURGO-derived | low_storage, high_storage |
| 5 | Site latitude / elevation | 35.51 N, 50 m unless manifest supplies | assumed | (manifest overrides) |
| 6 | Site region (cover-crop tables) | coastal_plain | assumed (Johnston straddles the boundary) | `region: piedmont` is supported and tested |
| 7 | Fallow Kc | 0.30, never zero | assumed | fallow_kc_low (0.15), fallow_kc_high (0.50) |
| 8 | Residue multiplier | 0.75 | assumed | residue_mult_none (1.0), residue_mult_strong (0.5) |
| 9 | Cover-crop Kc | 0.40 / 1.00 / 0.40 | assumed (no published cereal-rye Kc found) | cover_kc_low, cover_kc_high |
| 10 | Cover-crop phenology | wheat-like 30/140/40/30 | assumed | (not varied) |
| 11 | Living-cover fraction L_t | ramp 45 d, decline 10 d | assumed | cover_ramp_fast (30), cover_ramp_slow (60) |
| 12 | Winter wheat Kc ini | 0.7 (non-frozen soils) | sourced value, applicability inferred | wheat_kc_ini_frozen |
| 13 | Corn, wheat, soybean stage lengths | see crop_water_parameter_validation.md | corn and soybean sourced_secondary (non-NC rows); wheat unverified_generic | corn_stage_alt, wheat_stage_idaho, wheat_stage_winter_cereal |
| 14 | Kc mid for humid climate | Table 12 values | sourced for sub-humid | kc_mid_humid_adj |
| 15 | Corn Kc end | 0.60 | sourced | kc_end_sourced_alt (0.35; wheat 0.40) |
| 16 | Cash-crop schedule dates | one central date set per template | assumed within verified windows | corn_plant_early/late, rye_terminate_early/late |
| 17 | Spin-up | none by default; optional 1-year fallow-with-residue | method choice | spinup_1yr |
| 18 | First spring of each block has no cover | | structural | (not varied) |
| 19 | Management defaults | planter, combine, grain drill; herbicide termination; wheat buyer confirmed | demo assumption | tests flip each |
| 20 | Heat exposure | descriptive Tmax > 30 / 35 C counts | no sourced thresholds | (not varied) |
| 21 | Crop-active days | planned planting-to-harvest or termination calendar | assumed | corn/rye date sets |
| 22 | Cover termination to soybean gap | corn rule (7-14 d) applied by analogy | assumed for soybean | (not varied) |

Calendar windows are described in crop_calendar_verification.md; those still `assumed` push a rotation to `feasible_pending_verification`.
Phase 1 values are preserved in `config/phase1_frozen/`.

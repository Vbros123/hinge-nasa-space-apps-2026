# Robustness methodology (Phase 2, Task 6)

Goal: show how stable each rotation comparison is, without claiming probabilities. Implemented in `engine/robustness.py`; outputs in `output/<run>/robustness_summary.json`.

## A. Parameter robustness
24 parameter sets (config/model_parameters.yaml) in categories: soil_storage, cover_termination, corn_planting, kc, kc_stage, fallow_residue, cover_development, initial_storage (including a spin-up variant). Each set is labelled with its evidence status (illustrative, sourced_alternative, sourced_secondary_alternative, inferred_fao56_eq62, assumed_range, method_alternative). Ranges are scenarios, not draws from a distribution.

## B. Historical-scenario robustness
- Every rotation receives byte-identical weather in each block (`weather_sha256_16`; tested).
- Comparisons are **paired**: metric(rotation) - metric(baseline) per block and parameter set.
- Overlapping 3-year blocks are correlated. The engine reports counts ("lower in k of n blocks") and `n_nonoverlapping_blocks_max`; it does not report p-values, confidence intervals, or "probability a rotation wins".

## C. Ranking stability and trade-offs
- `direction_of_mean` (lower / higher / no_difference, tolerance 1e-6 mm) for each rotation, metric and parameter set; `parameter_sets_where_direction_differs_from_reference` lists any flips.
- `range_of_mean_paired_difference_by_category` gives the min and max mean difference within each parameter category.
- `tradeoffs_reference` flags rotations that are lower than baseline on one objective and higher on another (objectives: modeled unmet demand, rainfall-low-cover index). No weighted or composite score exists; conflicting objectives are reported as a trade-off.
- `ranking_stability` lists the order of rotations by mean metric in each parameter set and whether the order ever changes.
- `worst_blocks` names the weather blocks with the highest values and the largest increases over baseline.

## Findings on the synthetic fixture (demonstration only; regenerate with tools/validate_phase2.py)
1. Rotation_b (rye) and rotation_c (wheat / double-crop) had higher modeled unmet demand than baseline (+9.7 and +47.2 mm per 3-year block on average) and much lower rainfall-on-low-cover exposure (-633 and -391 mm). That is a trade-off in both cases, in all 24 parameter sets.
2. No direction flipped under any parameter set, and the rotation ordering by deficit was the same in all sets.
3. Absolute deficits moved by +-50 to +-120 mm under storage, planting date and Kc choices, far more than the between-rotation differences. Absolute deficits should not be quoted; paired differences are the stable quantity.
4. rotation_b's deficit penalty (+9.7 mm) is small relative to rye termination timing (-6 to +11 mm) and cover Kc (-5 to +6 mm). Its sign was stable here; its size is not.
5. Initial storage and 1-year spin-up changed drainage one-for-one with the starting water and left unmet demand unchanged on this fixture.
These are properties of the model on random synthetic weather. They are not evidence about Johnston County.

## What is not done
No Monte Carlo sampling (so no random seed issues), no bootstrapped intervals, no scoring, no claim about forecast accuracy.

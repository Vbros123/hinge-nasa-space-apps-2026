# Real-data scientific validation

The cached final source manifest passed independent SHA-256 checks for all 1,265 listed files. POWER Parquet was actually loaded and row-by-row compared to the 16,436-row JSON companion. The 1981–1983 solar-null years were excluded; 1984–2025 were retained. The model executed 40 overlapping three-year blocks × 3 rotations × 24 parameter sets = 2,880 records; all 120 reference rotation/window combinations were calendar feasible under the stated assumptions. No missing weather was interpolated or zero-filled.

The existing FAO-56 benchmarks, bucket mass-balance/storage bounds, calendar checks, and synthetic Phase 1 regression are exercised by the full suite. Real POWER ET0 across 15,341 retained days has mean 2.841773 mm/day, minimum 0.248361, maximum 8.157306. Example engine ET0: 1984-01-01 0.709446 mm/day, 1984-04-10 1.638463, 1986-09-27 4.117357. A scalar invocation agrees with vector calculation for 1984-01-01; this is an implementation consistency check, not an independent formula derivation. Recalculating ET0 at 0 vs 100 m site elevation changes its daily mean by 0.007053 mm/day and maximum single-day difference by 0.020530 mm/day; this is ET0 sensitivity, not a rerun of every rotation at alternate elevation.

| Rotation | Mean modeled crop ET demand, mm/3 years | Mean POWER rain on planned crop days, mm/3 years | Mean unmet crop ET demand, mm/3 years | Mean rain-on-low-cover index, mm/3 years |
|---|---:|---:|---:|---:|
| A baseline | 1716.72 | 1781.74 | 164.62 | 2110.33 |
| B rye cover | 2046.77 | 2721.08 | 165.03 | 1254.10 |
| C wheat/double soy | 2033.58 | 2357.13 | 159.75 | 1601.90 |

These are means across overlapping historical blocks, not statistical independent estimates, yield, profitability, erosion or recommendations. Crop-day rain is not synonymous with infiltrated supply. Soil capacity scenarios are conditional survey-component sensitivity points (97.0/129.3/170.0 mm), and initial water is assumed. Review the full paired and parameter-set results in `output/real_environment/robustness_summary.json`; apparent advantages can depend on weather and management assumptions. No independent field observation validates crop-specific moisture or crop calendar.

Reference paired differences relative to A: B has +0.414 mm mean modeled deficit (2 higher blocks, 38 equal at output precision) and −856.232 mm rain-on-low-cover index (40 lower blocks); C has −4.864 mm modeled deficit (19 lower, 8 higher, 13 equal) and −508.430 mm rain-on-low-cover index (40 lower). The deficit direction is less stable than the cover-exposure proxy. These comparisons use the same historical block for each rotation.

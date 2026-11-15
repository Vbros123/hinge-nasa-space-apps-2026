# Integration report

## Contributions and architecture

Person 1 archived and validated NASA POWER weather, SSURGO soil information, and 2025 NASA HLS 2.0 NDVI for the demonstration area. Person 2 implemented FAO-56 reference evapotranspiration, a daily soil-water bucket, three rotation calendars, matched three-year historical replay, and sensitivity and robustness analysis. Person 3 delivered the responsive React shell, navigation, charts, map, and synthetic demonstration.

Person 4 verified and joined all eight scientific outputs, prepared static assets, and integrated the full archive grid into the five original navigation destinations. A build-time Python script reads the Phase 3 archive. React reads an index plus one historical-window file at a time. No API or Python compute service is needed to run the site.

## Scientific mapping

| Display | Source or transformation |
| --- | --- |
| Baseline water deficit, 1984–1986, reference | `scenario_metrics.json`, matched to the reference simulation. 72.605162 mm, displayed as 72.61 mm. |
| Baseline annual water deficit in 1986 | `simulation_results.json`, `historical_1984_1986 / rotation_a / by_year / 1986`. 68.573604 mm, displayed as 68.57 mm. Annual responses belong to their parent window. |
| Baseline low-storage deficit change, 1984–1986 | `sensitivity_results.json`, the `low_storage / rotation_a` delta for the same window. +64.6 mm versus reference. |
| Observed weather by year | `weather.parquet` daily precipitation sum and daily mean-temperature arithmetic mean over full model-ready calendar years. |
| Movement between tested leaders | Minimum finite modeled value among calendar-eligible rotations for the selected objective. Exact ties are preserved. A different leader set identifies a tested change relative to the reference. |
| Paired historical differences | Archive summaries filter by objective and parameter set. Differences are alternative minus baseline over matched windows. Overlapping windows share years. |
| NDVI | Usable HLS scene medians come directly from `vegetation_context.json`. Seasonal summaries and quality flags retain archive definitions. |

Crop-water demand is ET demand on crop-active days. Unmet demand is a modeled water deficit. Rainfall on planned crop days is grid rainfall summed where the crop calendar is active. The low-cover rainfall index sums daily rainfall multiplied by one minus modeled living-cover fraction. It is an exposure proxy.

Of 191 HLS observations in the archive, 94 satisfy the usable-scene quality gate. Satellite NDVI measures greenness and has no modeled rotation attribution. SSURGO low, medium and high storage estimates are conditional quantiles of mapped component capacity. The assumed integration depth is 100 cm. Roughly 10.76% of area-weighted map component mass lacked a usable storage estimate.

## Scope and limitations

- One provisional demonstration area and a finite set of precomputed cases.
- 1984–2025 are accepted weather years. 1981–1983 failed source readiness, including missing solar radiation.
- Historical windows overlap. Parameter cases are modeled assumptions. Counts convey neither probabilities nor statistical confidence intervals.
- Weather is gridded. Soil capacity is survey-derived. Crop parameters, equipment, market access, and field applicability have no independent local agronomist confirmation.
- The daily screening model omits runoff and does not estimate yield, profitability, nutrients, carbon, or erosion.

# HINGE integration audit

The starting GitHub main commit was `01a006ad649a446a7c8d3d6e5dd4af0c22bf1380`. The original frontend provided synthetic farm locations, an 88% water-coverage exclusion, composite scoring, synthetic historical scenarios, and an optional HTTP interface whose backend routes were proposals.

The production demonstration uses static, versioned assets. The scientific package already contains a complete discrete grid. The browser selects and compares these cases directly. Arbitrary farm selection and continuous climate or agronomic controls require new scientific runs and source validation. The original synthetic controls remain available in the separate demo workspace.

| Phase 3 file | Archived analysis use |
| --- | --- |
| `feasible_rotations.json` | Rotation calendars, sourced and assumed windows, cited checks, caveats, and scenario-specific feasibility details where published. |
| `simulation_results.json` | Reference metrics, annual replay outcomes, warnings, quality flags, and initial conditions. |
| `scenario_metrics.json` | Canonical metric names, units, and the full historical-window × parameter-set × rotation grid. |
| `sensitivity_results.json` | Changes from reference, matched by historical window and rotation, plus parameter details. |
| `robustness_summary.json` | Paired reference/alternative summaries by parameter and objective, including historical block counts and archived ranking stability. |
| `explanations.json` | Baseline explanations, assumption statuses, warnings, source caveats, and global limitations. |
| `model_manifest.json` | Historical/parameter catalog, input hashes, accepted/excluded years, site metadata, soil, ET method, and evidence review status. |
| `vegetation_context.json` | Observed 2025 HLS NDVI, valid-pixel and scene provenance, coverage flags, and seasonal summaries. |

The adapter preserves rotation IDs, historical window IDs, model-defined feasibility, and original metric units. HLS and modeled cover remain distinct. Calendar feasibility and low water deficit convey different information. A window can have multiple tied leaders, no eligible rotation, or no available value for the selected objective.

The packager verifies the eight archive hashes and the four model input hashes. Reference and sensitivity metrics, feasibility, and assumption status must match the canonical grid. The generated index and per-window records are validated at load time. Invalid requests show an error and retry control.

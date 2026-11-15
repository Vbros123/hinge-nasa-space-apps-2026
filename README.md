# HINGE

HINGE is a crop-rotation screening workspace for NASA Space Apps Challenge 2026, [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/). It helps users compare water and living-cover trade-offs across historical weather and model assumptions for an illustrative Johnston County, NC study area.

| View | What you can do |
| --- | --- |
| Farm intelligence | Inspect the study boundary, NASA POWER coverage, SSURGO storage ranges, and 2025 NASA HLS observations. |
| Rotation comparison | Compare baseline, rye cover, and wheat followed by double-crop soybean under matched historical weather and parameters. |
| Decision explorer | Change the objective or choose a tested parameter set, inspect differences from reference, and see where the leading rotation changes. |
| Historical climate replay | Move through overlapping three-year windows and inspect NASA POWER weather and annual reference model outcomes. |
| Evidence & uncertainty | Inspect source manifests, model assumptions, missing evidence, output hashes, and robustness results. |

The default workspace reads precomputed Phase 3 results. The **Open synthetic demo** control opens the original demonstration with its own controls and illustrative scoring. The archived workspace uses individual physical metrics and calendar eligibility.

## Run locally

```bash
git clone https://github.com/Vbros123/hinge-nasa-space-apps-2026.git
cd hinge-nasa-space-apps-2026
npm ci
npm run dev
npm test
npm run lint
npm run build
npm run preview
```

To see how an assumption changes the decision, open **Decision explorer**, select a historical window and an objective, then switch from **Reference** to a tested soil-storage case. Compare the change from reference and the eligible rotations for that objective.

The [Python scientific engine](science-backend/README.md) includes the calculation source, input contract, tests, and replay instructions. Use the [integration report](docs/INTEGRATION_REPORT.md) for methodology, sources, and release evidence. See the [reproducibility and deployment guide](docs/DEPLOYMENT.md) to regenerate the data and deploy.

Results are conditional screening estimates. Site applicability, farm management and crop parameters require local agronomic review. The model does not predict yield, profit, soil loss, or future weather.

# Architecture

Archived NASA POWER meteorology, USDA SSURGO component and horizon data, and NASA HLS observations feed the Phase 3 Python pipeline. The pipeline calculates reference ET, simulates a daily water balance over rotation calendars, and writes structured model and evidence outputs.

The frontend packager verifies those outputs and publishes a catalog and one data file per historical window. The Vite application loads the catalog once per scientific workspace session and validates each window on request. The historical-window, objective and parameter selections stay synchronized while navigating its five views. The original synthetic workspace has separate state and its own scoring logic.

See the [integration audit](FINAL_INTEGRATION_AUDIT.md) for the full file mapping and [deployment](DEPLOYMENT.md) for build and regeneration commands.

# Frontend data contract

`/science/v1/index.json` uses schema `hinge.science.v1`. The index includes model and environment manifests, source hashes, units, rotation calendars, boundary geometry, annual weather summaries, robustness, explanations and HLS context.

`/science/v1/historical_YYYY_YYYY.json` contains one row per parameter × rotation for the identified window. Rows contain named metrics, assumption status, feasibility and weather identity. Reference rows include annual modeled results. Alternate rows include archived deltas from the same reference rotation and window. Measures are finite numeric values or explicit nulls, with source units in the index.

Unknown windows, incomplete pairs, repeated keys and incompatible values produce an explicit request error. `scripts/package_science.py` is the build-time source-to-asset adapter.

# Data provenance

| Source | Role and classification |
| --- | --- |
| NASA POWER | Archived gridded weather in local solar time. The browser displays aggregates of accepted complete years. |
| USDA SSURGO | Survey-derived conditional root-zone storage estimates from mapped components and horizons. |
| NASA HLS 2.0 | Observed vegetation context in 2025. Valid-pixel screening and scene IDs are retained. |
| Model configuration | Calendar windows, soil and crop assumptions, evidence statuses and management options. |
| Phase 3 scientific outputs | Modeled outcomes and comparisons for matched historical windows. |

The Evidence screen exposes the source manifest, model manifest and all eight output checksums. The [integration audit](FINAL_INTEGRATION_AUDIT.md) describes checksum verification and joins.

The [recorded scientific manifest](../science-backend/provenance/model_manifest.json) and [output digests](../science-backend/provenance/repro_before.sha256) are versioned with the model source. The [replay guide](../science-backend/README.md) explains access to the cached input bundle.

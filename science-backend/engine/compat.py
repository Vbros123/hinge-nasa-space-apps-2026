"""Compatibility conversions between the engine's canonical weather schema and likely upstream names.

ISOLATED on purpose: if Person 1's final schema differs, edit this file (and docs/data_contract_requirements.md), not the engine.
Aliases rename columns only. They never imply units: solar_radiation and wind_speed units must still be declared in manifest.json.
"""
from __future__ import annotations
import pandas as pd

# canonical name -> accepted alternative column names (checked in order, case-insensitive)
COLUMN_ALIASES = {
    "date": ["DATE", "day", "time", "YYYYMMDD"],
    "temperature_max_c": ["T2M_MAX", "tmax", "tmax_c", "temp_max_c"],
    "temperature_min_c": ["T2M_MIN", "tmin", "tmin_c", "temp_min_c"],
    "temperature_mean_c": ["T2M", "tmean", "tmean_c", "temp_mean_c"],
    "precipitation_mm": ["PRECTOTCORR", "PRECTOT", "precip_mm", "prcp_mm", "precipitation"],
    "relative_humidity_pct": ["RH2M", "rh_pct", "rh_mean_pct"],
    "solar_radiation": ["solar_radiation_mj_m2_day", "ALLSKY_SFC_SW_DWN", "srad", "rs"],
    "wind_speed": ["wind_speed_m_s", "WS2M", "wind", "u2"],
    "data_quality_flags": ["quality_flags", "flags"],
}


def apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with canonical column names. Records applied renames in df.attrs['aliases_applied'].

    A canonical column already present is never overwritten. Two alternative names for one canonical column raise ValueError
    (ambiguous upstream schema must be resolved by a human).
    """
    lower = {c.lower(): c for c in df.columns}
    ren, applied = {}, {}
    for canon, alts in COLUMN_ALIASES.items():
        if canon in df.columns:
            continue
        hits = [lower[a.lower()] for a in alts if a.lower() in lower]
        if len(hits) > 1:
            raise ValueError(f"Ambiguous columns for {canon!r}: {hits}")
        if hits:
            ren[hits[0]] = canon
            applied[canon] = hits[0]
    out = df.rename(columns=ren).copy()
    out.attrs["aliases_applied"] = applied
    return out

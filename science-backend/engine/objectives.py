"""Raw environmental metrics (no preference weighting). Names, units and definitions are fixed across rotations."""
from __future__ import annotations
import numpy as np
import pandas as pd

METRIC_UNITS = {
    "crop_water_demand_mm": "mm (modeled ET demand on crop-active days, whole 3-year block)",
    "rainfall_on_crop_days_mm": "mm (observed POWER rainfall during planned crop-active days; not infiltrated supply)",
    "water_deficit_mm": "mm (modeled unmet crop water demand over crop-active days; NOT yield loss)",
    "water_deficit_cash_mm": "mm (subset: cash-crop days)",
    "water_deficit_cover_mm": "mm (subset: cover-crop days)",
    "eta_total_mm": "mm (actual modeled evapotranspiration, whole block)",
    "drainage_mm": "mm (modeled deep drainage above Smax, whole block)",
    "heat_exposure_days_tmax_gt30_cash": "days (descriptive: cash-crop days with Tmax > 30 C; NOT physiological damage)",
    "heat_exposure_days_tmax_gt35_cash": "days (descriptive: cash-crop days with Tmax > 35 C; NOT physiological damage)",
    "living_cover_days": "days (planned calendar: days a cash or cover crop is on the field; NOT NDVI)",
    "living_cover_equivalent_days": "days (sum of modeled living-cover fraction L_t)",
    "rainfall_low_cover_index_mm": "mm (sum P_t * (1 - L_t); exposure proxy, NOT erosivity, runoff or soil loss; residue not credited)",
    "calendar_slack_days_min": "days (smallest harvest/termination-to-next-planting gap in the 3-year schedule)",
}


def compute_environmental_metrics(sim: pd.DataFrame, calendar: pd.DataFrame, weather: pd.DataFrame, feasibility: dict,
                                  thresholds=(30, 35)) -> dict:
    """sim: water-balance frame; calendar: daily crop calendar; weather: block weather (needs temperature_max_c)."""
    cash = (calendar["role"].to_numpy() == "cash")
    cover = (calendar["role"].to_numpy() == "cover")
    alive = calendar["alive"].to_numpy()
    d = sim["deficit_mm"].to_numpy()
    L = calendar["L"].to_numpy()
    p = sim["precip_mm"].to_numpy()
    tmax = weather["temperature_max_c"].to_numpy()
    years = pd.DatetimeIndex(sim["date"]).year
    m = {
        "crop_water_demand_mm": float(sim["etd_mm"].to_numpy()[alive].sum()),
        "rainfall_on_crop_days_mm": float(p[alive].sum()),
        "water_deficit_mm": float(d[alive].sum()),
        "water_deficit_cash_mm": float(d[cash].sum()),
        "water_deficit_cover_mm": float(d[cover].sum()),
        "eta_total_mm": float(sim["eta_mm"].sum()),
        "drainage_mm": float(sim["drainage_mm"].sum()),
        f"heat_exposure_days_tmax_gt{thresholds[0]}_cash": int(((tmax > thresholds[0]) & cash).sum()),
        f"heat_exposure_days_tmax_gt{thresholds[1]}_cash": int(((tmax > thresholds[1]) & cash).sum()),
        "living_cover_days": int(alive.sum()),
        "living_cover_equivalent_days": float(L.sum()),
        "rainfall_low_cover_index_mm": float((p * (1.0 - L)).sum()),
        "calendar_slack_days_min": feasibility.get("calendar", {}).get("calendar_slack_days_min"),
    }
    by_year = {}
    for y in sorted(set(years)):
        sel = years == y
        by_year[int(y)] = {"water_deficit_mm": float(d[alive & sel].sum()), "rainfall_low_cover_index_mm": float((p * (1 - L))[sel].sum())}
    return {"values": m, "by_year": by_year}

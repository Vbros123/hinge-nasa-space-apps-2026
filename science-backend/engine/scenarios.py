"""Historical climate replay: contiguous 3-year blocks, paired across rotations, plus parameter-set sensitivity."""
from __future__ import annotations
import copy, hashlib
import numpy as np
import pandas as pd
from . import MODEL_VERSION, InvalidInputError, MissingInputError
from .crop_calendar import build_daily_calendar, parse_md
from .evapotranspiration import compute_reference_et
from .feasibility import evaluate_rotation_feasibility
from .objectives import compute_environmental_metrics
from .water_balance import simulate_water_balance


def complete_years(weather: pd.DataFrame, required_cols: list[str]) -> tuple[list[int], dict]:
    """A year is usable only if it has every calendar day and no missing/flagged values in required columns."""
    ok, excluded = [], {}
    w = weather.copy()
    w["year"] = w["date"].dt.year
    for y, g in w.groupby("year"):
        n_expected = 366 if pd.Timestamp(year=int(y), month=12, day=31).dayofyear == 366 else 365
        reasons = []
        if len(g) != n_expected or g["date"].nunique() != n_expected:
            reasons.append(f"{len(g)} of {n_expected} days present")
        miss = [c for c in required_cols if c in g and g[c].isna().any()]
        if miss:
            reasons.append(f"missing values in {miss}")
        if g["data_quality_flags"].ne("").any():
            reasons.append("quality flags present")
        if "model_ready" in g and not g["model_ready"].fillna(False).all():
            reasons.append("source model_ready false")
        (excluded.__setitem__(int(y), "; ".join(reasons)) if reasons else ok.append(int(y)))
    return ok, excluded


def build_historical_blocks(weather: pd.DataFrame, block_years: int, required_cols: list[str]):
    """Contiguous overlapping blocks of `block_years` complete years. Days are never shuffled."""
    ok, excluded = complete_years(weather, required_cols)
    okset = set(ok)
    blocks = []
    for y in ok:
        yrs = list(range(y, y + block_years))
        if all(v in okset for v in yrs):
            sl = weather[(weather["date"].dt.year >= yrs[0]) & (weather["date"].dt.year <= yrs[-1])].reset_index(drop=True)
            blocks.append({"scenario_id": f"historical_{yrs[0]}_{yrs[-1]}", "start_year": yrs[0], "years": yrs, "weather": sl})
    return blocks, excluded


def weather_fingerprint(block_weather: pd.DataFrame) -> str:
    h = hashlib.sha256()
    for c in ("precipitation_mm", "et0_mm", "temperature_max_c"):
        h.update(np.ascontiguousarray(block_weather[c].to_numpy(float)).tobytes())
    return h.hexdigest()[:16]


def apply_parameter_set(rotation: dict, crop_library: dict, pset: dict):
    """Return modified deep copies (rotation, crop_library). The original objects are never mutated."""
    rot, lib = copy.deepcopy(rotation), copy.deepcopy(crop_library)
    for cid, ov in (pset.get("kc_overrides") or {}).items():
        for k, v in ov.items():
            if k not in lib["crops"][cid]["water"]:
                raise InvalidInputError(f"kc override {cid}.{k} unknown")
            lib["crops"][cid]["water"][k] = v
    for ov in (pset.get("op_overrides") or []):
        for op in rot["operations"]:
            if op["crop"] == ov["crop"] and op["action"] == ov["action"]:
                parse_md(ov["date"]); op["date"] = ov["date"]
    for sh in (pset.get("shift_days") or []):
        for op in rot["operations"]:
            if op["crop"] == sh["crop"] and op["action"] == sh["action"]:
                m, d = parse_md(op["date"])
                new = pd.Timestamp(2001, m, d) + pd.Timedelta(days=int(sh["days"]))
                op["date"] = f"{new.month:02d}-{new.day:02d}"
    return rot, lib


def apply_parameter_set_full(rotation: dict, crop_library: dict, pset: dict, parameters: dict):
    """Like apply_parameter_set but also returns a modified deep copy of `parameters` (water / cover_function overrides)."""
    rot, lib = apply_parameter_set(rotation, crop_library, pset)
    for cid, st in (pset.get("stage_overrides") or {}).items():
        if set(st) != {"initial", "development", "mid", "late"} or any(v <= 0 for v in st.values()):
            raise InvalidInputError(f"stage override for {cid} must give positive initial/development/mid/late")
        lib["crops"][cid]["water"]["stage_lengths_days"] = dict(st)
    par = copy.deepcopy(parameters)
    for k, v in (pset.get("water_overrides") or {}).items():
        if k not in par["water"]:
            raise InvalidInputError(f"water override {k!r} unknown")
        par["water"][k] = copy.deepcopy(v)
    for k, v in (pset.get("cover_function_overrides") or {}).items():
        if k not in par["cover_function"]:
            raise InvalidInputError(f"cover_function override {k!r} unknown")
        par["cover_function"][k] = v
    return rot, lib, par


def _feasibility_cache(rotations, crop_library, soil, management, parameters, psets):
    cache = {}
    for pid, ps in psets.items():
        for rid, r in rotations.items():
            rot, lib, par = apply_parameter_set_full(r, crop_library, ps, parameters)
            cache[(pid, rid)] = (rot, lib, evaluate_rotation_feasibility(rot, lib, soil, management, par), par)
    return cache


def prepare_weather(weather: pd.DataFrame, parameters: dict, site: dict) -> pd.DataFrame:
    """Attach ET0 (explicit method). Call on complete-year rows only."""
    et = compute_reference_et(weather, parameters["et0"]["method"], site)
    w = weather.copy()
    w["et0_mm"] = et["et0_mm"].values
    w.attrs["et0_method"] = et["et0_method"].iloc[0]
    return w


def spinup_storage(wx: pd.DataFrame, ok_years: set, start_year: int, years: int, smax: float, parameters: dict):
    """Initial storage from `years` complete preceding years of rotation-independent fallow-with-residue simulation.

    Returns (storage_mm or None, info). The same value is used for every rotation (paired fairness).
    """
    need = list(range(start_year - years, start_year))
    if years <= 0:
        return None, {"spinup": "none (documented assumption)"}
    if not all(y in ok_years for y in need):
        return None, {"spinup": "unavailable (no complete preceding year); fallback to initial_storage_fraction", "spinup_years_requested": years}
    sp = wx[wx["date"].dt.year.isin(need)].reset_index(drop=True)
    cal = build_daily_calendar({"rotation_id": "spinup", "operations": [], "residue_retained": True}, pd.DatetimeIndex(sp["date"]), need[0], {"crops": {}}, parameters)
    sim = simulate_water_balance(sp, {"smax_mm": smax}, cal, parameters)
    return float(sim["storage_end_mm"].iloc[-1]), {"spinup": f"fallow-with-residue run over {need[0]}-{need[-1]} from {parameters['water']['initial_storage_fraction']:.0%} of Smax",
                                                  "spinup_years_requested": years}


def replay_historical_scenarios(rotations: dict, weather: pd.DataFrame, soil: dict, parameters: dict, crop_library: dict,
                                management: dict, param_sets: dict | None = None, site: dict | None = None,
                                return_daily: bool = False) -> dict:
    """Run every feasible rotation x historical block x parameter set. All rotations see identical weather per block.

    `weather` must be canonical-unit data (io_utils.normalize_weather). ET0 is computed once per usable year.
    Parameter sets may override Kc, stage lengths, dates, water/cover parameters, storage scenario and spin-up (see config).
    """
    from .objectives import METRIC_UNITS
    psets = param_sets or {"reference": {"storage": "medium_storage", "status": "reference"}}
    site = site or parameters["site"]
    method = parameters["et0"]["method"]
    req = ["temperature_max_c", "temperature_min_c", "precipitation_mm"] + (["relative_humidity_pct", "solar_radiation", "wind_speed"] if method == "penman_monteith" else [])
    ok_years, excluded = complete_years(weather, req)
    wx = prepare_weather(weather[weather["date"].dt.year.isin(ok_years)].reset_index(drop=True), parameters, site)
    blocks, _ = build_historical_blocks(wx, int(parameters["history"]["block_years"]), req)
    if not blocks:
        raise MissingInputError(f"No complete {parameters['history']['block_years']}-year blocks available; excluded years: {excluded}")
    fcache = _feasibility_cache(rotations, crop_library, soil, management, parameters, psets)
    okset = set(ok_years)
    records, daily, skipped = [], {}, {}
    for pid, ps in psets.items():
        storage = soil["scenarios"].get(ps["storage"])
        if storage is None:
            if pid == "reference":
                raise MissingInputError(f"reference parameter set needs soil scenario {ps['storage']!r}, which is not available")
            skipped[pid] = f"soil scenario {ps['storage']!r} not available"
            continue
        smax = float(storage["value"])
        for blk in blocks:
            bw = blk["weather"]
            fp = weather_fingerprint(bw)
            for rid in sorted(rotations):
                rot, lib, feas, par = fcache[(pid, rid)]
                frac = float(par["water"]["initial_storage_fraction"])
                s0, spinfo = spinup_storage(wx, okset, blk["start_year"], int(ps.get("spinup_years", 0)), smax, par)
                init = frac * smax if s0 is None else s0
                warn = {r["code"] for r in feas["reasons"] if r["severity"] in ("warning", "verification")}
                if spinfo["spinup"].startswith("unavailable"):
                    warn.add("SPINUP_UNAVAILABLE")
                rec = {"rotation_id": rid, "scenario_id": blk["scenario_id"], "parameter_set_id": pid,
                       "feasible": feas["feasible"], "feasibility_status": feas["status"], "model_version": MODEL_VERSION,
                       "weather_sha256_16": fp, "metrics": None, "metric_units": None, "by_year": None,
                       "initial_conditions": {"initial_storage_mm": init, "initial_storage_fraction": init / smax, "start_date": str(bw["date"].iloc[0].date()), **spinfo},
                       "parameters": {"soil_storage_capacity_mm": smax, "soil_storage_status": storage["status"],
                                      "kc_overrides": ps.get("kc_overrides"), "stage_overrides": ps.get("stage_overrides"), "op_overrides": ps.get("op_overrides"),
                                      "shift_days": ps.get("shift_days"), "water_overrides": ps.get("water_overrides"),
                                      "cover_function_overrides": ps.get("cover_function_overrides"), "spinup_years": int(ps.get("spinup_years", 0))},
                       "assumption_status": ps.get("status", "unspecified"), "category": ps.get("category"),
                       "warnings": sorted(warn),
                       "data_quality_flags": sorted({f for x in bw["data_quality_flags"].unique() for f in str(x).split(";") if f}),
                       "provenance": {"et0_method": wx.attrs.get("et0_method"), "years": blk["years"],
                                      "assumption_dependencies": feas["assumption_dependencies"]}}
                if feas["feasible"]:
                    cal = build_daily_calendar(rot, pd.DatetimeIndex(bw["date"]), blk["start_year"], lib, par)
                    sim = simulate_water_balance(bw, {"smax_mm": smax}, cal, par, initial_storage_mm=init)
                    res = compute_environmental_metrics(sim, cal, bw, feas, tuple(par["heat_exposure"]["descriptive_thresholds_c"]))
                    rec["metrics"], rec["by_year"], rec["metric_units"] = res["values"], res["by_year"], METRIC_UNITS
                    if return_daily:
                        daily[(pid, blk["scenario_id"], rid)] = (cal, sim)
                else:
                    rec["rejection_reasons"] = [r for r in feas["reasons"] if r["severity"] == "hard"]
                records.append(rec)
    out = {"records": records, "feasibility": {k: v[2] for k, v in fcache.items()}, "blocks": [b["scenario_id"] for b in blocks],
           "excluded_years": excluded, "usable_years": ok_years, "et0_method": wx.attrs.get("et0_method"),
           "skipped_parameter_sets": skipped}
    if return_daily:
        out["daily"] = daily
    return out

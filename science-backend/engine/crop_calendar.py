"""Config loading, rotation templates, and daily crop-calendar construction (Kc, living-cover state)."""
from __future__ import annotations
import copy
import datetime as dt
import yaml
import numpy as np
import pandas as pd
from . import InvalidInputError, MissingInputError


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_crop_library(config_path: str) -> dict:
    lib = load_yaml(config_path)
    if "crops" not in lib or "sources" not in lib:
        raise InvalidInputError("crop library needs 'crops' and 'sources'")
    for cid, c in lib["crops"].items():
        for k in ("role", "family", "water", "planting_window" if c.get("role") == "cash_crop" else "role"):
            if k not in c:
                raise InvalidInputError(f"crop {cid} missing {k}")
        # every window must name an existing source
        for key in ("planting_window", "harvest_window", "termination_window"):
            w = c.get(key)
            if w and w.get("source_id") not in lib["sources"]:
                raise InvalidInputError(f"crop {cid}.{key} references unknown source {w.get('source_id')!r}")
    return lib


def parse_md(md: str) -> tuple[int, int]:
    try:
        m, d = md.split("-")
        dt.date(2001, int(m), int(d))
        return int(m), int(d)
    except Exception as e:
        raise InvalidInputError(f"Invalid MM-DD date {md!r}: {e}")


def md_in_window(md: str, earliest: str, latest: str) -> bool:
    key = lambda s: tuple(parse_md(s))
    a, b, x = key(earliest), key(latest), key(md)
    return (a <= x <= b) if a <= b else (x >= a or x <= b)


def generate_rotation_templates(crop_library: dict, rotations_path: str) -> dict:
    cfg = load_yaml(rotations_path)
    out = {}
    for rid, r in cfg["rotations"].items():
        for op in r["operations"]:
            if op["crop"] not in crop_library["crops"]:
                raise InvalidInputError(f"{rid}: unknown crop {op['crop']!r}")
            if op["action"] not in ("plant", "harvest", "terminate"):
                raise InvalidInputError(f"{rid}: invalid action {op['action']!r}")
            parse_md(op["date"])
            if not (0 <= int(op["year_offset"]) < cfg["horizon_years"]):
                raise InvalidInputError(f"{rid}: year_offset outside horizon")
        out[rid] = {"rotation_id": rid, **copy.deepcopy(r)}
    return out


def operation_date(op: dict, start_year: int) -> pd.Timestamp:
    m, d = parse_md(op["date"])
    return pd.Timestamp(year=start_year + int(op["year_offset"]), month=m, day=d)


def build_periods(rotation: dict, start_year: int) -> list[dict]:
    """Pair plant ops with the next harvest (cash) or terminate (cover) op of the same crop/label."""
    ops = sorted(rotation["operations"], key=lambda o: (o["year_offset"], parse_md(o["date"])))
    periods, open_ = [], {}
    for op in ops:
        key = (op["crop"], op.get("label"))
        when = operation_date(op, start_year)
        if op["action"] == "plant":
            if key in open_:
                raise InvalidInputError(f"{rotation['rotation_id']}: {key} planted twice without end")
            open_[key] = when
        else:
            if key not in open_:
                raise InvalidInputError(f"{rotation['rotation_id']}: {op['action']} of {key} without planting")
            periods.append({"crop": op["crop"], "label": op.get("label"), "start": open_.pop(key), "end": when,
                            "end_action": op["action"]})
    if open_:
        raise InvalidInputError(f"{rotation['rotation_id']}: planted but never ended: {list(open_)}")
    for p in periods:
        if p["end"] <= p["start"]:
            raise InvalidInputError(f"{rotation['rotation_id']}: {p['crop']} ends on/before it starts ({p['start'].date()} -> {p['end'].date()})")
    return sorted(periods, key=lambda p: p["start"])


def kc_curve(n_days: int, kc_ini: float, kc_mid: float, kc_end: float, stage_lengths: dict) -> np.ndarray:
    """FAO-56 piecewise single Kc curve (Fig. 34) with stage lengths rescaled to n_days."""
    if int(n_days) < 1:
        raise InvalidInputError("kc_curve needs at least one day")
    try:
        L = np.array([stage_lengths[k] for k in ("initial", "development", "mid", "late")], dtype=float)
    except KeyError as e:
        raise InvalidInputError(f"stage_lengths missing {e}")
    if not np.isfinite(L).all() or (L <= 0).any():
        raise InvalidInputError("all four stage lengths must be positive")
    frac = L / L.sum()
    edges = np.concatenate([[0.0], np.cumsum(frac)]) * n_days
    x = np.arange(n_days) + 0.5
    kc = np.empty(n_days)
    for i, xi in enumerate(x):
        if xi < edges[1]:
            kc[i] = kc_ini
        elif xi < edges[2]:
            kc[i] = kc_ini + (xi - edges[1]) / (edges[2] - edges[1]) * (kc_mid - kc_ini)
        elif xi < edges[3]:
            kc[i] = kc_mid
        else:
            kc[i] = kc_mid + (xi - edges[3]) / (edges[4] - edges[3]) * (kc_end - kc_mid)
    return kc


def crop_kc_params(crop_id: str, crop_library: dict, parameters: dict):
    """Return (kc_ini, kc_mid, kc_end, stage_lengths, kc_status). Cover crops use flagged assumptions."""
    c = crop_library["crops"][crop_id]
    w = c["water"]
    if c["role"] == "cover_crop":
        cov = parameters["water"]["cover_kc"]
        stages = parameters["water"].get("cover_stage_lengths_days") or crop_library["crops"]["winter_wheat"]["water"]["stage_lengths_days"]   # assumption: wheat-like phenology
        return cov["initial"], cov["mid"], cov["end"], stages, "assumed"
    for k in ("kc_initial", "kc_mid", "kc_end"):
        if w.get(k) is None:
            raise MissingInputError(f"{crop_id}: {k} is unknown; water metrics for this crop are suppressed (no silent substitution)")
        if not (0.0 < float(w[k]) < 2.0):
            raise InvalidInputError(f"{crop_id}: invalid {k}={w[k]!r}")
    return float(w["kc_initial"]), float(w["kc_mid"]), float(w["kc_end"]), w["stage_lengths_days"], w.get("stage_status", "sourced")


def build_daily_calendar(rotation: dict, dates: pd.DatetimeIndex, start_year: int, crop_library: dict, parameters: dict) -> pd.DataFrame:
    """Daily modeled state aligned to `dates`.

    Columns: kc, crop_id, role (cash/cover/fallow), alive (bool: living crop on field), L (living-cover fraction 0..1).
    Fallow days use fallow_kc (x residue multiplier if residue retained): fallow evaporation is never zero.
    L is a planned-calendar function, NOT satellite NDVI and NOT percent soil cover.
    """
    n = len(dates)
    wp = parameters["water"]; cf = parameters["cover_function"]
    fallow_kc = float(wp["fallow_kc"]) * (float(wp["residue_kc_multiplier"]) if rotation.get("residue_retained") else 1.0)
    kc = np.full(n, fallow_kc); crop = np.array([""] * n, dtype=object); role = np.array(["fallow"] * n, dtype=object)
    alive = np.zeros(n, bool); L = np.zeros(n)
    idx = {d: i for i, d in enumerate(dates)}
    for p in build_periods(rotation, start_year):
        c = crop_library["crops"][p["crop"]]
        kc_i, kc_m, kc_e, stages, _ = crop_kc_params(p["crop"], crop_library, parameters)
        span = pd.date_range(p["start"], p["end"] - pd.Timedelta(days=1))   # crop occupies [start, end)
        curve = kc_curve(len(span), kc_i, kc_m, kc_e, stages)
        for j, d in enumerate(span):
            i = idx.get(d)
            if i is None:
                continue
            if alive[i]:                                     # overlap: keep the larger demand; feasibility flags overlaps
                kc[i] = max(kc[i], curve[j])
            else:
                kc[i] = curve[j]
            crop[i] = p["crop"]; role[i] = "cash" if c["role"] == "cash_crop" else "cover"; alive[i] = True
            L[i] = max(L[i], min(1.0, (j + 1) / float(cf["ramp_days"])))
        if p["end_action"] == "terminate":                   # dying cover declines linearly; kc falls to fallow level at once
            for j in range(int(cf["decline_days"])):
                i = idx.get(p["end"] + pd.Timedelta(days=j))
                if i is not None and not alive[i]:
                    L[i] = max(L[i], 1.0 - (j + 1) / float(cf["decline_days"]))
    return pd.DataFrame({"date": dates, "kc": kc, "crop_id": crop, "role": role, "alive": alive, "L": np.clip(L, 0.0, 1.0)})

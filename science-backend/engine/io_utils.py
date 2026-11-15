"""Input loading and unit normalization. Uses manifest unit metadata; refuses to guess units that matter."""
from __future__ import annotations
import hashlib, json, os
import numpy as np
import pandas as pd
from . import MissingInputError, InvalidInputError

REQUIRED_WEATHER = ["date", "temperature_max_c", "temperature_min_c", "precipitation_mm"]
PM_WEATHER = ["relative_humidity_pct", "solar_radiation", "wind_speed"]
FILL_VALUES = (-999.0, -99.0)           # NASA POWER uses -999 for missing


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_weather(data_dir: str) -> pd.DataFrame:
    pq = os.path.join(data_dir, "weather.parquet")
    csv = os.path.join(data_dir, "weather.csv")
    if os.path.exists(pq):
        try:
            df = pd.read_parquet(pq)
        except ImportError as e:
            raise MissingInputError(f"weather.parquet found but no Parquet engine is installed (pip install pyarrow): {e}")
    elif os.path.exists(csv):
        df = pd.read_csv(csv)
    else:
        raise MissingInputError(f"No weather.parquet or weather.csv in {data_dir}")
    return df


def load_manifest(data_dir: str) -> dict:
    p = os.path.join(data_dir, "manifest.json")
    if not os.path.exists(p):
        raise MissingInputError(f"manifest.json not found in {data_dir}; unit metadata is required")
    with open(p) as f:
        return json.load(f)


def _convert_solar(values, unit):
    u = unit.lower().replace(" ", "")
    if u in ("mj/m2/day", "mjm-2day-1", "mj/m^2/day", "mj/m2/d"):
        return values
    if u in ("kwh/m2/day", "kw-hr/m^2/day", "kwh/m^2/day", "kw-hr/m2/day"):
        return values * 3.6
    if u in ("w/m2", "w/m^2"):
        return values * 0.0864        # W m-2 daily mean -> MJ m-2 day-1
    raise InvalidInputError(f"Unrecognized solar_radiation unit: {unit!r}")


def _convert_wind(values, unit):
    u = unit.lower().replace(" ", "")
    if u in ("m/s", "ms-1", "m/sec"):
        return values
    if u in ("km/h", "kmh", "km/hr"):
        return values / 3.6
    if u in ("mph", "mi/h"):
        return values * 0.44704
    raise InvalidInputError(f"Unrecognized wind_speed unit: {unit!r}")


KNOWN_UNITS = {"temperature": {"degc", "c", "celsius", "k", "kelvin", "degf", "f", "fahrenheit"},
               "precipitation": {"mm", "mm/day", "in", "inch", "inches"}}
BOUNDS = {"temperature_c": (-90.0, 60.0), "precipitation_mm": (0.0, 1000.0), "solar_radiation": (0.0, 45.0), "wind_speed": (0.0, 75.0)}


def validate_manifest(manifest: dict) -> dict:
    """Check manifest units and site. Returns {'units': ..., 'site': ...|None}. Raises on malformed or unrecognized values."""
    if not isinstance(manifest, dict):
        raise InvalidInputError("manifest.json must be a JSON object")
    units = manifest.get("units")
    if not isinstance(units, dict):
        raise MissingInputError("manifest.json needs a 'units' object")
    for k, allowed in KNOWN_UNITS.items():
        if k in units and str(units[k]).lower() not in allowed:
            raise InvalidInputError(f"Unrecognized {k} unit {units[k]!r}")
    for k in ("solar_radiation", "wind_speed"):
        if k not in units:
            raise MissingInputError(f"manifest units must declare {k}")
    if "wind_height_m" in units:
        try:
            if not (0.1 <= float(units["wind_height_m"]) <= 100):
                raise ValueError
        except (TypeError, ValueError):
            raise InvalidInputError(f"wind_height_m must be a number in [0.1, 100], got {units['wind_height_m']!r}")
    site = manifest.get("site")
    if site is not None:
        try:
            lat, z = float(site["latitude_deg"]), float(site["elevation_m"])
        except (KeyError, TypeError, ValueError):
            raise InvalidInputError("manifest site needs numeric latitude_deg and elevation_m")
        if not (-66.0 <= lat <= 66.0):
            raise InvalidInputError(f"latitude_deg {lat} outside the supported -66..66 range (FAO-56 daily Ra is not defined near the poles)")
        if not (-400.0 <= z <= 6000.0):
            raise InvalidInputError(f"elevation_m {z} implausible")
    return {"units": units, "site": site}


def normalize_weather(df: pd.DataFrame, units: dict | None, need_pm: bool = True) -> pd.DataFrame:
    """Return a weather frame in canonical units: degC, mm, %, MJ m-2 day-1, m/s at 2 m.

    Fill values (-999) become NaN. NaNs are kept (never zero-filled); completeness is judged per block.
    solar_radiation and wind_speed units must be declared in the manifest.
    """
    from .compat import apply_column_aliases
    units = units or {}
    try:
        df = apply_column_aliases(df)
    except ValueError as e:
        raise InvalidInputError(str(e))
    missing = [c for c in REQUIRED_WEATHER if c not in df.columns]
    if missing:
        raise MissingInputError(f"Weather is missing required columns: {missing}")
    try:
        dates = pd.to_datetime(df["date"], errors="raise")
    except (ValueError, TypeError) as e:
        raise InvalidInputError(f"Unparseable dates in weather: {e}")
    if getattr(dates.dt, "tz", None) is not None:
        raise InvalidInputError("Timezone-aware dates are ambiguous for daily data; supply local calendar dates")
    if (dates != dates.dt.normalize()).any():
        raise InvalidInputError("Weather must be daily: found timestamps with a time-of-day component")
    if dates.isna().any():
        raise InvalidInputError("Missing dates in weather")
    out = pd.DataFrame({"date": dates})
    if out["date"].duplicated().any():
        raise InvalidInputError("Duplicate dates in weather")
    for col in ["temperature_max_c", "temperature_min_c", "precipitation_mm",
                "temperature_mean_c", "relative_humidity_pct", "solar_radiation", "wind_speed"]:
        if col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce").astype(float)
            v = v.where(~v.isin(FILL_VALUES))
            out[col] = v.values
    # temperature / precipitation units (default degC / mm only if not declared otherwise)
    tu = (units.get("temperature") or "degC").lower()
    for col in ("temperature_max_c", "temperature_min_c", "temperature_mean_c"):
        if col in out:
            if tu in ("degc", "c", "celsius"):
                pass
            elif tu in ("k", "kelvin"):
                out[col] = out[col] - 273.15
            elif tu in ("degf", "f", "fahrenheit"):
                out[col] = (out[col] - 32.0) * 5.0 / 9.0
            else:
                raise InvalidInputError(f"Unrecognized temperature unit {tu!r}")
    pu = (units.get("precipitation") or "mm").lower()
    if pu in ("in", "inch", "inches"):
        out["precipitation_mm"] = out["precipitation_mm"] * 25.4
    elif pu not in ("mm", "mm/day"):
        raise InvalidInputError(f"Unrecognized precipitation unit {pu!r}")
    if "temperature_mean_c" not in out:
        out["temperature_mean_c"] = (out["temperature_max_c"] + out["temperature_min_c"]) / 2.0
    if "solar_radiation" in out:
        if "solar_radiation" not in units:
            raise MissingInputError("manifest units must declare solar_radiation unit")
        out["solar_radiation"] = _convert_solar(out["solar_radiation"], units["solar_radiation"])
    if "wind_speed" in out:
        if "wind_speed" not in units:
            raise MissingInputError("manifest units must declare wind_speed unit")
        out["wind_speed"] = _convert_wind(out["wind_speed"], units["wind_speed"])
        h = float(units.get("wind_height_m", 2.0))
        if abs(h - 2.0) > 1e-9:             # FAO-56 Eq. 47
            out["wind_speed"] = out["wind_speed"] * 4.87 / np.log(67.8 * h - 5.42)
    if need_pm:
        absent = [c for c in PM_WEATHER if c not in out]
        if absent:
            raise MissingInputError(f"FAO-56 Penman-Monteith requires columns {absent}")
    if "data_quality_flags" in df.columns:
        out["data_quality_flags"] = df["data_quality_flags"].fillna("").astype(str).replace("[]", "").values
    else:
        out["data_quality_flags"] = ""
    if "model_ready" in df.columns:
        out["model_ready"] = df["model_ready"].fillna(False).astype(bool).values
    # physical validity (only on non-NaN)
    def bad(mask, msg):
        if bool(mask.any()):
            raise InvalidInputError(f"{msg}: {int(mask.sum())} rows, first {out.loc[mask, 'date'].iloc[0].date()}")
    bad(out["precipitation_mm"] < 0, "negative precipitation")
    lo, hi = BOUNDS["precipitation_mm"]; bad(out["precipitation_mm"] > hi, f"precipitation above {hi} mm/day")
    lo, hi = BOUNDS["temperature_c"]
    for c in ("temperature_max_c", "temperature_min_c", "temperature_mean_c"):
        bad((out[c] < lo) | (out[c] > hi), f"{c} outside plausible {lo}..{hi} degC")
    if "solar_radiation" in out:
        bad(out["solar_radiation"] > BOUNDS["solar_radiation"][1], f"solar radiation above {BOUNDS['solar_radiation'][1]} MJ/m2/day")
    if "wind_speed" in out:
        bad(out["wind_speed"] > BOUNDS["wind_speed"][1], f"wind speed above {BOUNDS['wind_speed'][1]} m/s")
    bad(out["temperature_max_c"] < out["temperature_min_c"], "Tmax < Tmin")
    if "relative_humidity_pct" in out:
        bad((out["relative_humidity_pct"] < 0) | (out["relative_humidity_pct"] > 100), "RH outside 0-100")
    if "solar_radiation" in out:
        bad(out["solar_radiation"] < 0, "negative solar radiation")
    if "wind_speed" in out:
        bad(out["wind_speed"] < 0, "negative wind speed")
    return out.sort_values("date").reset_index(drop=True)


def load_soil(path_or_dict, scenarios_fallback: dict | None = None) -> dict:
    """Return {'scenarios': {id: {'value': mm, 'status': ...}}, 'source': ...}.

    Accepted schema in soils.json (verify against Person 1's actual file):
      {"available_water_storage_mm": {"low": x, "medium": y, "high": z}}   # preferred
    If absent, falls back to the illustrative scenarios and says so. Never invents SSURGO values.
    """
    data = None
    if isinstance(path_or_dict, dict):
        data = path_or_dict
    elif path_or_dict and os.path.exists(path_or_dict):
        with open(path_or_dict) as f:
            data = json.load(f)
    if data and isinstance(data.get("available_water_storage_cm"), dict) and "available_water_storage_mm" not in data:
        try:
            data = {**data, "available_water_storage_mm": {k: float(v) * 10.0 for k, v in data["available_water_storage_cm"].items()}}
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"soils.json storage values must be numeric: {e}")
    if data and isinstance(data.get("available_water_storage_mm"), dict):
        s = data["available_water_storage_mm"]
        bad_keys = set(s) - {"low", "medium", "high"}
        if bad_keys:
            raise InvalidInputError(f"soils.json storage keys must be low/medium/high, got extra {sorted(bad_keys)}")
        try:
            sc = {f"{k}_storage": {"value": float(v), "status": "soil_derived"} for k, v in s.items()}
        except (TypeError, ValueError) as e:
            raise InvalidInputError(f"soils.json storage values must be numeric: {e}")
        for k, v in sc.items():
            if not (v["value"] > 0):
                raise InvalidInputError(f"soil storage {k} must be > 0 mm")
        order = [sc[k]["value"] for k in ("low_storage", "medium_storage", "high_storage") if k in sc]
        if order != sorted(order):
            raise InvalidInputError("soils.json storage must satisfy low <= medium <= high")
        return {"scenarios": sc, "source": "soils.json" + ("" if len(sc) == 3 else f" (partial: only {sorted(sc)})")}
    if scenarios_fallback:
        return {"scenarios": scenarios_fallback, "source": "model_parameters.yaml (illustrative; no soil-derived storage found)"}
    raise MissingInputError("No soil water storage available (soils.json lacks available_water_storage_mm and no fallback)")

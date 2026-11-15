"""Reference evapotranspiration.

FAO-56 Penman-Monteith (Allen et al. 1998), daily time step. Equation numbers refer to FAO-56.
Hargreaves-Samani (FAO-56 Eq. 52) is available only when explicitly requested and is labeled approximate.
Inputs must already be in canonical units (see io_utils.normalize_weather):
  degC, mm, relative humidity %, solar radiation MJ m-2 day-1, wind m s-1 at 2 m.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import MissingInputError, InvalidInputError

GSC = 0.0820                 # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9             # Stefan-Boltzmann, MJ K-4 m-2 day-1


def sat_vp(t):               # Eq. 11, kPa
    t = np.asarray(t, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def slope_svp(t):            # Eq. 13, kPa/degC
    t = np.asarray(t, dtype=float)
    return 4098.0 * sat_vp(t) / (t + 237.3) ** 2


def pressure(z):             # Eq. 7, kPa
    return 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26


def psychrometric_constant(p):   # Eq. 8
    return 0.000665 * p


def inverse_rel_dist(doy):   # Eq. 23
    return 1.0 + 0.033 * np.cos(2.0 * np.pi * np.asarray(doy, dtype=float) / 365.0)


def solar_declination(doy):  # Eq. 24
    return 0.409 * np.sin(2.0 * np.pi * np.asarray(doy, dtype=float) / 365.0 - 1.39)


def sunset_hour_angle(lat_rad, decl):    # Eq. 25
    return np.arccos(np.clip(-np.tan(lat_rad) * np.tan(decl), -1.0, 1.0))


def extraterrestrial_radiation(lat_deg, doy):    # Eq. 21, MJ m-2 day-1
    phi = np.deg2rad(lat_deg)
    dr = inverse_rel_dist(doy)
    d = solar_declination(doy)
    ws = sunset_hour_angle(phi, d)
    return (24.0 * 60.0 / np.pi) * GSC * dr * (ws * np.sin(phi) * np.sin(d) + np.cos(phi) * np.cos(d) * np.sin(ws))


def daylight_hours(lat_deg, doy):    # Eq. 34
    return 24.0 / np.pi * sunset_hour_angle(np.deg2rad(lat_deg), solar_declination(doy))


def actual_vapor_pressure(tmax, tmin, rh_mean=None, rh_max=None, rh_min=None):
    """Eq. 17 if RHmax and RHmin are given, else Eq. 19 (RHmean)."""
    if rh_max is not None and rh_min is not None:
        return (sat_vp(tmin) * rh_max / 100.0 + sat_vp(tmax) * rh_min / 100.0) / 2.0
    if rh_mean is None:
        raise MissingInputError("Need RH mean, or RHmax and RHmin, for actual vapor pressure")
    return rh_mean / 100.0 * (sat_vp(tmax) + sat_vp(tmin)) / 2.0


def net_radiation(rs, tmax, tmin, ea, ra, elevation_m, albedo=0.23):
    """Eqs. 38-40 with Rso from Eq. 37. Returns (Rn, Rns, Rnl)."""
    rns = (1.0 - albedo) * rs
    rso = (0.75 + 2e-5 * elevation_m) * ra
    ratio = np.clip(rs / np.where(rso > 0, rso, np.nan), 0.0, 1.0)
    ratio = np.where(np.isnan(ratio), 0.0, ratio)
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2.0 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * ratio - 0.35)
    return rns - rnl, rns, rnl


def et0_penman_monteith(tmax, tmin, rs, u2, lat_deg, elevation_m, doy,
                        rh_mean=None, rh_max=None, rh_min=None, albedo=0.23, g=0.0):
    """FAO-56 Eq. 6, mm/day."""
    tmax = np.asarray(tmax, float); tmin = np.asarray(tmin, float)
    rs = np.asarray(rs, float); u2 = np.asarray(u2, float)
    tmean = (tmax + tmin) / 2.0
    p = pressure(elevation_m)
    gamma = psychrometric_constant(p)
    delta = slope_svp(tmean)
    es = (sat_vp(tmax) + sat_vp(tmin)) / 2.0                          # Eq. 12
    ea = actual_vapor_pressure(tmax, tmin, rh_mean, rh_max, rh_min)
    ra = extraterrestrial_radiation(lat_deg, doy)
    rn, _, _ = net_radiation(rs, tmax, tmin, ea, ra, elevation_m, albedo)
    num = 0.408 * delta * (rn - g) + gamma * 900.0 / (tmean + 273.0) * u2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2)
    return np.maximum(num / den, 0.0)      # negative ET0 is not physical for the screening bucket


def et0_hargreaves_samani(tmax, tmin, lat_deg, doy):
    """FAO-56 Eq. 52 (APPROXIMATE; needs only temperature)."""
    tmax = np.asarray(tmax, float); tmin = np.asarray(tmin, float)
    ra = extraterrestrial_radiation(lat_deg, doy)
    tmean = (tmax + tmin) / 2.0
    return np.maximum(0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0.0)) * 0.408 * ra, 0.0)


def _require(weather: pd.DataFrame, cols):
    absent = [c for c in cols if c not in weather.columns]
    if absent:
        raise MissingInputError(f"ET0 inputs missing columns: {absent}")
    nan_cols = [c for c in cols if weather[c].isna().any()]
    if nan_cols:
        raise MissingInputError(f"ET0 inputs contain missing values in: {nan_cols}. Not zero-filled; exclude those years first.")


def compute_reference_et(weather: pd.DataFrame, method: str, site: dict) -> pd.DataFrame:
    """Return DataFrame[date, et0_mm, et0_method]. `method` must be explicit; no silent fallback."""
    doy = weather["date"].dt.dayofyear.values
    lat, z = float(site["latitude_deg"]), float(site["elevation_m"])
    if method == "penman_monteith":
        _require(weather, ["temperature_max_c", "temperature_min_c", "relative_humidity_pct", "solar_radiation", "wind_speed"])
        rh_max = weather["rh_max_pct"].values if "rh_max_pct" in weather and weather["rh_max_pct"].notna().all() else None
        rh_min = weather["rh_min_pct"].values if "rh_min_pct" in weather and weather["rh_min_pct"].notna().all() else None
        et0 = et0_penman_monteith(weather["temperature_max_c"].values, weather["temperature_min_c"].values,
                                  weather["solar_radiation"].values, weather["wind_speed"].values,
                                  lat, z, doy, rh_mean=weather["relative_humidity_pct"].values,
                                  rh_max=rh_max, rh_min=rh_min)
        label = "FAO-56 Penman-Monteith (RH-mean vapor pressure, Eq. 19)" if rh_max is None else "FAO-56 Penman-Monteith (RHmax/RHmin, Eq. 17)"
    elif method == "hargreaves_samani":
        _require(weather, ["temperature_max_c", "temperature_min_c"])
        et0 = et0_hargreaves_samani(weather["temperature_max_c"].values, weather["temperature_min_c"].values, lat, doy)
        label = "Hargreaves-Samani (FAO-56 Eq. 52) -- APPROXIMATE, temperature only"
    else:
        raise InvalidInputError(f"Unknown ET0 method {method!r}")
    return pd.DataFrame({"date": weather["date"].values, "et0_mm": et0, "et0_method": label})

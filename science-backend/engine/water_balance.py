"""Bounded daily soil-water bucket (screening model; not APSIM/DSSAT).

Order of daily operations (documented, applied identically every day):
  1. Available water       A_t   = max(0, S_t + P_t + I_t - Q_t)
  2. Atmospheric demand    ETd_t = Kc_t * ET0_t
  3. Actual extraction     ETa_t = min(ETd_t, A_t)
  4. Deep drainage         D_t   = max(0, A_t - ETa_t - Smax)
  5. New storage           S_t+1 = A_t - ETa_t - D_t
Runoff Q_t = runoff_fraction * P_t (default 0: runoff is not modeled; no calibrated infiltration data).
Invariants checked every day: mass-balance residual ~ 0 and 0 <= S <= Smax.  Failure raises MassBalanceError.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import MassBalanceError, InvalidInputError, MissingInputError


def check_inputs(precip, et0, kc, smax, irrigation=None):
    for name, a in (("precipitation", precip), ("et0", et0), ("kc", kc)):
        a = np.asarray(a, float)
        if np.isnan(a).any():
            raise MissingInputError(f"{name} contains missing values; refusing to substitute zero")
        if (a < 0).any():
            raise InvalidInputError(f"{name} contains negative values")
    if not (len(precip) == len(et0) == len(kc)):
        raise InvalidInputError("precipitation, et0 and kc must have equal length")
    if not np.isfinite(smax) or smax <= 0:
        raise InvalidInputError(f"Smax must be > 0 mm, got {smax!r}")


def simulate_water_balance(weather: pd.DataFrame, soil: dict, crop_calendar: pd.DataFrame, parameters: dict,
                           initial_storage_mm: float | None = None, irrigation_mm=None) -> pd.DataFrame:
    """weather needs date, precipitation_mm, et0_mm. soil = {'smax_mm': float}. crop_calendar needs kc, role, alive.

    Returns one row per day with all terms. Raises MassBalanceError if an invariant fails.
    """
    smax = float(soil["smax_mm"])
    p = weather["precipitation_mm"].to_numpy(float)
    et0 = weather["et0_mm"].to_numpy(float)
    kc = crop_calendar["kc"].to_numpy(float)
    check_inputs(p, et0, kc, smax)
    n = len(p)
    irr = np.zeros(n) if irrigation_mm is None else np.asarray(irrigation_mm, float)
    rf = float(parameters["water"].get("runoff_fraction", 0.0))
    if not (0.0 <= rf <= 1.0):
        raise InvalidInputError("runoff_fraction must be in [0, 1]")
    tol = float(parameters["water"].get("mass_balance_tolerance_mm", 1e-9))
    s = (float(parameters["water"]["initial_storage_fraction"]) * smax) if initial_storage_mm is None else float(initial_storage_mm)
    if not (0.0 <= s <= smax):
        raise InvalidInputError("initial storage must lie in [0, Smax]")
    S0 = np.empty(n); A = np.empty(n); Q = np.empty(n); ETd = np.empty(n); ETa = np.empty(n); D = np.empty(n); S1 = np.empty(n)
    for t in range(n):
        q = min(rf * p[t], p[t])                      # runoff cannot exceed the rain that generates it
        a = max(0.0, s + p[t] + irr[t] - q)
        etd = kc[t] * et0[t]
        eta = min(etd, a)
        d = max(0.0, a - eta - smax)
        s_new = a - eta - d
        resid = s_new - s - (p[t] + irr[t] - q - eta - d)
        if abs(resid) > tol:
            raise MassBalanceError(f"mass balance residual {resid:.3e} mm on day {t}")
        if s_new < -tol or s_new > smax + tol:
            raise MassBalanceError(f"storage {s_new:.6f} outside [0, {smax}] on day {t}")
        S0[t], A[t], Q[t], ETd[t], ETa[t], D[t], S1[t] = s, a, q, etd, eta, d, s_new
        s = s_new
    out = pd.DataFrame({"date": weather["date"].values, "storage_start_mm": S0, "precip_mm": p, "irrigation_mm": irr,
                        "runoff_mm": Q, "available_mm": A, "et0_mm": et0, "kc": kc, "etd_mm": ETd, "eta_mm": ETa,
                        "drainage_mm": D, "storage_end_mm": S1})
    out["deficit_mm"] = out["etd_mm"] - out["eta_mm"]
    out["mass_residual_mm"] = out["storage_end_mm"] - out["storage_start_mm"] - (out["precip_mm"] + out["irrigation_mm"] - out["runoff_mm"] - out["eta_mm"] - out["drainage_mm"])
    return out

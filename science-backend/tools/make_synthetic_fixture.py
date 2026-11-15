"""SYNTHETIC weather generator for software tests only. NOT NASA data. Never use for agronomic conclusions.

Writes weather.csv + manifest.json (provenance = SYNTHETIC_TEST_FIXTURE) so the pipeline can be exercised
end to end when Person 1's real data/demo/ files are not present.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import pandas as pd


def make_weather(start_year=1981, end_year=2025, partial_year=None, seed=42, lat=35.5):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31")
    if partial_year:
        dates = dates.append(pd.date_range(f"{partial_year}-01-01", f"{partial_year}-06-30"))
    n = len(dates)
    doy = dates.dayofyear.values
    season = np.sin(2 * np.pi * (doy - 110) / 365.0)
    tmean = 15.5 + 11.0 * season + rng.normal(0, 3.0, n)
    dtr = 10.5 + 1.5 * season + rng.normal(0, 1.0, n)
    tmax, tmin = tmean + dtr / 2, tmean - dtr / 2
    wet = np.zeros(n, bool); amt = np.zeros(n)
    for i in range(n):                       # first-order Markov occurrence, gamma amounts (persistence preserved)
        pw = 0.45 if (i > 0 and wet[i - 1]) else 0.22
        wet[i] = rng.random() < pw
        if wet[i]:
            amt[i] = rng.gamma(0.7, 11.0)
    rh = np.clip(68 + 8 * wet - 6 * season + rng.normal(0, 7, n), 25, 100)
    from engine.evapotranspiration import extraterrestrial_radiation
    ra = extraterrestrial_radiation(lat, doy)
    rs = np.clip(ra * (0.72 - 0.28 * wet + rng.normal(0, 0.05, n)), 2.0, None)
    wind = np.clip(2.2 + rng.normal(0, 0.7, n), 0.3, None)
    return pd.DataFrame({"date": dates, "temperature_mean_c": tmean, "temperature_max_c": tmax, "temperature_min_c": tmin,
                         "precipitation_mm": amt, "relative_humidity_pct": rh, "solar_radiation": rs, "wind_speed": wind,
                         "data_quality_flags": ""})


MANIFEST = {"provenance": "SYNTHETIC_TEST_FIXTURE", "note": "Random weather for software tests. Not NASA POWER.",
            "units": {"temperature": "degC", "precipitation": "mm", "solar_radiation": "MJ/m2/day", "wind_speed": "m/s", "wind_height_m": 2.0},
            "site": {"latitude_deg": 35.5, "elevation_m": 50}}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synthetic_test")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    make_weather(partial_year=2026).to_csv(os.path.join(a.out, "weather.csv"), index=False)
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(MANIFEST, f, indent=2)
    with open(os.path.join(a.out, "soils.json"), "w") as f:
        json.dump({"note": "synthetic: no soil-derived storage; engine falls back to illustrative scenarios"}, f)
    print("wrote synthetic fixture to", a.out)

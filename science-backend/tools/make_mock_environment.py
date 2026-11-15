"""Write a MOCK environment (weather, manifest, soils) that follows the documented proposed data contract.

All content is synthetic/mock. It exists to exercise ingestion and the engine; it is not NASA POWER, HLS or SSURGO data.
Parquet is written too when pyarrow is installed; otherwise the script says so.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools.make_synthetic_fixture import make_weather

MANIFEST = {"provenance": "MOCK_ENVIRONMENT_SYNTHETIC (not NASA POWER / SSURGO)",
            "units": {"temperature": "degC", "precipitation": "mm", "solar_radiation": "MJ/m2/day", "wind_speed": "m/s", "wind_height_m": 2.0},
            "site": {"latitude_deg": 35.51, "elevation_m": 50}}
SOILS = {"note": "MOCK soil storage scenarios, not derived from SSURGO", "available_water_storage_mm": {"low": 70, "medium": 105, "high": 140}}


def write(out):
    os.makedirs(out, exist_ok=True)
    w = make_weather(1990, 2002, partial_year=2003, seed=7, lat=35.51)
    w.to_csv(os.path.join(out, "weather.csv"), index=False)
    try:
        w.to_parquet(os.path.join(out, "weather.parquet"), index=False)
        parquet = True
    except ImportError:
        parquet = False
    json.dump(MANIFEST, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    json.dump(SOILS, open(os.path.join(out, "soils.json"), "w"), indent=2)
    return parquet


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="tests/fixtures/mock_environment")
    a = ap.parse_args()
    print("parquet written" if write(a.out) else "pyarrow not installed: weather.parquet NOT written (CSV only)")

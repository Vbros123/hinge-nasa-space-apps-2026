"""Package the verified Phase 3 outputs for static hosting."""
import argparse
import hashlib
import json
import math
from calendar import isleap

import pyarrow.parquet as parquet
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive_root", type=Path)
args = parser.parse_args()
root = args.archive_root
source = root / "output/real_environment"
target = Path(__file__).resolve().parents[1] / "public/science/v1"
target.mkdir(parents=True, exist_ok=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def reject_constant(value):
    raise ValueError(f"Invalid JSON number {value}")

def read(path):
    return json.loads(path.read_bytes(), parse_constant=reject_constant)

def write(name, value):
    (target / name).write_text(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")

outputs = {}
hashes = {}
for line in (source / "repro_before.sha256").read_text().splitlines():
    expected, relative = line.split()
    path = root / relative
    if digest(path) != expected:
        raise ValueError(f"Checksum mismatch for {path}")
    outputs[path.stem] = read(path)
    hashes[path.name] = expected

manifest = outputs["model_manifest"]
environment = root / "data/real_environment"
for name, expected in manifest["input_sha256"].items():
    candidates = list(environment.rglob(name))
    if not any(digest(path) == expected for path in candidates):
        raise ValueError(f"Input checksum mismatch for {name}")

environment_manifest = read(environment / "manifest.json")
boundary = read(environment / "field.geojson")
if boundary["properties"]["polygon_id"] != manifest["data_provenance"]["polygon_id"]:
    raise ValueError("Boundary and model polygon IDs differ")

weather_columns = ["year", "date", "precipitation_mm", "temperature_mean_c", "model_ready"]
annual_weather = {year: [] for year in manifest["usable_weather_years"]}
for row in parquet.read_table(environment / "weather.parquet", columns=weather_columns).to_pylist():
    if row["year"] in annual_weather:
        annual_weather[row["year"]].append(row)
weather_summary = {}
for year, rows in annual_weather.items():
    days = 365 + isleap(year)
    if len(rows) != days or len({row["date"] for row in rows}) != days or not all(row["model_ready"] for row in rows):
        raise ValueError(f"Incomplete accepted weather year {year}")
    weather_summary[year] = {
        "precipitationMm": round(math.fsum(row["precipitation_mm"] for row in rows), 6),
        "meanTemperatureC": round(math.fsum(row["temperature_mean_c"] for row in rows) / days, 6),
        "days": days,
    }

def row_key(row):
    return (row["scenario_id"], row["parameter_set_id"], row["rotation_id"])

scenarios = outputs["scenario_metrics"]
simulations = {row_key(row): row for row in outputs["simulation_results"]["results"]}
sensitivity = {row_key(row): row for row in outputs["sensitivity_results"]["results"]}
rotation_ids = [row["rotation_id"] for row in outputs["feasible_rotations"]["rotations"]]
windows = {scenario: [] for scenario in manifest["scenario_ids"]}
seen = set()
for row in scenarios["rows"]:
    key = row_key(row)
    if key in seen or key[1] not in manifest["parameter_sets"] or key[2] not in rotation_ids:
        raise ValueError(f"Unexpected scenario row {key}")
    seen.add(key)
    detail = (simulations if key[1] == "reference" else sensitivity)[key]
    if any(detail[field] != row[field] for field in ["metrics", "feasible", "assumption_status"]):
        raise ValueError(f"Conflicting model results for {key}")
    windows[key[0]].append({
        **row,
        **{k: detail[k] for k in (
            "by_year", "delta_vs_reference", "warnings", "data_quality_flags",
            "feasibility_status", "parameters", "initial_conditions",
        ) if k in detail},
    })

expected = len(rotation_ids) * len(manifest["parameter_sets"])
if any(len(rows) != expected for rows in windows.values()):
    raise ValueError("Incomplete scenario grid")

for scenario, rows in windows.items():
    write(f"{scenario}.json", rows)

write("index.json", {
    "schema": "hinge.science.v1",
    "manifest": manifest,
    "environment": environment_manifest,
    "boundary": boundary,
    "outputHashes": hashes,
    "annualWeather": weather_summary,
    "units": scenarios["metric_units"],
    "rotations": outputs["feasible_rotations"]["rotations"],
    "explanations": outputs["explanations"],
    "robustness": outputs["robustness_summary"],
    "vegetation": outputs["vegetation_context"],
})

#!/usr/bin/env python3
"""One-command scientific evaluation from cached input files.

    python run_evaluation.py --data data/demo --out output
    python run_evaluation.py --data data/synthetic_test --out output/synthetic_smoke   # software smoke test only

Outputs are deterministic (no timestamps, no random numbers).
"""
import argparse, json, os, sys, copy, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import MODEL_VERSION
from engine.io_utils import load_weather, load_manifest, normalize_weather, load_soil, sha256_file, validate_manifest
from engine.robustness import robustness_summary, ranking_stability
from engine.explainability import explain_all
from engine.crop_calendar import load_crop_library, load_yaml, generate_rotation_templates
from engine.scenarios import replay_historical_scenarios


def _round(o, nd=6):
    if isinstance(o, float):
        if not math.isfinite(o):
            return None
        return round(o, nd)
    if isinstance(o, dict):
        return {str(k): _round(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v, nd) for v in o]
    return o


def _dump(obj, path):
    with open(path, "w") as f:
        json.dump(_round(obj), f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def run(data_dir, out_dir, config_dir=None, management_path=None, baseline="rotation_a"):
    cfg = config_dir or os.path.join(HERE, "config")
    P = load_yaml(os.path.join(cfg, "model_parameters.yaml"))
    lib = load_crop_library(os.path.join(cfg, "crops_nc.yaml"))
    rots = generate_rotation_templates(lib, os.path.join(cfg, "rotations_nc.yaml"))
    manifest = load_manifest(data_dir)
    validate_manifest(manifest)
    weather = normalize_weather(load_weather(data_dir), manifest.get("units"), need_pm=P["et0"]["method"] == "penman_monteith")
    soil = load_soil(os.path.join(data_dir, "soils.json"), P["soil_storage_scenarios_mm"])
    site = copy.deepcopy(P["site"])
    site_from = "model_parameters.yaml (assumed)"
    if isinstance(manifest.get("site"), dict) and {"latitude_deg", "elevation_m"} <= set(manifest["site"]):
        site.update(manifest["site"]); site_from = manifest.get("site_source", "data manifest")
    mgmt = P["management_defaults"]
    if management_path:
        with open(management_path) as f:
            mgmt = json.load(f)
    res = replay_historical_scenarios(rots, weather, soil, P, lib, mgmt, P["parameter_sets"], site=site)
    recs = res["records"]
    summary = robustness_summary(recs, baseline)
    provenance = manifest.get("provenance", "unspecified (see input manifest)")
    expl = explain_all(res, summary, rots, P, lib, soil, baseline, provenance)
    ref = [r for r in recs if r["parameter_set_id"] == "reference"]
    os.makedirs(out_dir, exist_ok=True)

    feas = {}
    for (pid, rid), f in sorted(res["feasibility"].items()):
        feas.setdefault(rid, {"rotation_id": rid, "reference": None, "other_parameter_sets": {}})
        if pid == "reference":
            feas[rid]["reference"] = f
        elif f["status"] != res["feasibility"][("reference", rid)]["status"]:
            feas[rid]["other_parameter_sets"][pid] = {"status": f["status"], "hard_reasons": [r for r in f["reasons"] if r["severity"] == "hard"]}
    _dump({"model_version": MODEL_VERSION, "rotations": [feas[k] for k in sorted(feas)],
           "legend": {"feasible": "all checks passed on sourced values", "feasible_pending_verification": "no hard failure; relies on assumed values listed in assumption_dependencies/reasons",
                      "infeasible": "a hard constraint failed; see reasons with severity=hard"}}, os.path.join(out_dir, "feasible_rotations.json"))

    _dump({"model_version": MODEL_VERSION, "parameter_set_id": "reference", "results": ref}, os.path.join(out_dir, "simulation_results.json"))

    rows = [{"rotation_id": r["rotation_id"], "scenario_id": r["scenario_id"], "parameter_set_id": r["parameter_set_id"],
             "feasible": r["feasible"], "weather_sha256_16": r["weather_sha256_16"], "metrics": r["metrics"],
             "assumption_status": r["assumption_status"]} for r in recs]
    from engine.objectives import METRIC_UNITS
    _dump({"model_version": MODEL_VERSION, "metric_units": METRIC_UNITS, "rows": rows,
           "note": "Raw scientific metrics only. No preference weighting, ranking or probabilities. Blocks overlap and are not independent samples."},
          os.path.join(out_dir, "scenario_metrics.json"))

    refidx = {(r["rotation_id"], r["scenario_id"]): r for r in ref}
    sens = []
    for r in recs:
        if r["parameter_set_id"] == "reference":
            continue
        base = refidx.get((r["rotation_id"], r["scenario_id"]))
        s = {k: r[k] for k in ("rotation_id", "scenario_id", "parameter_set_id", "parameters", "metrics", "assumption_status", "feasible", "warnings")}
        if r["metrics"] and base and base["metrics"]:
            s["delta_vs_reference"] = {k: (r["metrics"][k] - base["metrics"][k]) for k in r["metrics"]
                                       if isinstance(r["metrics"][k], (int, float)) and isinstance(base["metrics"][k], (int, float))}
        else:
            s["delta_vs_reference"] = None
            s["rejection_reasons"] = r.get("rejection_reasons")
        sens.append(s)
    _dump({"model_version": MODEL_VERSION, "results": sens,
           "note": "Parameter-set comparisons are model sensitivity, not confidence intervals or probabilities."}, os.path.join(out_dir, "sensitivity_results.json"))

    _dump({"model_version": MODEL_VERSION, "summary": summary, "ranking_stability_water_deficit": ranking_stability(recs, "water_deficit_mm"),
           "ranking_stability_rainfall_low_cover": ranking_stability(recs, "rainfall_low_cover_index_mm")}, os.path.join(out_dir, "robustness_summary.json"))
    _dump(expl, os.path.join(out_dir, "explanations.json"))
    inputs = {}
    for fn in ("weather.parquet", "weather.csv", "soils.json", "manifest.json", "vegetation.parquet"):
        p = os.path.join(data_dir, fn)
        if os.path.exists(p):
            inputs[fn] = sha256_file(p)
    n_years = len(res["usable_years"])
    _dump({"model_version": MODEL_VERSION,
           "data_provenance": manifest.get("provenance", "unspecified (see input manifest)"),
           "input_sha256": inputs, "config_sha256": {fn: sha256_file(os.path.join(cfg, fn)) for fn in ("crops_nc.yaml", "rotations_nc.yaml", "model_parameters.yaml")},
           "et0_method": res["et0_method"], "site": site, "site_from": site_from,
           "soil_source": soil["source"], "soil_scenarios": soil["scenarios"],
           "usable_weather_years": res["usable_years"], "excluded_years": res["excluded_years"],
           "n_historical_blocks": len(res["blocks"]), "n_nonoverlapping_blocks_max": n_years // P["history"]["block_years"],
           "statistical_note": "Overlapping 3-year blocks are strongly correlated; do not treat n_historical_blocks as an independent sample size.",
           "scenario_ids": res["blocks"], "skipped_parameter_sets": res.get("skipped_parameter_sets", {}),
           "dependencies": {m: __import__(m).__version__ for m in ("numpy", "pandas", "yaml", "pyarrow")}, "python": sys.version.split()[0],
           "aliases_note": "column aliases (engine/compat.py) are applied silently only to column names, never to units", "parameter_sets": P["parameter_sets"], "management": mgmt,
           "assumed_parameters": {"initial_storage_fraction": P["water"]["initial_storage_fraction"], "runoff": "not modeled (runoff_fraction=%s)" % P["water"]["runoff_fraction"],
                                  "cover_kc": P["water"]["cover_kc"], "fallow_kc": P["water"]["fallow_kc"], "residue_kc_multiplier": P["water"]["residue_kc_multiplier"],
                                  "cover_function": P["cover_function"], "crop_windows_marked_assumed": sorted(
                                      f"{c}.{k}" for c, v in lib["crops"].items() for k in ("planting_window", "harvest_window") if v.get(k, {}).get("status") == "assumed")},
           "limitations": ["Screening water bucket; not APSIM/DSSAT. No yield, nutrient, carbon, disease or erosion prediction.",
                           "Historical weather blocks are stress-test scenarios, not forecast probabilities.",
                           "Water deficit is modeled unmet demand, not crop damage."],
           "review_status": "crop parameters unverified by a human reviewer"}, os.path.join(out_dir, "model_manifest.json"))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/demo")
    ap.add_argument("--out", default="output")
    ap.add_argument("--config", default=None)
    ap.add_argument("--management", default=None, help="optional JSON overriding management defaults")
    ap.add_argument("--baseline", default="rotation_a")
    a = ap.parse_args()
    r = run(a.data, a.out, a.config, a.management, a.baseline)
    print(f"{len(r['records'])} simulation records; {len(r['blocks'])} historical blocks; excluded years: {r['excluded_years']}")
    print("wrote 7 files to", a.out)

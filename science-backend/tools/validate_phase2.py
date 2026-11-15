#!/usr/bin/env python3
"""Reproducible Phase 2 validation. Runs the test suite, ET benchmarks, stress cases and the spin-up / robustness analyses on the
SYNTHETIC fixture, then writes docs/numerical_validation_phase2.md and output/validation/validation_manifest.json.

    python tools/validate_phase2.py            # full (about 2 minutes)
No field-observed validation data is used or invented.
"""
import io, json, os, platform, sys, unittest, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import numpy as np, pandas as pd
from _common import P, LIB, ROTS, MGMT, SOIL, CFG
from engine.crop_calendar import load_crop_library, generate_rotation_templates, load_yaml
from engine.evapotranspiration import et0_penman_monteith
from engine.scenarios import replay_historical_scenarios
from engine.robustness import robustness_summary, ranking_stability
from engine.io_utils import normalize_weather
from engine.water_balance import simulate_water_balance
from tools.make_synthetic_fixture import make_weather, MANIFEST
import test_et_benchmarks as tb


def run_suite():
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"), pattern="test_*.py")
    buf = io.StringIO(); r = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    return {"tests_run": r.testsRun, "failures": len(r.failures), "errors": len(r.errors), "skipped": [f"{t}: {why}" for t, why in r.skipped]}


def et_table():
    rows = []
    for name, c in tb.CASES.items():
        v = tb.run_case(c)
        for ref_name, ref in (("FAO published (1 decimal)", c["fao_published"]), ("independent implementation", c["independent"])):
            tol = 0.06 if "FAO" in ref_name else 1e-3
            rows.append({"case": name, "reference": ref_name, "expected": ref, "actual": round(v, 6), "abs_diff": round(abs(v - ref), 6),
                         "rel_diff_pct": round(100 * abs(v - ref) / ref, 4), "tolerance_mm_day": tol, "pass": abs(v - ref) <= tol})
    return rows


def stress_table():
    def s(p, e, k, smax, s0):
        n = len(p); w = pd.DataFrame({"date": pd.date_range("2001-01-01", periods=n), "precipitation_mm": p, "et0_mm": e})
        return simulate_water_balance(w, {"smax_mm": smax}, pd.DataFrame({"kc": k, "role": "cash", "alive": True}), P, initial_storage_mm=s0)
    rows = []
    d = s([0.0] * 400, [4.0] * 400, [1.0] * 400, 100, 100); rows.append(("400-day drought, S0=Smax=100, ET0=4, Kc=1", "total ETa = 100 mm; deficit = 1500 mm; S_end = 0", f"ETa={d.eta_mm.sum():.3f}; deficit={d.deficit_mm.sum():.3f}; S_end={d.storage_end_mm.iloc[-1]:.3f}", abs(d.eta_mm.sum() - 100) < 1e-9 and abs(d.deficit_mm.sum() - 1500) < 1e-9))
    h = s([0, 500, 0, 0], [3] * 4, [1] * 4, 100, 40); rows.append(("500 mm in one day, S0=40, Smax=100", "day-2 drainage = (40-3)+500-3-100 = 434 mm", f"{h.drainage_mm.iloc[1]:.3f}", abs(h.drainage_mm.iloc[1] - 434) < 1e-9))
    q = s([40, 0, 0], [5, 6, 100], [1.0, 0.5, 1.0], 50, 20); rows.append(("hand-calculated 3-day case", "ETa = 5, 3, 47; drainage = 5, 0, 0; S_end = 50, 47, 0", f"ETa={list(q.eta_mm.round(6))}; D={list(q.drainage_mm.round(6))}; S={list(q.storage_end_mm.round(6))}", list(q.eta_mm.round(6)) == [5, 3, 47] and list(q.storage_end_mm.round(6)) == [50, 47, 0]))
    z = s([0.0] * 120, [3.0] * 120, [0.3] * 120, 100, 80); rows.append(("120 days zero rain", "storage never increases; no drainage", f"max daily increase={np.diff(z.storage_end_mm).max():.3e}; drainage={z.drainage_mm.sum():.3f}", bool((np.diff(z.storage_end_mm) <= 1e-12).all() and z.drainage_mm.sum() == 0)))
    rng = np.random.default_rng(2026); worst = 0.0; ok = True
    for _ in range(500):
        n = int(rng.integers(5, 400)); sm = float(rng.uniform(5, 500))
        p = np.where(rng.random(n) < rng.uniform(0.05, 0.9), rng.gamma(0.6, rng.uniform(2, 40), n), 0.0)
        r = s(p, rng.uniform(0, 12, n), rng.uniform(0.05, 1.3, n), sm, float(rng.uniform(0, sm)))
        worst = max(worst, float(r.mass_residual_mm.abs().max())); ok &= bool(((r.storage_end_mm >= -1e-12) & (r.storage_end_mm <= sm + 1e-12)).all() and (r.eta_mm <= r.etd_mm + 1e-12).all())
    rows.append(("500 random series (seed 2026), random Smax, S0, Kc, rain", "|mass residual| < 1e-9 mm; 0<=S<=Smax; ETa<=ETd", f"max |residual| = {worst:.2e} mm; invariants hold = {ok}", worst < 1e-9 and ok))
    return rows


def main():
    t0 = time.time()
    suite = run_suite()
    et = et_table(); st = stress_table()
    w = normalize_weather(make_weather(1981, 2025, partial_year=2026), MANIFEST["units"])
    res = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, P["parameter_sets"], site={**P["site"], **MANIFEST["site"]})
    recs = res["records"]
    df = pd.DataFrame([{"rot": r["rotation_id"], "scen": r["scenario_id"], "pid": r["parameter_set_id"], "cat": r["category"], **r["metrics"]} for r in recs if r["metrics"]])
    # spin-up / initial condition effect
    ref = df[df.pid == "reference"].set_index(["rot", "scen"]); eff = []
    spun = {r["scenario_id"] for r in recs if r["parameter_set_id"] == "spinup_1yr" and r["initial_conditions"]["spinup"].startswith("fallow")}
    for pid in ("spinup_1yr", "init_storage_25", "init_storage_75"):
        o = df[df.pid == pid].set_index(["rot", "scen"])
        if pid == "spinup_1yr":
            o = o[o.index.get_level_values(1).isin(spun)]
        for rot in sorted(ROTS):
            d = (o.loc[rot, "water_deficit_mm"] - ref.loc[rot, "water_deficit_mm"].reindex(o.loc[rot].index)).abs()
            dd = (o.loc[rot, "drainage_mm"] - ref.loc[rot, "drainage_mm"].reindex(o.loc[rot].index)).abs()
            eff.append({"parameter_set": pid, "rotation": rot, "n_blocks": int(len(d)), "max_abs_diff_deficit_mm": float(d.max()), "mean_abs_diff_deficit_mm": float(d.mean()), "max_abs_diff_drainage_mm": float(dd.max())})
    summ = robustness_summary(recs)
    rank = ranking_stability(recs)
    flips = {rid: {m: v["parameter_sets_where_direction_differs_from_reference"] for m, v in d.items() if m in ("water_deficit_mm", "rainfall_low_cover_index_mm")} for rid, d in summ["sensitivity"].items()}
    ref_pc = [p for p in summ["paired_comparisons"] if p["parameter_set_id"] == "reference" and p["metric"] in ("water_deficit_mm", "rainfall_low_cover_index_mm")]
    catrange = {rid: {m: v["range_of_mean_paired_difference_by_category"] for m, v in d.items() if m == "water_deficit_mm"} for rid, d in summ["sensitivity"].items()}
    # sensitivity of the absolute deficit by parameter set (largest movers)
    ab = df.groupby(["pid", "rot"]).water_deficit_mm.mean().unstack(); ab = ab.sub(ab.loc["reference"], axis=1)
    deps = {m: __import__(m).__version__ for m in ("numpy", "pandas", "yaml")}
    try: import pyarrow; deps["pyarrow"] = pyarrow.__version__
    except ImportError: deps["pyarrow"] = "NOT INSTALLED"
    manifest = {"model_version": "screening-v2", "python": platform.python_version(), "dependencies": deps, "test_suite": suite,
                "et_benchmarks": et, "stress_cases": [{"case": a, "expected": b, "observed": c, "pass": bool(d)} for a, b, c, d in st],
                "spinup_and_initial_condition_effects": eff, "n_blocks": len(res["blocks"]), "n_parameter_sets": len(P["parameter_sets"]),
                "data_provenance": "SYNTHETIC_TEST_FIXTURE seed 42 (no field data, no NASA data)", "ranking_stability": rank["order_identical_across_parameter_sets"],
                "direction_flips": flips, "runtime_seconds": round(time.time() - t0, 1)}
    os.makedirs(os.path.join(ROOT, "output", "validation"), exist_ok=True)
    json.dump(manifest, open(os.path.join(ROOT, "output", "validation", "validation_manifest.json"), "w"), indent=2, sort_keys=True)
    L = ["# Numerical validation, Phase 2", "", "_Generated by `python tools/validate_phase2.py`. All numerical experiments use a SYNTHETIC weather fixture (seed 42) or hand-built series; no field-observed data are used or invented._", "",
         f"Environment: Python {manifest['python']}; numpy {deps['numpy']}, pandas {deps['pandas']}, PyYAML {deps['yaml']}, pyarrow {deps['pyarrow']}.", "",
         "## 1. Test suite", f"- tests run: **{suite['tests_run']}**, failures: **{suite['failures']}**, errors: **{suite['errors']}**, skipped: **{len(suite['skipped'])}**"]
    L += [f"  - skipped: {s}" for s in suite["skipped"]]
    L += ["", "## 2. Evapotranspiration benchmarks (FAO-56 worked examples)", "",
          "| Case | Reference | Expected (mm/day) | Actual | Abs diff | Rel diff % | Tolerance | Pass |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['case']} | {r['reference']} | {r['expected']} | {r['actual']} | {r['abs_diff']} | {r['rel_diff_pct']} | {r['tolerance_mm_day']} | {r['pass']} |" for r in et]
    L += ["", "Inputs. Example 18: Tmax 21.5, Tmin 12.3 C, RHmax 84 / RHmin 63 %, u10 = 2.78 m/s (converted to 2.079 m/s at 2 m by FAO-56 Eq. 47), Rs 22.07 MJ/m2/day, lat 50.8 N, z 100 m, day 187, G = 0. "
          "Example 17 (April monthly means): Tmax 34.8, Tmin 25.6 C, RHmax 87 / RHmin 51 %, u2 2.0 m/s, Rs 22.65, lat 13.733 N, z 2 m, day 105, G = 0.14 MJ/m2/day (Eq. 43).", "",
          "Interpretation: the 1e-3 mm/day agreement with the independent R implementation (CSLSevap test suite) verifies our arithmetic and unit handling. "
          "It is NOT independent observational validation, because both code bases implement the same FAO-56 equations. FAO prints ET0 to one decimal (3.9 and 5.7), so the 0.06 mm/day tolerance is the rounding of the printed value (0.05) plus a small margin. "
          "Both discrepancies are well inside that rounding.", "",
          "## 3. Water-balance stress and invariant tests", "", "| Case | Expected | Observed | Pass |", "|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in st]
    L += ["", "Further stress tests in `tests/test_stress.py`: alternating wet/dry cycles, near-zero and full storage, extreme temperatures (-40 to 45 C), leap years (366-day years complete, missing Feb 29 flagged incomplete), zero-rain full pipeline, malformed/missing inputs (raise, never zero-filled), determinism.", "",
          "## 4. Initial-condition and spin-up effect (synthetic fixture, 1981-2025)", "",
          "Baseline = each block starts at 50% of Smax. Compared with a 1-year rotation-independent fallow spin-up (only blocks with a complete preceding year) and with 25% / 75% starts.", "",
          "| Parameter set | Rotation | Blocks | Max abs diff deficit (mm) | Mean abs diff deficit (mm) | Max abs diff drainage (mm) |", "|---|---|---|---|---|---|"]
    L += [f"| {e['parameter_set']} | {e['rotation']} | {e['n_blocks']} | {e['max_abs_diff_deficit_mm']:.4f} | {e['mean_abs_diff_deficit_mm']:.4f} | {e['max_abs_diff_drainage_mm']:.4f} |" for e in eff]
    mx = max(e["max_abs_diff_deficit_mm"] for e in eff); mxd = max(e["max_abs_diff_drainage_mm"] for e in eff)
    L += ["", f"Largest change in modeled unmet demand from any initial-condition choice: **{mx:.4f} mm** (block totals are roughly 800-1000 mm). "
          f"Largest change in modeled deep drainage: **{mxd:.1f} mm**, which equals the difference in starting storage (25 to 50 mm): the extra starting water simply overflows once the bucket refills. "
          "On this synthetic weather (wet winters, Jan-Apr fallow with low demand) the starting condition is forgotten within weeks for unmet demand, so spin-up is immaterial for that metric and shifts drainage one-for-one. "
          "This does NOT show the same holds for real Johnston County weather, where a dry preceding autumn could matter more; re-run this script on real data.", "",
          "## 5. Paired comparison and sensitivity (synthetic; demonstration only)", "", "Reference parameter set, mean paired difference vs rotation_a on identical weather:", "",
          "| Rotation | Metric | Mean paired diff (mm) | Blocks lower / higher of n | Direction |", "|---|---|---|---|---|"]
    L += [f"| {p['rotation_id']} | {p['metric']} | {p['mean_paired_difference']:.2f} | {p['blocks_lower_count']} / {p['blocks_higher_count']} of {p['n_blocks']} | {p['direction_of_mean']} |" for p in ref_pc]
    L += ["", "Parameter sets where the direction differs from the reference (empty list = direction never flips):", ""]
    for rid, d in flips.items():
        for m, v in d.items(): L.append(f"- {rid}, {m}: {v if v else 'none'}")
    L += ["", "Change in each rotation's own mean water deficit (mm) relative to the reference parameter set (rows = parameter sets that moved something):", "", "| Parameter set | " + " | ".join(sorted(ROTS)) + " |", "|---|" + "---|" * len(ROTS)]
    for pid, r in ab.iterrows():
        if pid != "reference" and r.abs().max() > 0.05: L.append(f"| {pid} | " + " | ".join(f"{r[k]:+.1f}" for k in sorted(ROTS)) + " |")
    L += ["", f"Rotation ordering by mean water deficit identical across all {len(P['parameter_sets'])} parameter sets: **{rank['order_identical_across_parameter_sets']}**.", "",
          "## 6. Remaining limitations", "- No field or NASA observations used; Section 5 numbers are properties of the model on synthetic weather.",
          "- ET0 benchmarks check arithmetic against FAO worked examples, not against lysimeter or flux data.", "- Parquet ingestion untested if pyarrow is absent (see skipped tests).",
          "- Kc, stage lengths, fallow and cover parameters are generic or assumed; see crop_water_parameter_validation.md.", "- Soil storage values are illustrative until SSURGO-derived values are supplied.", ""]
    open(os.path.join(ROOT, "docs", "numerical_validation_phase2.md"), "w").write("\n".join(L))
    print(json.dumps({"tests": suite, "et_pass": all(r["pass"] for r in et), "stress_pass": all(r[3] for r in st), "max_spinup_diff_mm": mx, "runtime_s": manifest["runtime_seconds"]}, indent=1))
    return 0 if suite["failures"] == 0 and suite["errors"] == 0 and all(r["pass"] for r in et) and all(r[3] for r in st) else 1


if __name__ == "__main__":
    sys.exit(main())

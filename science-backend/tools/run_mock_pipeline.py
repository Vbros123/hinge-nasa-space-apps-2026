#!/usr/bin/env python3
"""End-to-end run on the MOCK environment: regenerate mock inputs, run the engine, check the output contract.

    python tools/run_mock_pipeline.py
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from tools.make_mock_environment import write
from run_evaluation import run

EXPECTED = ["feasible_rotations.json", "simulation_results.json", "scenario_metrics.json", "sensitivity_results.json", "model_manifest.json",
            "robustness_summary.json", "explanations.json"]

if __name__ == "__main__":
    data = os.path.join(ROOT, "tests", "fixtures", "mock_environment")
    out = os.path.join(ROOT, "output", "mock_pipeline")
    print("parquet written" if write(data) else "NOTE: pyarrow not installed; Parquet ingestion NOT exercised (CSV used)")
    res = run(data, out)
    missing = [f for f in EXPECTED if not os.path.exists(os.path.join(out, f))]
    assert not missing, f"missing outputs: {missing}"
    m = json.load(open(os.path.join(out, "model_manifest.json")))
    print(f"OK: {len(res['records'])} records, {len(res['blocks'])} blocks, provenance={m['data_provenance']}")

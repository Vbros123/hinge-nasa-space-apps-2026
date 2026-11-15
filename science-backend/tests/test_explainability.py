import unittest, json, re
from _common import *
from engine.scenarios import replay_historical_scenarios
from engine.robustness import robustness_summary
from engine.explainability import explain_all

FORBIDDEN = ["increases yield", "reduces erosion", "guaranteed", "guarantees", "will survive", "improves soil", "% yield", "saves fertilizer", "prevents erosion"]


def build(mgmt=None, prov="SYNTHETIC_TEST_FIXTURE"):
    w = weather(1990, 1996); ps = {k: P["parameter_sets"][k] for k in ("reference", "low_storage", "high_storage", "kc_end_sourced_alt")}
    res = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, mgmt or MGMT, ps)
    s = robustness_summary(res["records"])
    return res, s, explain_all(res, s, ROTS, P, LIB, SOIL, provenance=prov)


class TestExplain(unittest.TestCase):
    def test_structure_units_and_json(self):
        res, s, ex = build(); json.dumps(ex)
        need = {"rotation_id", "feasibility_status", "baseline_rotation_id", "comparison_metrics", "supporting_evidence", "assumptions", "warnings", "sensitivity_findings", "limitations", "explanation_text"}
        for r in ex["rotations"]:
            self.assertTrue(need <= set(r), r["rotation_id"])
            for m in r["comparison_metrics"]: self.assertIn(m["unit"], ("mm", "days"))
            for w in r["warnings"]: self.assertRegex(w["code"], r"^[A-Z0-9_]+$")
            self.assertTrue(r["assumptions"]); self.assertIn("NO_YIELD_PREDICTION", {l["code"] for l in r["limitations"]})

    def test_deterministic(self):
        a = build()[2]; b = build()[2]
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_no_unsupported_claims_and_numbers_traceable(self):
        res, s, ex = build()
        for r in ex["rotations"]:
            t = r["explanation_text"].lower()
            for bad in FORBIDDEN: self.assertNotIn(bad, t)
            if not r["is_baseline"]:
                d = [m for m in r["comparison_metrics"] if m["metric"] == "water_deficit_mm"][0]
                self.assertIn(f"{d['mean_paired_difference']:.1f} mm", r["explanation_text"])
                self.assertIn(f"{d['rotation_mean']:.1f} mm", r["explanation_text"]); self.assertIn("not crop damage", t)
            self.assertIn("synthetic", t)

    def test_synthetic_warning_and_real_provenance(self):
        ex = build()[2]; self.assertEqual(ex["rotations"][0]["warnings"][0]["code"], "DATA_SYNTHETIC")
        ex2 = build(prov="NASA POWER (real)")[2]; self.assertNotIn("DATA_SYNTHETIC", {w["code"] for r in ex2["rotations"] for w in r["warnings"]})

    def test_infeasible_rotation_explained_without_metrics(self):
        m = copy.deepcopy(MGMT); m["market_access_confirmed"] = {"winter_wheat": False}
        ex = build(m)[2]; c = [r for r in ex["rotations"] if r["rotation_id"] == "rotation_c"][0]
        self.assertFalse(c["feasible"]); self.assertEqual(c["comparison_metrics"], [])
        self.assertIn("MARKET_ACCESS_UNCONFIRMED", {h["code"] for h in c["feasibility"]["governing_hard_constraints"]})
        self.assertIn("infeasible", c["explanation_text"]); self.assertNotIn("mean paired difference", c["explanation_text"])

    def test_tradeoff_and_unfavorable_blocks_reported(self):
        ex = build()[2]; b = [r for r in ex["rotations"] if r["rotation_id"] == "rotation_b"][0]
        self.assertIn("TRADEOFF_ACROSS_OBJECTIVES", {w["code"] for w in b["warnings"]})
        self.assertTrue(b["supporting_evidence"]["largest_increase_vs_baseline_blocks"])
        self.assertIn("low_storage", b["sensitivity_findings"]["soil_storage_directions"])
        self.assertIn("Not substantiated", b["explanation_text"])


if __name__ == "__main__":
    unittest.main()

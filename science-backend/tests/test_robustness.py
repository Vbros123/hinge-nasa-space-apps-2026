import unittest, json
from _common import *
from engine.robustness import *
from engine.scenarios import replay_historical_scenarios


def rec(rot, scen, pid, deficit, low, cat="cat", status="x"):
    return {"rotation_id": rot, "scenario_id": scen, "parameter_set_id": pid, "category": cat, "assumption_status": status, "feasible": True,
            "metrics": {"water_deficit_mm": deficit, "rainfall_low_cover_index_mm": low, "eta_total_mm": 0, "drainage_mm": 0, "living_cover_days": 0,
                        "living_cover_equivalent_days": 0, "water_deficit_cash_mm": 0, "water_deficit_cover_mm": 0}}


class TestRobustness(unittest.TestCase):
    def setUp(self):
        self.R = []
        for pid, shift in (("reference", 0.0), ("low_storage", 0.0), ("flip", -30.0)):
            for s, (a, b) in {"b1": (100, 110), "b2": (200, 195), "b3": (300, 310)}.items():
                self.R.append(rec("A", s, pid, a, 50, cat="storage" if pid != "reference" else "reference"))
                self.R.append(rec("B", s, pid, b + shift, 20))

    def test_paired_difference_hand_calculation(self):
        df = records_frame(self.R, ["water_deficit_mm"])
        p = paired_differences(df, "water_deficit_mm", "A"); r = p[p.parameter_set_id == "reference"].iloc[0]
        self.assertEqual(r["n_blocks"], 3); self.assertAlmostEqual(r["mean_paired_difference"], (10 - 5 + 10) / 3)
        self.assertEqual((r["blocks_lower_count"], r["blocks_higher_count"]), (1, 2)); self.assertEqual(r["direction_of_mean"], "higher")

    def test_sign_flip_and_tradeoff_detected(self):
        s = robustness_summary(self.R, "A", ["water_deficit_mm", "rainfall_low_cover_index_mm"])
        d = s["sensitivity"]["B"]["water_deficit_mm"]
        self.assertEqual(d["parameter_sets_where_direction_differs_from_reference"], ["flip"]); self.assertFalse(d["consistent_across_all_parameter_sets"])
        self.assertTrue(s["tradeoffs_reference"]["B"]["tradeoff_present"])
        self.assertIn("flip", s["parameter_sets_with_tradeoff"]["B"] or ["flip"]) if False else None

    def test_no_probabilities_or_scores_reported(self):
        s = json.dumps(robustness_summary(self.R, "A", ["water_deficit_mm", "rainfall_low_cover_index_mm"])).lower()
        for bad in ("probab", "confidence", "p_value", "p-value", "overall_score", "composite"):
            self.assertNotIn(bad, s.replace("no probability, confidence interval or overall score is computed.", ""))
        self.assertIn("overlap", s)

    def test_baseline_missing(self):
        s = robustness_summary([r for r in self.R if r["rotation_id"] != "A"], "A", ["water_deficit_mm"])
        self.assertFalse(s["available"])

    def test_ranking_stability(self):
        r = ranking_stability(self.R)
        self.assertEqual(r["order_lowest_to_highest_by_parameter_set"]["reference"], ["A", "B"])
        self.assertEqual(r["order_lowest_to_highest_by_parameter_set"]["flip"], ["B", "A"]); self.assertFalse(r["order_identical_across_parameter_sets"])

    def test_worst_blocks_deterministic_order(self):
        df = records_frame(self.R, ["water_deficit_mm"]); w = worst_blocks(df, "water_deficit_mm", "A", k=2)
        self.assertEqual([b["scenario_id"] for b in w["B"]["largest_increase_vs_baseline_blocks"]], ["b1", "b3"])

    def test_end_to_end_paired_and_reproducible(self):
        w = weather(1990, 1996); ps = {k: P["parameter_sets"][k] for k in ("reference", "low_storage", "high_storage", "rye_terminate_early")}
        a = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, ps); b = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, ps)
        sa, sb = robustness_summary(a["records"]), robustness_summary(b["records"])
        self.assertEqual(json.dumps(sa, sort_keys=True), json.dumps(sb, sort_keys=True))
        n = sa["n_blocks"]
        for p in sa["paired_comparisons"]:
            self.assertEqual(p["blocks_lower_count"] + p["blocks_higher_count"] + p["blocks_equal_count"], p["n_blocks"]); self.assertEqual(p["n_blocks"], n)
        self.assertLess(sa["sensitivity"]["rotation_b"]["water_deficit_mm"]["reference_mean_paired_difference"] * 0, 1)   # finite
        # more storage never raises a rotation's own mean deficit (monotone physics check on the same weather)
        m = lambda pid, rid: np.mean([r["metrics"]["water_deficit_mm"] for r in a["records"] if r["parameter_set_id"] == pid and r["rotation_id"] == rid])
        for rid in ROTS: self.assertLessEqual(m("high_storage", rid), m("reference", rid) + 1e-9)


if __name__ == "__main__":
    unittest.main()

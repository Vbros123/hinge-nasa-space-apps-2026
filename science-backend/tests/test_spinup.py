import unittest
from _common import *
from engine.scenarios import replay_historical_scenarios, spinup_storage, prepare_weather, complete_years
from engine.water_balance import simulate_water_balance
from engine.crop_calendar import build_daily_calendar


class TestSpinup(unittest.TestCase):
    def setUp(self):
        self.w = weather(1990, 1997)
        self.ps = {"reference": P["parameter_sets"]["reference"], "spinup_1yr": P["parameter_sets"]["spinup_1yr"]}

    def test_baseline_unchanged_when_spinup_not_requested(self):
        a = replay_historical_scenarios(ROTS, self.w, SOIL, P, LIB, MGMT, {"reference": self.ps["reference"]})
        b = replay_historical_scenarios(ROTS, self.w, SOIL, P, LIB, MGMT, self.ps)
        rb = [r for r in b["records"] if r["parameter_set_id"] == "reference"]
        self.assertEqual(a["records"], rb)
        self.assertTrue(all(r["initial_conditions"]["spinup"].startswith("none") for r in rb))

    def test_spinup_same_initial_storage_for_all_rotations_and_labeled(self):
        res = replay_historical_scenarios(ROTS, self.w, SOIL, P, LIB, MGMT, self.ps)
        sp = [r for r in res["records"] if r["parameter_set_id"] == "spinup_1yr"]
        by = {}
        for r in sp: by.setdefault(r["scenario_id"], set()).add(round(r["initial_conditions"]["initial_storage_mm"], 9))
        self.assertTrue(all(len(v) == 1 for v in by.values()))
        first = [r for r in sp if r["scenario_id"] == "historical_1990_1992"][0]
        self.assertIn("unavailable", first["initial_conditions"]["spinup"]); self.assertIn("SPINUP_UNAVAILABLE", first["warnings"])
        self.assertEqual(first["initial_conditions"]["initial_storage_fraction"], 0.5)
        later = [r for r in sp if r["scenario_id"] == "historical_1992_1994"][0]
        self.assertTrue(later["initial_conditions"]["spinup"].startswith("fallow-with-residue"))

    def test_spinup_storage_matches_manual_fallow_run(self):
        ok, _ = complete_years(self.w, ["precipitation_mm"])
        wx = prepare_weather(self.w, P, P["site"])
        s0, _ = spinup_storage(wx, set(ok), 1993, 1, 100.0, P)
        yr = wx[wx["date"].dt.year == 1992].reset_index(drop=True)
        cal = build_daily_calendar({"rotation_id": "x", "operations": [], "residue_retained": True}, pd.DatetimeIndex(yr["date"]), 1992, LIB, P)
        sim = simulate_water_balance(yr, {"smax_mm": 100.0}, cal, P)
        self.assertAlmostEqual(s0, float(sim["storage_end_mm"].iloc[-1])); self.assertTrue(0.0 <= s0 <= 100.0)

    def test_no_spinup_when_gap_before_block(self):
        w = self.w[~((self.w["date"].dt.year == 1992) & (self.w["date"].dt.month == 3))].reset_index(drop=True)
        ok, _ = complete_years(w, ["precipitation_mm"]); wx = prepare_weather(w[w["date"].dt.year.isin(ok)].reset_index(drop=True), P, P["site"])
        s0, info = spinup_storage(wx, set(ok), 1993, 1, 100.0, P)
        self.assertIsNone(s0); self.assertIn("unavailable", info["spinup"])

    def test_deterministic(self):
        a = replay_historical_scenarios(ROTS, self.w, SOIL, P, LIB, MGMT, self.ps); b = replay_historical_scenarios(ROTS, self.w, SOIL, P, LIB, MGMT, self.ps)
        self.assertEqual(a["records"], b["records"])


if __name__ == "__main__":
    unittest.main()

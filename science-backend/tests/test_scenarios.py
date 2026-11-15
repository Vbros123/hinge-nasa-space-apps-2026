import unittest
from _common import *
from engine.scenarios import *
from engine.crop_calendar import build_daily_calendar, kc_curve


def run(w, psets=None, rots=None):
    return replay_historical_scenarios(rots or ROTS, w, SOIL, P, LIB, MGMT, psets)


class TestScenarios(unittest.TestCase):
    def test_blocks_are_contiguous_unshuffled_and_overlapping(self):
        w = weather(1990, 1995)
        blocks, _ = build_historical_blocks(w, 3, ["precipitation_mm", "temperature_max_c", "temperature_min_c"])
        self.assertEqual([b["scenario_id"] for b in blocks], ["historical_1990_1992", "historical_1991_1993", "historical_1992_1994", "historical_1993_1995"])
        orig = w.set_index("date")["precipitation_mm"]
        for b in blocks:   # days appear in original chronological order with original values
            self.assertTrue(b["weather"]["date"].is_monotonic_increasing)
            np.testing.assert_array_equal(b["weather"]["precipitation_mm"].values, orig.loc[b["weather"]["date"]].values)

    def test_same_weather_for_every_rotation(self):  # Test F
        res = run(weather(1990, 1994))
        by = {}
        for r in res["records"]:
            by.setdefault((r["parameter_set_id"], r["scenario_id"]), set()).add(r["weather_sha256_16"])
        self.assertTrue(all(len(v) == 1 for v in by.values()))
        self.assertEqual(len({r["rotation_id"] for r in res["records"]}), 3)

    def test_deterministic_replay(self):  # Tests E and I
        w = weather(1990, 1994)
        a = run(w, P["parameter_sets"]); b = run(w, P["parameter_sets"])
        self.assertEqual(a["records"], b["records"])

    def test_incomplete_year_excluded_and_reported(self):
        w = weather(1990, 1998)
        w = w[~((w["date"].dt.year == 1994) & (w["date"].dt.month == 6) & (w["date"].dt.day == 15))].reset_index(drop=True)
        res = run(w)
        self.assertIn(1994, res["excluded_years"])
        self.assertTrue(all(not (1994 in range(int(b[11:15]), int(b[16:20]) + 1)) for b in res["blocks"]))
        self.assertEqual(res["blocks"], ["historical_1990_1992", "historical_1991_1993", "historical_1995_1997", "historical_1996_1998"])

    def test_gap_year_leaves_no_block_and_raises(self):
        from engine import MissingInputError
        w = weather(1990, 1994)
        w = w[~((w["date"].dt.year == 1992) & (w["date"].dt.month == 6))].reset_index(drop=True)
        with self.assertRaises(MissingInputError):
            run(w)

    def test_partial_trailing_year_never_used(self):
        w = weather(1990, 1993, partial_year=1994)
        res = run(w)
        self.assertIn(1994, res["excluded_years"]); self.assertNotIn(1994, res["usable_years"])

    def test_infeasible_rotation_is_reported_not_simulated(self):
        m = copy.deepcopy(MGMT); m["market_access_confirmed"] = {"winter_wheat": False}
        res = replay_historical_scenarios(ROTS, weather(1990, 1992), SOIL, P, LIB, m)
        c = [r for r in res["records"] if r["rotation_id"] == "rotation_c"][0]
        self.assertFalse(c["feasible"]); self.assertIsNone(c["metrics"]); self.assertTrue(c["rejection_reasons"])
        self.assertTrue([r for r in res["records"] if r["rotation_id"] == "rotation_a"][0]["metrics"])

    def test_sensitivity_directions(self):
        res = run(weather(1990, 1996), P["parameter_sets"])
        def mean(pid, rid, k="water_deficit_mm"):
            v = [r["metrics"][k] for r in res["records"] if r["parameter_set_id"] == pid and r["rotation_id"] == rid]
            return sum(v) / len(v)
        for rid in ROTS:   # more storage -> less unmet demand
            self.assertLessEqual(mean("high_storage", rid), mean("reference", rid))
            self.assertLessEqual(mean("reference", rid), mean("low_storage", rid))
        # rotation_a has no rye: termination-date sets must not change it
        self.assertAlmostEqual(mean("rye_terminate_early", "rotation_a"), mean("reference", "rotation_a"))
        self.assertAlmostEqual(mean("rye_terminate_early", "rotation_c"), mean("reference", "rotation_c"))

    def test_cover_crop_adds_living_cover_and_lowers_exposure_proxy(self):
        res = run(weather(1990, 1996))
        m = lambda rid, k: sum(r["metrics"][k] for r in res["records"] if r["rotation_id"] == rid) / len([1 for r in res["records"] if r["rotation_id"] == rid])
        self.assertGreater(m("rotation_b", "living_cover_days"), m("rotation_a", "living_cover_days"))
        self.assertLess(m("rotation_b", "rainfall_low_cover_index_mm"), m("rotation_a", "rainfall_low_cover_index_mm"))
        self.assertGreaterEqual(m("rotation_b", "water_deficit_cover_mm"), 0.0)
        self.assertEqual(m("rotation_a", "water_deficit_cover_mm"), 0.0)

    def test_calendar_kc_curve_and_fallow(self):
        k = kc_curve(150, 0.3, 1.2, 0.6, {"initial": 30, "development": 40, "mid": 50, "late": 30})
        self.assertAlmostEqual(k[0], 0.3); self.assertAlmostEqual(k[75], 1.2); self.assertTrue(0.6 <= k[-1] < 1.2)
        w = weather(1990, 1992)
        cal = build_daily_calendar(ROTS["rotation_a"], pd.DatetimeIndex(w["date"]), 1990, LIB, P)
        fallow = cal[cal["role"] == "fallow"]
        self.assertTrue((fallow["kc"] > 0).all()); self.assertTrue((fallow["L"] == 0).all())
        self.assertAlmostEqual(fallow["kc"].iloc[0], P["water"]["fallow_kc"] * P["water"]["residue_kc_multiplier"])


if __name__ == "__main__":
    unittest.main()

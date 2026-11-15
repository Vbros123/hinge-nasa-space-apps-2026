import unittest
from _common import *
from engine.water_balance import simulate_water_balance
from engine.evapotranspiration import compute_reference_et, et0_penman_monteith
from engine.scenarios import complete_years
from engine import MissingInputError, InvalidInputError


def series(p, et0, kc, start="2001-01-01"):
    n = len(p)
    return (pd.DataFrame({"date": pd.date_range(start, periods=n), "precipitation_mm": np.asarray(p, float), "et0_mm": np.asarray(et0, float)}),
            pd.DataFrame({"kc": np.asarray(kc, float), "role": "cash", "alive": True}))


def invariants(tc, s, smax):
    tc.assertLess(s["mass_residual_mm"].abs().max(), 1e-9)
    tc.assertTrue(((s["storage_end_mm"] >= -1e-12) & (s["storage_end_mm"] <= smax + 1e-12)).all())
    tc.assertTrue((s["eta_mm"] <= s["etd_mm"] + 1e-12).all())
    tc.assertTrue((s[["eta_mm", "drainage_mm", "deficit_mm", "runoff_mm", "available_mm"]] >= -1e-12).all().all())


class TestStress(unittest.TestCase):
    def test_extended_drought(self):
        w, c = series([0] * 400, [4] * 400, [1.0] * 400)
        s = simulate_water_balance(w, {"smax_mm": 100}, c, P, initial_storage_mm=100)
        invariants(self, s, 100)
        self.assertAlmostEqual(s["eta_mm"].sum(), 100.0)                   # only the stored water can be extracted
        self.assertAlmostEqual(s["deficit_mm"].sum(), 400 * 4 - 100.0)
        self.assertEqual(s["storage_end_mm"].iloc[-1], 0.0)

    def test_heavy_rainfall_excess_drains(self):
        w, c = series([0, 500, 0, 0], [3, 3, 3, 3], [1, 1, 1, 1])
        s = simulate_water_balance(w, {"smax_mm": 100}, c, P, initial_storage_mm=40)
        invariants(self, s, 100)
        self.assertAlmostEqual(s["drainage_mm"].iloc[1], (40 - 3) + 500 - 3 - 100)   # day 0 leaves 37 mm; A=537, ETa=3, excess over Smax drains
        self.assertAlmostEqual(s["storage_end_mm"].iloc[1], 100.0)

    def test_alternating_wet_dry(self):
        p = ([60.0] * 5 + [0.0] * 30) * 12
        w, c = series(p, [4.0] * len(p), [0.9] * len(p))
        invariants(self, simulate_water_balance(w, {"smax_mm": 80}, c, P), 80)

    def test_near_zero_and_full_storage(self):
        w, c = series([0.001, 0, 0.5, 0], [5, 5, 5, 5], [1, 1, 1, 1])
        invariants(self, simulate_water_balance(w, {"smax_mm": 100}, c, P, initial_storage_mm=0.0), 100)
        w, c = series([0, 0, 0], [0.0, 0.0, 0.0], [1, 1, 1])
        s = simulate_water_balance(w, {"smax_mm": 100}, c, P, initial_storage_mm=100.0)
        self.assertTrue((s["storage_end_mm"] == 100.0).all())               # zero demand, zero rain: nothing changes

    def test_randomised_property(self):
        rng = np.random.default_rng(2026)
        for _ in range(200):
            n = int(rng.integers(5, 400)); smax = float(rng.uniform(5, 500))
            p = np.where(rng.random(n) < rng.uniform(0.05, 0.9), rng.gamma(0.6, rng.uniform(2, 40), n), 0.0)
            w, c = series(p, rng.uniform(0, 12, n), rng.uniform(0.05, 1.3, n))
            invariants(self, simulate_water_balance(w, {"smax_mm": smax}, c, P, initial_storage_mm=float(rng.uniform(0, smax))), smax)

    def test_extreme_but_plausible_temperatures(self):
        for tmax, tmin in ((45.0, 30.0), (-30.0, -40.0), (0.0, -5.0), (38.0, 38.0)):
            e = et0_penman_monteith(tmax, tmin, 20.0, 2.0, 35.5, 50, 190, rh_mean=50.0)
            self.assertTrue(np.isfinite(e) and e >= 0, (tmax, tmin, e))
        self.assertGreater(float(et0_penman_monteith(45, 30, 28, 3, 35.5, 50, 190, rh_mean=25.0)), float(et0_penman_monteith(25, 15, 28, 3, 35.5, 50, 190, rh_mean=25.0)))

    def test_leap_years(self):
        w = weather(1999, 2004)
        ok, ex = complete_years(w, ["precipitation_mm"])
        self.assertEqual(ok, [1999, 2000, 2001, 2002, 2003, 2004])
        self.assertEqual(int(((w["date"].dt.year == 2000) & (w["date"].dt.month == 2) & (w["date"].dt.day == 29)).sum()), 1)
        w2 = w[~((w["date"].dt.year == 2000) & (w["date"].dt.month == 2) & (w["date"].dt.day == 29))]
        self.assertIn(2000, complete_years(w2, ["precipitation_mm"])[1])     # leap year missing Feb 29 is incomplete
        from engine.scenarios import replay_historical_scenarios
        res = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, return_daily=True)
        self.assertIn("historical_1999_2001", res["blocks"])
        _, sim = res["daily"][("reference", "historical_1999_2001", "rotation_a")]
        self.assertEqual(len(sim), 365 + 366 + 365); self.assertLess(sim["mass_residual_mm"].abs().max(), 1e-9)

    def test_long_zero_precipitation_full_pipeline(self):
        w = weather(1990, 1992); w["precipitation_mm"] = 0.0
        from engine.scenarios import replay_historical_scenarios
        res = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, return_daily=True)
        for key, (cal, sim) in res["daily"].items():
            self.assertTrue((np.diff(sim["storage_end_mm"]) <= 1e-12).all(), key)
            self.assertEqual(float(sim["drainage_mm"].sum()), 0.0)

    def test_malformed_inputs(self):
        w, c = series([1, 2, 3], [3, 3, 3], [1, 1, 1])
        w.loc[1, "precipitation_mm"] = np.nan
        with self.assertRaises(MissingInputError): simulate_water_balance(w, {"smax_mm": 50}, c, P)
        w, c = series([1, 2, 3], [3, 3, 3], [1, 1, 1])
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": float("nan")}, c, P)
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": 50}, c.iloc[:2], P)

    def test_determinism(self):
        w = weather(1990, 1992); w["et0_mm"] = compute_reference_et(w, "penman_monteith", P["site"])["et0_mm"].values
        c = pd.DataFrame({"kc": 0.8, "role": "cash", "alive": True}, index=range(len(w)))
        a = simulate_water_balance(w, {"smax_mm": 100}, c, P); b = simulate_water_balance(w, {"smax_mm": 100}, c, P)
        pd.testing.assert_frame_equal(a, b)


if __name__ == "__main__":
    unittest.main()

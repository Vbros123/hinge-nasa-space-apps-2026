import unittest
from _common import *
from engine.water_balance import simulate_water_balance
from engine import MassBalanceError, MissingInputError, InvalidInputError


def frame(p, et0, kc):
    n = len(p)
    w = pd.DataFrame({"date": pd.date_range("2001-01-01", periods=n), "precipitation_mm": p, "et0_mm": et0})
    c = pd.DataFrame({"kc": kc, "role": "cash", "alive": True})
    return w, c


class TestWB(unittest.TestCase):
    def test_hand_calculation(self):
        # Smax=50, S0=20. Day1: P=40,ET0=5,Kc=1 -> A=60, ETa=5, D=60-5-50=5, S=50. Day2: P=0,ET0=6,Kc=0.5 -> A=50, ETd=3, S=47.
        # Day3: P=0, ET0=100, Kc=1 -> A=47, ETa=47 (limited by water), deficit=53, S=0.
        w, c = frame([40, 0, 0], [5, 6, 100], [1.0, 0.5, 1.0])
        P2 = copy.deepcopy(P)
        s = simulate_water_balance(w, {"smax_mm": 50}, c, P2, initial_storage_mm=20)
        np.testing.assert_allclose(s["eta_mm"], [5, 3, 47])
        np.testing.assert_allclose(s["drainage_mm"], [5, 0, 0])
        np.testing.assert_allclose(s["storage_end_mm"], [50, 47, 0])
        np.testing.assert_allclose(s["deficit_mm"], [0, 0, 53])

    def test_zero_rain_never_increases_storage(self):  # Test C
        w, c = frame([0.0] * 120, [3.0] * 120, [0.3] * 120)
        s = simulate_water_balance(w, {"smax_mm": 100}, c, P, initial_storage_mm=80)
        self.assertTrue((np.diff(s["storage_end_mm"]) <= 1e-12).all())
        self.assertTrue((s["drainage_mm"] == 0).all())

    def test_mass_balance_and_bounds_on_long_series(self):  # Tests A, B
        w = weather(1990, 1999)
        w["et0_mm"] = compute_reference_et_safe(w)
        cal = pd.DataFrame({"kc": np.where(w["date"].dt.month.isin([5, 6, 7, 8]), 1.1, 0.3), "role": "cash", "alive": True})
        for smax in (30, 60, 100, 140, 400):
            s = simulate_water_balance(w, {"smax_mm": smax}, cal, P)
            self.assertLess(s["mass_residual_mm"].abs().max(), 1e-9)
            self.assertTrue((s["storage_end_mm"] >= 0).all() and (s["storage_end_mm"] <= smax + 1e-12).all())
            self.assertTrue((s["eta_mm"] <= s["etd_mm"] + 1e-12).all())

    def test_identical_inputs_identical_outputs(self):  # Test E
        w, c = frame(list(np.random.default_rng(1).gamma(0.5, 10, 200)), [3.0] * 200, [0.8] * 200)
        a = simulate_water_balance(w, {"smax_mm": 90}, c, P); b = simulate_water_balance(w, {"smax_mm": 90}, c, P)
        pd.testing.assert_frame_equal(a, b)

    def test_invalid_inputs_rejected(self):  # Test G (water side)
        w, c = frame([1, 2], [3, 3], [1, 1])
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": 0}, c, P)
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": -5}, c, P)
        w2, c2 = frame([1, np.nan], [3, 3], [1, 1])
        with self.assertRaises(MissingInputError): simulate_water_balance(w2, {"smax_mm": 50}, c2, P)
        w3, c3 = frame([1, 2], [3, 3], [1, -0.2])
        with self.assertRaises(InvalidInputError): simulate_water_balance(w3, {"smax_mm": 50}, c3, P)
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": 50}, c, P, initial_storage_mm=60)

    def test_runoff_cannot_exceed_rain(self):
        w, c = frame([10.0, 0.0], [1, 1], [0.5, 0.5])
        P2 = copy.deepcopy(P); P2["water"]["runoff_fraction"] = 0.3
        s = simulate_water_balance(w, {"smax_mm": 100}, c, P2, initial_storage_mm=10)
        self.assertAlmostEqual(s["runoff_mm"].iloc[0], 3.0)
        P2["water"]["runoff_fraction"] = 1.5
        with self.assertRaises(InvalidInputError): simulate_water_balance(w, {"smax_mm": 100}, c, P2)


def compute_reference_et_safe(w):
    from engine.evapotranspiration import compute_reference_et
    return compute_reference_et(w, "penman_monteith", P["site"])["et0_mm"].values


if __name__ == "__main__":
    unittest.main()

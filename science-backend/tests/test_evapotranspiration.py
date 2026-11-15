import unittest
from _common import *
from engine.evapotranspiration import *
from engine import MissingInputError, InvalidInputError


class TestET(unittest.TestCase):
    def test_fao56_example18(self):
        # FAO-56 Example 18 (Uccle, 6 July): published ET0 = 3.9 mm/day; Rn = 13.28 MJ m-2 d-1; ea = 1.409 kPa; Ra = 41.09
        doy = 187
        ra = extraterrestrial_radiation(50.8, doy)
        ea = actual_vapor_pressure(21.5, 12.3, rh_max=84, rh_min=63)
        rn, _, _ = net_radiation(22.07, 21.5, 12.3, ea, ra, 100)
        et0 = et0_penman_monteith(21.5, 12.3, 22.07, 2.078, 50.8, 100, doy, rh_max=84, rh_min=63)
        self.assertAlmostEqual(float(ra), 41.09, delta=0.02)
        self.assertAlmostEqual(float(ea), 1.409, delta=0.002)
        self.assertAlmostEqual(float(rn), 13.28, delta=0.02)
        self.assertAlmostEqual(float(et0), 3.88, delta=0.02)

    def test_hargreaves_is_labeled_approximate_and_close_in_magnitude(self):
        w = weather(1990, 1991)
        site = P["site"]
        a = compute_reference_et(w, "hargreaves_samani", site)
        b = compute_reference_et(w, "penman_monteith", site)
        self.assertIn("APPROXIMATE", a["et0_method"].iloc[0])
        self.assertNotIn("APPROXIMATE", b["et0_method"].iloc[0])
        self.assertLess(abs(a["et0_mm"].mean() - b["et0_mm"].mean()) / b["et0_mm"].mean(), 0.5)

    def test_no_silent_method_fallback(self):
        w = weather(1990, 1991).drop(columns=["solar_radiation"])
        with self.assertRaises(MissingInputError):
            compute_reference_et(w, "penman_monteith", P["site"])
        with self.assertRaises(InvalidInputError):
            compute_reference_et(weather(1990, 1991), "made_up", P["site"])

    def test_nan_input_not_zero_filled(self):
        w = weather(1990, 1991)
        w.loc[10, "wind_speed"] = np.nan
        with self.assertRaises(MissingInputError):
            compute_reference_et(w, "penman_monteith", P["site"])

    def test_et0_nonnegative_and_finite(self):
        e = compute_reference_et(weather(1990, 1992), "penman_monteith", P["site"])["et0_mm"]
        self.assertTrue(np.isfinite(e).all()); self.assertTrue((e >= 0).all())
        self.assertGreater(e.mean(), 1.0); self.assertLess(e.mean(), 6.0)


if __name__ == "__main__":
    unittest.main()

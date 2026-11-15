import unittest
from _common import *
from engine.evapotranspiration import *

# (name, inputs, expected published FAO value, expected independent-implementation value)
CASES = {
    "FAO-56 Example 18 (Uccle, 6 Jul, daily)": dict(
        args=dict(tmax=21.5, tmin=12.3, rs=22.07, u2=2.0 * 0 + 2.78 * 4.87 / np.log(67.8 * 10 - 5.42), lat_deg=50.8, elevation_m=100, doy=187, rh_max=84, rh_min=63),
        fao_published=3.9, independent=3.880142, g=0.0),
    "FAO-56 Example 17 (Bangkok, April, monthly means)": dict(
        args=dict(tmax=34.8, tmin=25.6, rs=22.65, u2=2.0, lat_deg=13 + 44 / 60, elevation_m=2, doy=105, rh_max=87, rh_min=51),
        fao_published=5.7, independent=5.718284, g=0.14),
}


def run_case(c):
    return float(et0_penman_monteith(g=c["g"], **c["args"]))


class TestBenchmarks(unittest.TestCase):
    def test_against_independent_implementation_and_published_values(self):
        for name, c in CASES.items():
            v = run_case(c)
            self.assertAlmostEqual(v, c["independent"], delta=1e-3, msg=name)            # arithmetic agreement (same equations, other code base)
            self.assertAlmostEqual(v, c["fao_published"], delta=0.06, msg=name)           # FAO prints one decimal

    def test_example17_intermediates(self):
        tmean = (34.8 + 25.6) / 2
        self.assertAlmostEqual(float(slope_svp(tmean)), 0.2458, delta=5e-4)
        es = (sat_vp(34.8) + sat_vp(25.6)) / 2
        self.assertAlmostEqual(float(es), 4.4218, delta=2e-3)
        self.assertAlmostEqual(float(actual_vapor_pressure(34.8, 25.6, rh_max=87, rh_min=51)), 2.846, delta=2e-3)
        self.assertAlmostEqual(float(extraterrestrial_radiation(13 + 44 / 60, 105)), 38.06, delta=0.02)
        self.assertAlmostEqual(float(psychrometric_constant(pressure(2.0))), 0.0673, delta=2e-4)

    def test_daylight_hours_example18(self):
        self.assertAlmostEqual(float(daylight_hours(50.8, 187)), 16.1, delta=0.05)


if __name__ == "__main__":
    unittest.main()

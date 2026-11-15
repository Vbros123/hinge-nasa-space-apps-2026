import unittest
from _common import *
from engine.crop_calendar import kc_curve, crop_kc_params, build_daily_calendar
from engine import InvalidInputError, MissingInputError

ST = {"initial": 30, "development": 40, "mid": 50, "late": 50}


class TestKcCurve(unittest.TestCase):
    def test_stage_boundaries_and_continuity(self):
        n = 170
        k = kc_curve(n, 0.30, 1.20, 0.60, ST)
        self.assertTrue(np.allclose(k[:30], 0.30))                           # initial stage flat
        self.assertTrue(np.allclose(k[70:120], 1.20))                        # mid stage flat
        self.assertTrue((np.diff(k[29:71]) > 0).all())                       # development rises
        self.assertTrue((np.diff(k[119:]) < 0).all())                        # late declines
        self.assertLess(np.abs(np.diff(k)).max(), 0.05)                      # no jumps between days
        self.assertTrue(0.60 <= k[-1] < 0.65)

    def test_rescaling_preserves_proportions_and_extremes(self):
        for n in (60, 143, 228, 400):
            k = kc_curve(n, 0.4, 1.15, 0.5, {"initial": 20, "development": 30, "mid": 60, "late": 25})
            self.assertAlmostEqual(k.min(), 0.4, delta=0.03); self.assertAlmostEqual(k.max(), 1.15, delta=1e-9)
            self.assertTrue((k >= 0.4 - 1e-9).all() and (k <= 1.15 + 1e-9).all())

    def test_boundary_lengths(self):
        self.assertEqual(len(kc_curve(1, 0.3, 1.2, 0.6, ST)), 1)
        self.assertTrue(0.3 <= float(kc_curve(1, 0.3, 1.2, 0.6, ST)[0]) <= 1.2)   # one-day crop is evaluated at its day-centre
        with self.assertRaises(InvalidInputError): kc_curve(0, 0.3, 1.2, 0.6, ST)
        with self.assertRaises(InvalidInputError): kc_curve(10, 0.3, 1.2, 0.6, {**ST, "mid": 0})
        with self.assertRaises(InvalidInputError): kc_curve(10, 0.3, 1.2, 0.6, {"initial": 1})

    def test_kc_end_below_and_above_start(self):
        k = kc_curve(100, 0.4, 1.15, 0.25, ST); self.assertLess(k[-1], k[0])
        k = kc_curve(100, 0.7, 1.15, 0.25, ST); self.assertAlmostEqual(k[0], 0.7)

    def test_wheat_uses_non_frozen_soil_ini(self):
        self.assertEqual(LIB["crops"]["winter_wheat"]["water"]["kc_initial"], 0.7)
        self.assertEqual(LIB["crops"]["winter_wheat"]["water"]["kc_initial_frozen_soils"], 0.4)

    def test_fao_table12_values_in_library(self):
        W = {c: LIB["crops"][c]["water"] for c in ("corn", "soybean", "winter_wheat")}
        self.assertEqual((W["corn"]["kc_initial"], W["corn"]["kc_mid"], W["corn"]["kc_end"]), (0.30, 1.20, 0.60))
        self.assertEqual((W["soybean"]["kc_initial"], W["soybean"]["kc_mid"], W["soybean"]["kc_end"]), (0.40, 1.15, 0.50))
        self.assertEqual((W["winter_wheat"]["kc_mid"], W["winter_wheat"]["kc_end"]), (1.15, 0.25))

    def test_cash_crop_kc_never_substituted_and_cover_flagged(self):
        lib = copy.deepcopy(LIB); lib["crops"]["soybean"]["water"]["kc_end"] = None
        with self.assertRaises(MissingInputError): crop_kc_params("soybean", lib, P)
        self.assertEqual(crop_kc_params("cereal_rye", LIB, P)[4], "assumed")

    def test_cover_phenology_decoupled_from_wheat_stage_override(self):
        P2 = copy.deepcopy(P); P2["water"]["cover_stage_lengths_days"] = {"initial": 30, "development": 140, "mid": 40, "late": 30}
        lib = copy.deepcopy(LIB); lib["crops"]["winter_wheat"]["water"]["stage_lengths_days"] = {"initial": 160, "development": 75, "mid": 75, "late": 25}
        self.assertEqual(crop_kc_params("cereal_rye", lib, P2)[3]["development"], 140)

    def test_calendar_kc_matches_curve_on_crop_days(self):
        w = weather(1990, 1992)
        cal = build_daily_calendar(ROTS["rotation_a"], pd.DatetimeIndex(w["date"]), 1990, LIB, P)
        corn = cal[(cal["crop_id"] == "corn") & (cal["date"].dt.year == 1990)]
        self.assertEqual(len(corn), (pd.Timestamp("1990-09-15") - pd.Timestamp("1990-04-25")).days)
        self.assertAlmostEqual(corn["kc"].iloc[0], 0.30, delta=0.01); self.assertAlmostEqual(corn["kc"].max(), 1.20, delta=1e-9)
        self.assertEqual(corn["role"].unique().tolist(), ["cash"])
        # day after harvest drops to fallow Kc (never zero)
        after = cal[cal["date"] == "1990-09-15"].iloc[0]
        self.assertEqual(after["role"], "fallow"); self.assertGreater(after["kc"], 0)

    def test_cover_decline_after_termination(self):
        w = weather(1990, 1992)
        cal = build_daily_calendar(ROTS["rotation_b"], pd.DatetimeIndex(w["date"]), 1990, LIB, P)
        t = cal[(cal["date"] >= "1991-04-05") & (cal["date"] < "1991-04-16")]
        self.assertTrue((t["L"].diff().dropna() <= 1e-12).all()); self.assertEqual(t["L"].iloc[-1], 0.0)
        self.assertTrue((t["role"] == "fallow").all())


if __name__ == "__main__":
    unittest.main()

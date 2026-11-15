import unittest
from _common import *
from engine.scenarios import replay_historical_scenarios


class TestFullReplayInvariants(unittest.TestCase):
    def test_every_day_of_every_run_conserves_water(self):
        w = weather(1990, 1995)
        res = replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT, P["parameter_sets"], return_daily=True)
        self.assertGreater(len(res["daily"]), 0)
        for key, (cal, sim) in res["daily"].items():
            smax = [r for r in res["records"] if (r["parameter_set_id"], r["scenario_id"], r["rotation_id"]) == key][0]["parameters"]["soil_storage_capacity_mm"]
            self.assertLess(sim["mass_residual_mm"].abs().max(), 1e-9, key)
            self.assertTrue((sim["storage_end_mm"].between(-1e-9, smax + 1e-9)).all(), key)
            self.assertTrue((cal["L"].between(0, 1)).all(), key)
            self.assertTrue((cal["kc"] > 0).all(), "fallow evaporation must never be zero")


if __name__ == "__main__":
    unittest.main()

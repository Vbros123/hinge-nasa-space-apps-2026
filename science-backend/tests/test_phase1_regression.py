"""Phase 1 behaviour is preserved: the frozen Phase 1 config reproduces the stored Phase 1 reference metrics on the same synthetic fixture."""
import unittest, json
from _common import *
from engine.scenarios import replay_historical_scenarios


class TestPhase1Regression(unittest.TestCase):
    def test_frozen_config_reproduces_phase1_metrics(self):
        fz = os.path.join(CFG, "phase1_frozen")
        lib = load_crop_library(os.path.join(fz, "crops_nc.yaml"))
        rots = generate_rotation_templates(lib, os.path.join(fz, "rotations_nc.yaml"))
        P1 = load_yaml(os.path.join(fz, "model_parameters.yaml"))
        w = normalize_weather(make_weather(1981, 2025, partial_year=2026), MANIFEST["units"])
        res = replay_historical_scenarios(rots, w, {"scenarios": P1["soil_storage_scenarios_mm"]}, P1, lib, P1["management_defaults"],
                                          {"reference": P1["parameter_sets"]["reference"]},
                                          site={**P1["site"], **MANIFEST["site"]})   # Phase 1 CLI took lat/elevation from the fixture manifest
        ref = json.load(open(os.path.join(ROOT, "tests", "fixtures", "phase1_reference_metrics.json")))["metrics"]
        self.assertEqual(len(res["records"]), len(ref))
        for r in res["records"]:
            exp = ref[f"{r['rotation_id']}|{r['scenario_id']}"]
            for k, v in exp.items():
                self.assertAlmostEqual(r["metrics"][k], v, places=5, msg=(r["rotation_id"], r["scenario_id"], k))


if __name__ == "__main__":
    unittest.main()

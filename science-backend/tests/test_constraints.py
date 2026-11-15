import unittest
from _common import *
from engine.feasibility import *
from engine.scenarios import apply_parameter_set


def ev(rot, mgmt=None, lib=None):
    return evaluate_rotation_feasibility(rot, lib or LIB, SOIL, mgmt or MGMT, P)


def codes(f, sev=None):
    return {r["code"] for r in f["reasons"] if sev is None or r["severity"] == sev}


class TestFeasibility(unittest.TestCase):
    def test_templates_feasible_on_verified_windows_with_caveats(self):
        for rid, r in ROTS.items():
            f = ev(r)
            self.assertTrue(f["feasible"], (rid, codes(f, "hard")))
            self.assertEqual(f["status"], "feasible", (rid, codes(f, "verification")))
            self.assertNotIn("ASSUMED_WINDOW", codes(f))
            cav = {c["code"] for c in f["evidence_caveats"]}
            self.assertIn("STATEWIDE_USUAL_DATES", cav); self.assertIn("NO_HUMAN_REVIEW", cav)   # `feasible` is never a field guarantee

    def test_reliance_on_assumed_window_keeps_pending_status(self):
        lib = copy.deepcopy(LIB); lib["crops"]["corn"]["planting_window"]["status"] = "assumed"
        f = ev(ROTS["rotation_a"], lib=lib)
        self.assertEqual(f["status"], "feasible_pending_verification"); self.assertIn("ASSUMED_WINDOW", codes(f, "verification"))
        self.assertEqual(ev(ROTS["rotation_c"], lib=lib)["status"], "feasible_pending_verification")   # corn is in rotation_c too

    def test_phase1_frozen_config_still_pending(self):
        from engine.crop_calendar import load_crop_library as L
        lib1 = L(os.path.join(CFG, "phase1_frozen", "crops_nc.yaml"))
        rots1 = generate_rotation_templates(lib1, os.path.join(CFG, "phase1_frozen", "rotations_nc.yaml"))
        for rid, r in rots1.items():
            self.assertEqual(evaluate_rotation_feasibility(r, lib1, SOIL, MGMT, P)["status"], "feasible_pending_verification")

    def test_planting_before_harvest_conflict(self):  # Test H: impossible schedule
        r = copy.deepcopy(ROTS["rotation_c"])
        for op in r["operations"]:
            if op["crop"] == "soybean" and op["action"] == "plant": op["date"] = "05-20"   # before wheat harvest 06-05
        f = ev(r)
        self.assertFalse(f["feasible"]); self.assertIn("OPERATION_CONFLICT", codes(f, "hard"))
        self.assertIn("OUTSIDE_USUAL_RANGE", codes(f, "verification"))   # descriptive window: flagged, the hard failure is the overlap

    def test_sourced_window_violation_is_hard_and_cites_source(self):
        r = copy.deepcopy(ROTS["rotation_b"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "plant": op["date"] = "01-10"
        f = ev(r)
        bad = [x for x in f["reasons"] if x["code"] == "PLANTING_WINDOW_CONFLICT"]
        self.assertTrue(bad); self.assertEqual(bad[0]["source_id"], "ncsu_winter_cover_crops")

    def test_late_but_possible_cover_planting_is_warning_not_rejection(self):
        r = copy.deepcopy(ROTS["rotation_b"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "plant": op["date"] = "12-01"   # possible, not preferred
        f = ev(r)
        self.assertTrue(f["feasible"]); self.assertIn("LATE_ESTABLISHMENT", codes(f, "warning"))

    def test_cover_termination_gap_rule(self):
        r = copy.deepcopy(ROTS["rotation_b"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "terminate": op["date"] = "04-20"   # only 5 days before corn
        f = ev(r)
        self.assertIn("COVER_TERMINATION_GAP", codes(f, "hard"))

    def test_cover_planted_before_cash_harvest_is_conflict(self):
        r = copy.deepcopy(ROTS["rotation_b"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "plant" and op["year_offset"] == 0: op["date"] = "09-30"  # corn harvest 10-... shift below
            if op["crop"] == "corn" and op["action"] == "harvest" and op["year_offset"] == 0: op["date"] = "10-10"
        self.assertIn("COVER_ESTABLISHMENT_CONFLICT", codes(ev(r), "hard"))

    def test_unsupported_termination_method(self):
        r = copy.deepcopy(ROTS["rotation_b"]); r["termination_method"] = "flamethrower"
        m = copy.deepcopy(MGMT); m["termination_methods_available"].append("flamethrower")
        self.assertIn("UNSUPPORTED_TERMINATION_METHOD", codes(ev(r, m), "hard"))

    def test_termination_method_unavailable_on_farm(self):
        r = copy.deepcopy(ROTS["rotation_b"]); r["termination_method"] = "roller_crimper"
        self.assertIn("TERMINATION_METHOD_UNAVAILABLE", codes(ev(r), "hard"))

    def test_missing_equipment_rejects(self):
        m = copy.deepcopy(MGMT); m["equipment_available"] = ["planter", "combine"]   # no grain drill
        self.assertFalse(ev(ROTS["rotation_b"], m)["feasible"])
        self.assertFalse(ev(ROTS["rotation_c"], m)["feasible"])
        self.assertTrue(ev(ROTS["rotation_a"], m)["feasible"])

    def test_market_access_denied_and_unknown(self):
        m = copy.deepcopy(MGMT); m["market_access_confirmed"] = {"winter_wheat": False}
        self.assertIn("MARKET_ACCESS_UNCONFIRMED", codes(ev(ROTS["rotation_c"], m), "hard"))
        m["market_access_confirmed"] = {}
        f = ev(ROTS["rotation_c"], m)
        self.assertTrue(f["feasible"]); self.assertIn("MARKET_ACCESS_UNKNOWN", codes(f, "verification"))

    def test_farmer_excluded_crop(self):
        m = copy.deepcopy(MGMT); m["excluded_crops"] = ["winter_wheat"]
        self.assertIn("FARMER_EXCLUDED_CROP", codes(ev(ROTS["rotation_c"], m), "hard"))

    def test_unknown_crop_and_sequence_restriction(self):
        r = copy.deepcopy(ROTS["rotation_a"]); r["cash_sequence"] = ["corn", "quinoa"]
        self.assertIn("UNKNOWN_CROP", codes(ev(r), "hard"))
        lib = copy.deepcopy(LIB); lib["crops"]["soybean"]["rotation"]["preceding_crop_restrictions"] = ["corn"]
        self.assertIn("SEQUENCE_RESTRICTION", codes(ev(ROTS["rotation_a"], lib=lib), "hard"))

    def test_family_repeat_is_warning_only(self):
        f = ev(ROTS["rotation_c"])
        self.assertIn("CROP_FAMILY_REPEAT", codes(f, "warning")); self.assertTrue(f["feasible"])

    def test_missing_soil_requests_information(self):
        f = evaluate_rotation_feasibility(ROTS["rotation_a"], LIB, None, MGMT, P)
        self.assertIn("SOIL_STORAGE_UNKNOWN", codes(f, "verification"))

    def test_parameter_set_does_not_mutate_inputs(self):
        before = copy.deepcopy(ROTS["rotation_b"])
        apply_parameter_set(ROTS["rotation_b"], LIB, P["parameter_sets"]["rye_terminate_late"])
        self.assertEqual(before, ROTS["rotation_b"])


if __name__ == "__main__":
    unittest.main()

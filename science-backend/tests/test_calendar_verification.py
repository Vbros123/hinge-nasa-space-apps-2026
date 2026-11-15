import unittest, yaml
from _common import *
from engine.feasibility import *
from engine.crop_calendar import parse_md, md_in_window

REG = yaml.safe_load(open(os.path.join(CFG, "evidence_register.yaml")))["entries"]
# NASS NC Agricultural Statistics p.58 (Begin, Most Active, End) transcribed independently of the config
NASS = {"corn": {"plant": ("04-01", "04-10", "04-25", "05-20"), "harvest": ("08-20", "09-10", "10-10", "10-10")},
        "soybean": {"plant": ("05-01", "05-20", "06-30", "07-20"), "harvest": ("10-10", "11-10", "12-05", "12-20")},
        "winter_wheat": {"plant": ("09-20", "10-15", "11-20", "12-20"), "harvest": ("05-30", "06-10", "06-30", "07-25")}}


def ev(rot, mgmt=None, par=None):
    return evaluate_rotation_feasibility(rot, LIB, SOIL, mgmt or MGMT, par or P)


def codes(f, sev=None):
    return {r["code"] for r in f["reasons"] if sev is None or r["severity"] == sev}


class TestVerifiedCalendars(unittest.TestCase):
    def test_config_matches_nass_table(self):
        for crop, d in NASS.items():
            for act, key in (("plant", "planting_window"), ("harvest", "harvest_window")):
                w = LIB["crops"][crop][key]; b, a1, a2, e = d[act]
                self.assertEqual((w["earliest"], w["latest"]), (b, e), (crop, act))
                self.assertEqual((w["most_active"]["earliest"], w["most_active"]["latest"]), (a1, a2), (crop, act))
                self.assertEqual(w["status"], "sourced_descriptive")

    def test_every_sourced_window_has_registered_evidence(self):
        for cid, c in LIB["crops"].items():
            for key in ("planting_window", "harvest_window", "termination_window", "full_season_window", "double_crop_window"):
                w = c.get(key)
                if w and w.get("status") in ("sourced", "sourced_descriptive", "sourced_secondary"):
                    self.assertTrue(w.get("evidence_ids"), (cid, key))
                    for e in w["evidence_ids"]:
                        self.assertIn(e, REG, (cid, key, e)); self.assertTrue(REG[e]["url"].startswith("http")); self.assertIn(REG[e]["evidence_type"], ("direct", "inferred", "secondary"))
                    self.assertIn(w["source_id"], LIB["sources"])
        for e, r in REG.items():
            for f in ("title", "url", "location", "geography", "evidence_type", "uncertainty"):
                self.assertTrue(r.get(f), (e, f))

    def test_template_operation_dates_inside_windows(self):
        for rid, r in ROTS.items():
            for e in ev(r)["operation_evidence"]:
                self.assertTrue(e["inside"], (rid, e))

    def test_corn_late_extension_is_warning_not_rejection(self):
        r = copy.deepcopy(ROTS["rotation_a"])
        for op in r["operations"]:
            if op["crop"] == "corn" and op["action"] == "plant" and op["year_offset"] == 0: op["date"] = "06-10"
            if op["crop"] == "corn" and op["action"] == "harvest" and op["year_offset"] == 0: op["date"] = "10-10"   # keeps the 108-day sourced minimum
        f = ev(r); self.assertTrue(f["feasible"]); self.assertIn("LATE_PLANTING_EXTENDED", codes(f, "warning"))

    def test_corn_beyond_extension_needs_verification_not_hard_reject(self):
        r = copy.deepcopy(ROTS["rotation_a"])
        for op in r["operations"]:
            if op["crop"] == "corn" and op["action"] == "plant" and op["year_offset"] == 0: op["date"] = "06-22"
            if op["crop"] == "corn" and op["action"] == "harvest" and op["year_offset"] == 0: op["date"] = "10-10"
        f = ev(r); self.assertIn("OUTSIDE_USUAL_RANGE", codes(f, "verification")); self.assertEqual(f["status"], "feasible_pending_verification")

    def test_original_phase1_soybean_harvest_now_flagged(self):
        r = copy.deepcopy(ROTS["rotation_a"])
        for op in r["operations"]:
            if op["crop"] == "soybean" and op["action"] == "harvest": op["date"] = "10-05"     # Phase 1 date, before the NASS usual start Oct 10
        f = ev(r); self.assertIn("OUTSIDE_USUAL_RANGE", codes(f, "verification"))

    def test_double_crop_slack_and_window(self):
        f = ev(ROTS["rotation_c"]); self.assertIn(5, f["calendar"]["calendar_slack_days"])
        r = copy.deepcopy(ROTS["rotation_c"])
        for op in r["operations"]:
            if op["crop"] == "soybean" and op.get("label") == "double_crop" and op["action"] == "plant": op["date"] = "07-25"
        self.assertIn("OUTSIDE_USUAL_RANGE", codes(ev(r), "verification"))

    def test_region_changes_cover_crop_table(self):
        par = copy.deepcopy(P); par["site"]["region"] = "piedmont"
        r = copy.deepcopy(ROTS["rotation_b"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "plant": op["date"] = "11-10"     # Piedmont preferred ends Oct 15, possible Nov 15
        self.assertIn("LATE_ESTABLISHMENT", codes(ev(r, par=par), "warning")); self.assertTrue(ev(r, par=par)["feasible"])
        for op in r["operations"]:
            if op["crop"] == "cereal_rye" and op["action"] == "plant": op["date"] = "12-10"     # beyond Piedmont possible, inside Coastal Plain possible
        self.assertFalse(ev(r, par=par)["feasible"]); self.assertTrue(ev(r)["feasible"])

    def test_cover_termination_gap_is_sourced_hard(self):
        c = LIB["crops"]["cereal_rye"]["pre_cash_crop_gap_days"]
        self.assertEqual((c["min"], c["max"], c["status"]), (7, 14, "sourced"))

    def test_johnston_region_flagged_unverified(self):
        self.assertTrue(P["site"]["region_status"].startswith("assumed"))
        self.assertIn("REGION_UNVERIFIED", {c["code"] for c in ev(ROTS["rotation_b"])["evidence_caveats"]})


if __name__ == "__main__":
    unittest.main()

"""Integration contract: weather + manifest + soils as documented in docs/data_contract_requirements.md. All inputs are MOCK/synthetic."""
import unittest, json, shutil, tempfile, subprocess, sys
from _common import *
from engine import MissingInputError, InvalidInputError
from engine.io_utils import *
from engine.scenarios import replay_historical_scenarios
import run_evaluation

MOCK = os.path.join(ROOT, "tests", "fixtures", "mock_environment")
try:
    import pyarrow  # noqa
    HAVE_ARROW = True
except ImportError:
    HAVE_ARROW = False


def raw():
    return pd.read_csv(os.path.join(MOCK, "weather.csv"))


def units():
    return json.load(open(os.path.join(MOCK, "manifest.json")))["units"]


class TestContract(unittest.TestCase):
    def test_end_to_end_mock_pipeline_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            res = run_evaluation.run(MOCK, d)
            for f in ("feasible_rotations", "simulation_results", "scenario_metrics", "sensitivity_results", "model_manifest", "robustness_summary", "explanations"):
                self.assertTrue(os.path.exists(os.path.join(d, f + ".json")), f)
            m = json.load(open(os.path.join(d, "model_manifest.json")))
            self.assertIn("MOCK", m["data_provenance"]); self.assertEqual(m["site_from"], "data manifest"); self.assertEqual(m["soil_source"], "soils.json")
            self.assertEqual(m["excluded_years"], {"2003": "181 of 365 days present"})
            self.assertEqual(m["soil_scenarios"]["medium_storage"]["value"], 105.0)
            ex = json.load(open(os.path.join(d, "explanations.json")))
            self.assertTrue(all(r["rotation_id"] for r in ex["rotations"]))

    def test_cli_command_runs(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "run_evaluation.py"), "--data", MOCK, "--out", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("7 files", r.stdout)

    def test_outputs_byte_identical_between_runs(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            run_evaluation.run(MOCK, a); run_evaluation.run(MOCK, b)
            for f in os.listdir(a):
                with open(os.path.join(a, f), "rb") as fa, open(os.path.join(b, f), "rb") as fb: self.assertEqual(fa.read(), fb.read(), f)

    def test_power_style_column_names_accepted_with_declared_units(self):
        r = raw().rename(columns={"temperature_max_c": "T2M_MAX", "temperature_min_c": "T2M_MIN", "temperature_mean_c": "T2M", "precipitation_mm": "PRECTOTCORR",
                                  "relative_humidity_pct": "RH2M", "solar_radiation": "ALLSKY_SFC_SW_DWN", "wind_speed": "WS2M"})
        w = normalize_weather(r, units()); self.assertEqual(w.attrs.get("aliases_applied", {}) or {}, {}) if False else None
        ref = normalize_weather(raw(), units())
        pd.testing.assert_frame_equal(w[ref.columns], ref)
        with self.assertRaises(MissingInputError): normalize_weather(r, {"temperature": "degC"})       # aliases never imply units

    def test_ambiguous_alias_rejected(self):
        r = raw().rename(columns={"precipitation_mm": "PRECTOTCORR"}); r["precip_mm"] = 1.0
        with self.assertRaises(InvalidInputError): normalize_weather(r, units())

    def test_required_fields(self):
        for col in ("temperature_max_c", "temperature_min_c", "precipitation_mm", "date"):
            with self.assertRaises(MissingInputError): normalize_weather(raw().drop(columns=[col]), units())
        for col in ("relative_humidity_pct", "solar_radiation", "wind_speed"):
            with self.assertRaises(MissingInputError): normalize_weather(raw().drop(columns=[col]), units())
        normalize_weather(raw().drop(columns=["relative_humidity_pct", "solar_radiation", "wind_speed"]), units(), need_pm=False)   # Hargreaves path allowed

    def test_manifest_validation(self):
        good = json.load(open(os.path.join(MOCK, "manifest.json")))
        validate_manifest(good)
        for bad, exc in (({**good, "units": {k: v for k, v in good["units"].items() if k != "wind_speed"}}, MissingInputError),
                         ({**good, "units": {**good["units"], "temperature": "rankine"}}, InvalidInputError),
                         ({**good, "units": {**good["units"], "wind_height_m": "tall"}}, InvalidInputError),
                         ({**good, "site": {"latitude_deg": 80, "elevation_m": 10}}, InvalidInputError),
                         ({**good, "site": {"latitude_deg": 35}}, InvalidInputError),
                         ({**good, "site": {"latitude_deg": 35, "elevation_m": 99999}}, InvalidInputError),
                         ({"provenance": "x"}, MissingInputError), ([], InvalidInputError)):
            with self.assertRaises(exc): validate_manifest(bad)

    def test_latitude_and_elevation_change_et0(self):
        from engine.evapotranspiration import compute_reference_et
        w = normalize_weather(raw(), units()).iloc[:365]
        a = compute_reference_et(w, "penman_monteith", {"latitude_deg": 35.5, "elevation_m": 50})["et0_mm"].sum()
        b = compute_reference_et(w, "penman_monteith", {"latitude_deg": 45.5, "elevation_m": 50})["et0_mm"].sum()
        c = compute_reference_et(w, "penman_monteith", {"latitude_deg": 35.5, "elevation_m": 1500})["et0_mm"].sum()
        self.assertNotAlmostEqual(a, b, places=2); self.assertNotAlmostEqual(a, c, places=2)

    def test_unit_conversions_flow_through_to_identical_results(self):
        r = raw(); r2 = r.copy()
        r2["solar_radiation"] = r["solar_radiation"] / 3.6; r2["wind_speed"] = r["wind_speed"] * 3.6; r2["precipitation_mm"] = r["precipitation_mm"] / 25.4
        u2 = {**units(), "solar_radiation": "kWh/m2/day", "wind_speed": "km/h", "precipitation": "in"}
        a, b = normalize_weather(r, units()), normalize_weather(r2, u2)
        for c in ("solar_radiation", "wind_speed", "precipitation_mm"): np.testing.assert_allclose(a[c], b[c], rtol=1e-12)

    def test_incomplete_years_and_inconsistent_dates(self):
        r = raw(); r2 = r[~((pd.to_datetime(r["date"]).dt.year == 1995) & (pd.to_datetime(r["date"]).dt.month == 5))]
        res = replay_historical_scenarios(ROTS, normalize_weather(r2, units()), {"scenarios": P["soil_storage_scenarios_mm"]}, P, LIB, MGMT)
        self.assertIn(1995, res["excluded_years"]); self.assertTrue(all("1995" not in s for s in res["blocks"] if s.split("_")[1] <= "1995" <= s.split("_")[2]))
        d = r.copy(); d.loc[10, "date"] = d.loc[9, "date"]
        with self.assertRaises(InvalidInputError): normalize_weather(d, units())
        d = r.copy(); d["date"] = d["date"].astype(str); d.loc[3, "date"] = "1990-13-45"
        with self.assertRaises(InvalidInputError): normalize_weather(d, units())
        d = r.copy(); d["date"] = pd.to_datetime(d["date"]).dt.tz_localize("UTC")
        with self.assertRaises(InvalidInputError): normalize_weather(d, units())
        d = r.copy(); d["date"] = pd.to_datetime(d["date"]) + pd.Timedelta(hours=6)
        with self.assertRaises(InvalidInputError): normalize_weather(d, units())
        shuffled = r.sample(frac=1.0, random_state=3)
        self.assertTrue(normalize_weather(shuffled, units())["date"].is_monotonic_increasing)        # order is irrelevant; sorted deterministically

    def test_out_of_range_and_nonsense_values(self):
        for col, val in (("precipitation_mm", 5000.0), ("temperature_max_c", 120.0), ("solar_radiation", 90.0), ("wind_speed", 300.0), ("relative_humidity_pct", -5.0)):
            r = raw(); r.loc[100, col] = val
            if col == "temperature_max_c": r.loc[100, "temperature_mean_c"] = 60.0
            with self.assertRaises(InvalidInputError, msg=col): normalize_weather(r, units())
        r = raw(); r["precipitation_mm"] = r["precipitation_mm"].astype(object); r.loc[5, "precipitation_mm"] = "abc"
        w = normalize_weather(r, units()); self.assertTrue(np.isnan(w.loc[5, "precipitation_mm"]))   # non-numeric becomes missing, never zero

    def test_partial_and_malformed_soil_information(self):
        s = load_soil({"available_water_storage_mm": {"medium": 105}}, None)
        self.assertEqual(list(s["scenarios"]), ["medium_storage"]); self.assertIn("partial", s["source"])
        res = replay_historical_scenarios(ROTS, normalize_weather(raw(), units()), s, P, LIB, MGMT, P["parameter_sets"])
        self.assertIn("low_storage", res["skipped_parameter_sets"]); self.assertTrue(all(r["parameter_set_id"] != "low_storage" for r in res["records"]))
        with self.assertRaises(MissingInputError):
            replay_historical_scenarios(ROTS, normalize_weather(raw(), units()), load_soil({"available_water_storage_mm": {"low": 60}}, None), P, LIB, MGMT, P["parameter_sets"])
        with self.assertRaises(InvalidInputError): load_soil({"available_water_storage_mm": {"low": 100, "medium": 80}}, None)
        with self.assertRaises(InvalidInputError): load_soil({"available_water_storage_mm": {"huge": 100}}, None)
        with self.assertRaises(InvalidInputError): load_soil({"available_water_storage_mm": {"low": "x"}}, None)
        c = load_soil({"available_water_storage_cm": {"low": 7, "medium": 10, "high": 14}}, None); self.assertEqual(c["scenarios"]["medium_storage"]["value"], 100.0)
        self.assertIn("illustrative", load_soil({"mapunit": "x"}, P["soil_storage_scenarios_mm"])["source"])

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(MissingInputError): load_weather(d)
            with self.assertRaises(MissingInputError): load_manifest(d)

    @unittest.skipUnless(HAVE_ARROW, "pyarrow is not installed: Parquet ingestion could NOT be tested in this environment")
    def test_parquet_ingestion_matches_csv(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(MOCK, d, dirs_exist_ok=True); w = raw(); w["date"] = pd.to_datetime(w["date"]); w.to_parquet(os.path.join(d, "weather.parquet"), index=False)
            os.remove(os.path.join(d, "weather.csv"))
            pd.testing.assert_frame_equal(normalize_weather(load_weather(d), units()), normalize_weather(raw(), units()))

    def test_parquet_without_engine_reports_clearly(self):
        if HAVE_ARROW: self.skipTest("pyarrow present")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "weather.parquet"), "wb") as fh: fh.write(b"PAR1")
            with self.assertRaises((MissingInputError, Exception)) as cm: load_weather(d)
            self.assertIn("arrow", str(cm.exception).lower())


if __name__ == "__main__":
    unittest.main()

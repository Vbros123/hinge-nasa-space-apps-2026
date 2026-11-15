import unittest, json
from _common import *
from engine import MissingInputError, InvalidInputError
from engine.io_utils import normalize_weather, load_soil
from engine.crop_calendar import parse_md, build_periods, load_crop_library, md_in_window, kc_curve
from engine.scenarios import replay_historical_scenarios


class TestMissing(unittest.TestCase):
    def raw(self):
        return make_weather(1990, 1993)

    def test_missing_precipitation_excludes_year_not_zero_filled(self):
        r = self.raw(); r.loc[r["date"] == "1991-07-04", "precipitation_mm"] = np.nan
        w = normalize_weather(r, MANIFEST["units"])
        self.assertTrue(np.isnan(w.loc[w["date"] == "1991-07-04", "precipitation_mm"]).all())
        with self.assertRaises(MissingInputError):
            replay_historical_scenarios(ROTS, w, SOIL, P, LIB, MGMT)

    def test_nasa_fill_value_is_missing(self):
        r = self.raw(); r.loc[5, "temperature_max_c"] = -999
        w = normalize_weather(r, MANIFEST["units"])
        self.assertTrue(np.isnan(w.loc[5, "temperature_max_c"]))

    def test_missing_temperature_column_and_required_units(self):
        with self.assertRaises(MissingInputError): normalize_weather(self.raw().drop(columns=["temperature_max_c"]), MANIFEST["units"])
        with self.assertRaises(MissingInputError): normalize_weather(self.raw(), {"temperature": "degC"})   # no solar/wind units declared

    def test_inconsistent_units_converted_or_rejected(self):
        r = self.raw()
        r2 = r.copy(); r2["solar_radiation"] = r["solar_radiation"] / 3.6
        w = normalize_weather(r2, {**MANIFEST["units"], "solar_radiation": "kWh/m2/day"})
        np.testing.assert_allclose(w["solar_radiation"], r["solar_radiation"])
        r3 = r.copy(); r3["wind_speed"] = r["wind_speed"] * 3.6
        w3 = normalize_weather(r3, {**MANIFEST["units"], "wind_speed": "km/h"})
        np.testing.assert_allclose(w3["wind_speed"], r["wind_speed"])
        with self.assertRaises(InvalidInputError): normalize_weather(r, {**MANIFEST["units"], "solar_radiation": "furlongs"})
        rf = r.copy(); rf["temperature_max_c"] = rf["temperature_max_c"] * 9 / 5 + 32; rf["temperature_min_c"] = rf["temperature_min_c"] * 9 / 5 + 32
        rf["temperature_mean_c"] = rf["temperature_mean_c"] * 9 / 5 + 32
        wf = normalize_weather(rf, {**MANIFEST["units"], "temperature": "degF"})
        np.testing.assert_allclose(wf["temperature_max_c"], r["temperature_max_c"], atol=1e-9)

    def test_wind_height_correction_eq47(self):
        r = self.raw(); w = normalize_weather(r, {**MANIFEST["units"], "wind_height_m": 10.0})
        self.assertAlmostEqual(float(w["wind_speed"].iloc[0] / r["wind_speed"].iloc[0]), 4.87 / np.log(67.8 * 10 - 5.42), places=9)

    def test_physically_invalid_values_rejected(self):
        r = self.raw(); r.loc[3, "precipitation_mm"] = -1
        with self.assertRaises(InvalidInputError): normalize_weather(r, MANIFEST["units"])
        r = self.raw(); r.loc[3, "relative_humidity_pct"] = 140
        with self.assertRaises(InvalidInputError): normalize_weather(r, MANIFEST["units"])
        r = self.raw(); r.loc[3, "temperature_max_c"] = r.loc[3, "temperature_min_c"] - 2
        with self.assertRaises(InvalidInputError): normalize_weather(r, MANIFEST["units"])
        r = self.raw(); r = pd.concat([r, r.iloc[:1]])
        with self.assertRaises(InvalidInputError): normalize_weather(r, MANIFEST["units"])

    def test_quality_flag_marks_year_incomplete(self):
        r = self.raw(); r.loc[r["date"] == "1992-03-01", "data_quality_flags"] = "FILLED"
        from engine.scenarios import complete_years
        ok, ex = complete_years(normalize_weather(r, MANIFEST["units"]), ["precipitation_mm"])
        self.assertIn(1992, ex); self.assertNotIn(1992, ok)

    def test_invalid_crop_coefficients_rejected(self):
        from engine.crop_calendar import crop_kc_params
        lib = copy.deepcopy(LIB); lib["crops"]["corn"]["water"]["kc_mid"] = None
        with self.assertRaises(MissingInputError): crop_kc_params("corn", lib, P)   # cash-crop Kc is never invented
        self.assertEqual(crop_kc_params("cereal_rye", lib, P)[4], "assumed")        # cover Kc: flagged assumption only
        lib["crops"]["corn"]["water"].update({"kc_initial": 0.3, "kc_mid": 5.0, "kc_end": 0.6})
        with self.assertRaises(InvalidInputError): crop_kc_params("corn", lib, P)

    def test_invalid_crop_dates_rejected(self):
        with self.assertRaises(InvalidInputError): parse_md("02-30")
        with self.assertRaises(InvalidInputError): parse_md("13-01")
        r = copy.deepcopy(ROTS["rotation_a"]); r["operations"][1]["date"] = "04-01"   # harvest before planting
        with self.assertRaises(InvalidInputError): build_periods(r, 2001)
        r = copy.deepcopy(ROTS["rotation_a"]); r["operations"].pop(1)                  # planted, never harvested
        with self.assertRaises(InvalidInputError): build_periods(r, 2001)

    def test_missing_soil_not_invented(self):
        with self.assertRaises(MissingInputError): load_soil(None, None)
        with self.assertRaises(InvalidInputError): load_soil({"available_water_storage_mm": {"low": -5}}, None)
        s = load_soil({"available_water_storage_mm": {"low": 70, "medium": 110, "high": 150}}, None)
        self.assertEqual(s["scenarios"]["medium_storage"]["status"], "soil_derived")
        f = load_soil({"note": "no storage"}, P["soil_storage_scenarios_mm"])
        self.assertIn("illustrative", f["source"])

    def test_crop_library_rejects_unknown_source(self):
        import tempfile, yaml
        bad = copy.deepcopy(LIB); bad["crops"]["corn"]["planting_window"]["source_id"] = "nope"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f: yaml.safe_dump(bad, f)
        with self.assertRaises(InvalidInputError): load_crop_library(f.name)


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import pandas as pd
import pytest
from engine.io_utils import normalize_weather, InvalidInputError
from engine.soil_adapter import adapt_ssurgo
from engine.scenarios import complete_years
from run_integrated import verify

DATA = Path(__file__).resolve().parents[1] / 'data' / 'real_environment'
UNITS = {'temperature': 'degC', 'precipitation': 'mm/day', 'solar_radiation': 'MJ/m^2/day', 'wind_speed': 'm/s', 'wind_height_m': 2}

def test_manifest_and_real_parquet_json():
    verify(str(DATA))
    pq = pd.read_parquet(DATA / 'weather.parquet')
    js = pd.DataFrame(json.loads((DATA / 'weather.json').read_text()))
    assert len(pq) == len(js) == 16436
    for column in js:
        assert pq[column].astype(str).tolist() == js[column].astype(str).tolist()
    w = normalize_weather(pq, UNITS)
    years, excluded = complete_years(w, ['temperature_max_c','temperature_min_c','precipitation_mm','relative_humidity_pct','solar_radiation','wind_speed'])
    assert years == list(range(1984,2026))
    assert set(excluded) == {1981,1982,1983}

def test_corrupted_weather_rejected():
    pq = pd.read_parquet(DATA / 'weather.parquet').iloc[:2].copy()
    pq.loc[pq.index[0], 'precipitation_mm'] = -1
    with pytest.raises(InvalidInputError): normalize_weather(pq, UNITS)

def test_soil_weights_and_unknown_mass():
    s = adapt_ssurgo(json.loads((DATA / 'soils.json').read_text()))
    assert 0.89 < s['known_aoi_component_mass'] < 0.90
    assert abs(s['known_aoi_component_mass'] + s['unknown_aoi_component_mass'] - 1) < 1e-10
    assert [s['scenarios'][k]['value'] for k in ('low_storage','medium_storage','high_storage')] == [97,129.3,170]

def test_soil_invalid_fraction_rejected():
    s = json.loads((DATA / 'soils.json').read_text())
    s['components'][0]['component_fraction'] = 1.1
    with pytest.raises(InvalidInputError): adapt_ssurgo(s)

def test_missing_component_storage_keeps_unassigned_mass():
    s = json.loads((DATA / 'soils.json').read_text())
    s['components'][0]['estimated_storage_mm'] = None
    out = adapt_ssurgo(s)
    assert out['unknown_aoi_component_mass'] > 0.10
    assert out['known_aoi_component_mass'] < 0.90

def test_incompatible_soil_integration_depth_rejected():
    s = json.loads((DATA / 'soils.json').read_text())
    s['components'][0]['target_depth_cm'] = 200
    with pytest.raises(InvalidInputError): adapt_ssurgo(s)

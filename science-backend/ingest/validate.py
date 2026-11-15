from pathlib import Path
import json
import numpy as np
import pandas as pd
from .common import read,dump
from .power import COLUMNS

def validate(out):
    out=Path(out);checks={};errors=[]
    def check(name,fn):
        try:checks[name]=bool(fn())
        except Exception as e:checks[name]=False;errors.append({'check':name,'error':str(e)})
    def weather():
        d=pd.read_parquet(out/'weather.parquet')
        j=read(out/'weather.json')
        assert len(d)==len(j)>0 and not d.duplicated(['polygon_id','date']).any()
        assert set(COLUMNS.values())<=set(d)
        dates=pd.to_datetime(d.date)
        assert len(d)==len(pd.date_range(dates.min(),dates.max()))
        assert set(d.time_standard)=={'LST'}
        for s in d.data_quality_flags:assert isinstance(json.loads(s),list)
        v=d.loc[d.model_ready]
        assert v[list(COLUMNS.values())].notna().all().all()
        assert (v.precipitation_mm>=0).all() and (v.temperature_min_c<=v.temperature_max_c).all()
        return True
    check('weather_contract',weather)
    check('twenty_model_ready_years',lambda:len(read(out/'weather_metadata.json')['model_ready_years'])>=20)
    def soils():
        s=read(out/'soils.json');h=pd.read_parquet(out/'soil_horizons.parquet')
        assert s['components'] and len(h)>0
        assert all(c['component_fraction'] is None or 0<=c['component_fraction']<=1 for c in s['components'])
        assert all(v<=1.001 for v in s['component_fraction_sums'].values())
        assert s['mapped_aoi_fraction']<=1.01
        for _,r in h.iterrows():
            if pd.notna(r.horizon_top_cm) and pd.notna(r.horizon_bottom_cm):assert r.horizon_top_cm<r.horizon_bottom_cm
        return True
    check('soil_contract',soils)
    def vegetation():
        d=pd.read_parquet(out/'vegetation.parquet')
        assert len(d)>0 and not d.duplicated(['polygon_id','dataset_id','observation_date']).any()
        for c in ['valid_pixel_fraction','spatial_coverage_fraction']:assert d[c].between(0,1).all()
        assert (d.valid_pixel_fraction<=d.spatial_coverage_fraction+1e-9).all()
        assert d.ndvi_median.dropna().between(-1,1).all()
        assert (d.valid_pixel_count>0).any()
        return True
    check('vegetation_contract',vegetation)
    check('hls_independent_pixel_calculation',lambda:read(out/'vegetation_metadata.json')['pixel_validation_passed'])
    check('power_separate_csv_comparison',lambda:read(out/'power_csv_validation.json')['passed'])
    check('soil_separate_export_comparison',lambda:read(out/'soil_profile_validation.json')['passed'])
    def evidence():
        e=read(out/'validation_evidence.json')
        for k in ['power_csv','soil_export']:
            assert e[k]['source_url'].startswith('https://')
            assert e[k]['retrieved_at'] and e[k]['method'] and e[k]['source_sha256']
        assert e['power_csv']['time_standard']=='LST'
        assert e['power_csv']['solar_unit']=='MJ/m^2/day'
        for k,name in [('power_csv','power_csv_validation.json'),('soil_export','soil_profile_validation.json')]:
            r=read(out/name)
            digest=r.get('input_sha256',r.get('reference_sha256'))
            assert digest==e[k]['source_sha256']
        return True
    check('validation_evidence_complete',evidence)
    def identity():
        pid=read(out/'field.geojson')['properties']['polygon_id']
        for name in ['weather','vegetation','vegetation_scenes','vegetation_seasonal','soil_horizons']:
            f=pd.read_parquet(out/(name+'.parquet'))
            assert len(f)>0 and set(f.polygon_id)=={pid}
        assert read(out/'soils.json')['polygon_id']==pid
        return True
    check('shared_polygon_identity',identity)
    def machine_contract():
        spec=read(Path(__file__).resolve().parents[1]/'docs/contract.json')
        for name in ['weather','vegetation','soil_horizons']:
            f=pd.read_parquet(out/(name+'.parquet'))
            assert set(spec[name]['required']).issubset(f.columns)
        return True
    check('machine_readable_contract',machine_contract)
    def source_archives():
        from .common import sha
        for folder in ['power','ssurgo']:
            metas=list((out/'raw'/folder).glob('*.meta.json'));assert metas
            for f in metas:
                m=read(f);body=f.with_name(f.name.replace('.meta.json','.response'))
                assert sha(body)==m['response_sha256']
        assert read(out/'raw/hls/search.json')['items']
        assert list((out/'raw/hls').glob('*.npz'))
        return True
    check('archived_sources_present',source_archives)
    result={'passed':all(checks.values()),'checks':checks,'errors':errors,
      'meaning':'Automated acceptance gates only; agronomic/source-resolution review remains required'}
    dump(out/'validation_report.json',result);return result

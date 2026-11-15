#!/usr/bin/env python3
"""Validate cached source bundle and execute the model without network access."""
import argparse, hashlib, json, os, sys, copy
from engine.soil_adapter import adapt_ssurgo
from engine.vegetation_adapter import vegetation_context
from engine.io_utils import load_weather, normalize_weather, sha256_file
import run_evaluation

EXPECTED = {'T2M':'C','T2M_MAX':'C','T2M_MIN':'C','PRECTOTCORR':'mm/day','RH2M':'%','WS2M':'m/s','ALLSKY_SFC_SW_DWN':'MJ/m^2/day'}

def verify(data):
    manifest = json.load(open(os.path.join(data,'manifest.json')))
    if manifest.get('schema_version') != 'hinge.environment.v2' or not manifest.get('validation',{}).get('passed'):
        raise ValueError('Environmental final run has not passed automated gates')
    for name,digest in manifest['file_sha256'].items():
        path=os.path.join(data,name)
        if not os.path.isfile(path) or sha256_file(path)!=digest:
            raise ValueError('Source hash mismatch: '+name)
    meta=json.load(open(os.path.join(data,'weather_metadata.json')))
    seen={}
    for req in meta['requests']:
        key=req['arguments']['parameters']
        if key in EXPECTED:
            unit=req['parameter_metadata'][key]['units']
            if key in seen and seen[key]!=unit: raise ValueError('Inconsistent POWER units: '+key)
            seen[key]=unit
            if req['header']['time_standard']!='LST' or req['arguments']['time-standard']!='LST':
                raise ValueError('Unexpected POWER time standard')
    if seen!=EXPECTED: raise ValueError('POWER units mismatch: '+str(seen))
    return manifest,meta

def run(data, out):
    manifest,meta=verify(data)
    original=run_evaluation.load_manifest
    original_soil=run_evaluation.load_soil
    source_point=next(q['source_geometry']['coordinates'] for q in meta['requests'] if q['arguments']['parameters']=='T2M')
    def adapted_manifest(_):
        return {'units': {'temperature':'degC','precipitation':'mm/day','solar_radiation':'MJ/m^2/day','wind_speed':'m/s','wind_height_m':2},
                'site': {'latitude_deg': source_point[1], 'elevation_m': source_point[2], 'name': 'NASA POWER source grid point', 'status': 'source-reported grid elevation; not field survey', 'note': 'POWER source geometry; field elevation unverified'},
                'site_source': 'NASA POWER archived source_geometry (grid point/elevation; not surveyed field elevation)',
                'provenance': {'source_manifest_sha256':sha256_file(os.path.join(data,'manifest.json')), 'schema_version':manifest['schema_version'], 'polygon_id':manifest['polygon_id'], 'time_standard':'NASA POWER LST'}}
    def adapted_soil(path, fallback):
        with open(path) as f: return adapt_ssurgo(json.load(f))
    run_evaluation.load_manifest=adapted_manifest
    run_evaluation.load_soil=adapted_soil
    try:
        result=run_evaluation.run(data,out)
    finally:
        run_evaluation.load_manifest=original
        run_evaluation.load_soil=original_soil
    with open(os.path.join(out,'vegetation_context.json'),'w') as f:
        json.dump(vegetation_context(data),f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    model_path=os.path.join(out,'model_manifest.json')
    with open(model_path) as f: model_manifest=json.load(f)
    model_manifest['soil_coverage']={k:v for k,v in adapted_soil(os.path.join(data,'soils.json'),None).items() if k in ('known_aoi_component_mass','unknown_aoi_component_mass','component_count','method')}
    with open(model_path,'w') as f: json.dump(model_manifest,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    expl_path=os.path.join(out,'explanations.json')
    with open(expl_path) as f: explanations=json.load(f)
    explanations['observed_vegetation_context']={'file':'vegetation_context.json','interpretation':'2025 observed HLS NDVI is separate from all modeled rotation cover outcomes'}
    with open(expl_path,'w') as f: json.dump(explanations,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',default='data/real_environment');p.add_argument('--out',default='output/real_environment');a=p.parse_args()
    r=run(a.data,a.out)
    print(len(r['records']),'records;',len(r['blocks']),'blocks;',len(r['usable_years']),'years')

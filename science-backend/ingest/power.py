import calendar,json
import numpy as np
import pandas as pd
from .common import retrieve,table,dump
URL='https://power.larc.nasa.gov/api/temporal/daily/point'
COLUMNS={'T2M':'temperature_mean_c','T2M_MAX':'temperature_max_c','T2M_MIN':'temperature_min_c',
 'PRECTOTCORR':'precipitation_mm','RH2M':'relative_humidity_pct',
 'ALLSKY_SFC_SW_DWN':'solar_radiation_mj_m2_day','WS2M':'wind_speed_m_s'}
UNITS={'T2M':{'C':1},'T2M_MAX':{'C':1},'T2M_MIN':{'C':1},'PRECTOTCORR':{'mm/day':1,'mm':1},
 'RH2M':{'%':1},'ALLSKY_SFC_SW_DWN':{'MJ/m^2/day':1,'MJ/m2/day':1,'kW-hr/m^2/day':3.6,'kWh/m^2/day':3.6},'WS2M':{'m/s':1}}

def parse(body,parameter,index):
    meta=body['parameters'][parameter];unit=meta['units']
    if unit not in UNITS[parameter]:raise ValueError(f'Unrecognized {parameter} unit: {unit}')
    raw=body['properties']['parameter'][parameter]
    s=pd.Series(raw,dtype=float)
    s.index=pd.to_datetime(s.index,format='%Y%m%d')
    if s.index.duplicated().any():raise ValueError('Duplicate source dates')
    if len(s.index.difference(index)):raise ValueError('Dates outside request')
    fill=body.get('header',{}).get('fill_value',-999)
    return s.reindex(index).replace(fill,np.nan)*UNITS[parameter][unit]

def quality(df):
    flags=[[] for _ in range(len(df))]
    for c in COLUMNS.values():
        for i in np.flatnonzero(df[c].isna().to_numpy()):flags[i].append('missing:'+c)
    conditions={
      'min_exceeds_max':df.temperature_min_c>df.temperature_max_c,
      'mean_outside_extrema':(df.temperature_mean_c<df.temperature_min_c)|(df.temperature_mean_c>df.temperature_max_c),
      'negative_precipitation':df.precipitation_mm<0,
      'humidity_out_of_range':(df.relative_humidity_pct<0)|(df.relative_humidity_pct>100),
      'negative_wind':df.wind_speed_m_s<0,'negative_solar':df.solar_radiation_mj_m2_day<0,
      'review_temperature_extreme':(df.temperature_min_c < -60)|(df.temperature_max_c > 60),
      'review_precipitation_extreme':df.precipitation_mm>500,
      'review_radiation_extreme':df.solar_radiation_mj_m2_day>50,
      'review_wind_extreme':df.wind_speed_m_s>60}
    for flag,bad in conditions.items():
        for i in np.flatnonzero(bad.to_numpy()):flags[i].append(flag)
    df['data_quality_flags']=[json.dumps(f) for f in flags]
    df['model_ready']=[not f for f in flags]
    return df

def ingest(feature,geom,start,end,out,offline=False):
    from pathlib import Path
    out=Path(out); raw=out/'raw/power';point=geom.representative_point()
    frames,requests,errors=[],[],[]
    for year in range(start,end+1):
        index=pd.date_range(f'{year}-01-01',f'{year}-12-31')
        df=pd.DataFrame(index=index)
        for parameter,column in COLUMNS.items():
            args={'parameters':parameter,'community':'AG','latitude':point.y,'longitude':point.x,
              'start':f'{year}0101','end':f'{year}1231','format':'JSON','time-standard':'LST'}
            try:
                body,meta=retrieve(URL,args,raw,offline=offline)
                df[column]=parse(body,parameter,index)
                requests.append(dict(meta,parameter_metadata=body.get('parameters'),header=body.get('header'),
                                     source_geometry=body.get('geometry')))
            except Exception as e:
                df[column]=np.nan;errors.append({'year':year,'parameter':parameter,'error':str(e)})
        df=quality(df)
        df['date']=index.strftime('%Y-%m-%d');df['year']=year
        df['latitude']=point.y;df['longitude']=point.x
        df['polygon_id']=feature['properties']['polygon_id'];df['time_standard']='LST'
        frames.append(df.reset_index(drop=True))
        if year==start and not requests:
            dump(out/'weather_failure.json',{'status':'blocked','errors':errors})
            raise RuntimeError('All first-year POWER requests failed; aborting baseline')
    df=pd.concat(frames,ignore_index=True)
    annual=[]
    for year,g in df.groupby('year'):
        expected=366 if calendar.isleap(int(year)) else 365
        counts={c:int(g[c].notna().sum()) for c in COLUMNS.values()}
        annual.append({'year':int(year),'expected_days':expected,'rows':len(g),
          'nonmissing_by_column':counts,'model_ready_days':int(g.model_ready.sum()),
          'model_ready_year':len(g)==expected and bool(g.model_ready.all())})
    table(df,out,'weather')
    report={'source':'NASA POWER','url':URL,'requests':requests,'errors':errors,'years':annual,
      'model_ready_years':[a['year'] for a in annual if a['model_ready_year']],
      'classification':'source_product; reanalysis/satellite-derived, not field station measurements',
      'outlier_policy':'Conservative review thresholds; source values retained, not clipped or imputed',
      'transformations':['fill values to null','complete daily calendar','documented unit conversions'],
      'spatial_support':'Source grid, not field resolution; parameter headers retained; inspect source-specific documentation'}
    dump(out/'weather_metadata.json',report)
    if not df[list(COLUMNS.values())].notna().any().any():raise RuntimeError('No authentic weather values')
    return report

def compare_csv(out,path):
    from pathlib import Path
    out=Path(out);df=pd.read_parquet(out/'weather.parquet')
    lines=Path(path).read_text().splitlines()
    end=next((i for i,l in enumerate(lines) if '-END HEADER-' in l),-1)
    from io import StringIO
    independent=pd.read_csv(StringIO('\n'.join(lines[end+1:])))
    if not {'YEAR','MO','DY'}.issubset(independent):raise ValueError('Expected NASA POWER daily CSV YEAR, MO, DY')
    independent['date']=pd.to_datetime(dict(year=independent.YEAR,month=independent.MO,day=independent.DY)).dt.strftime('%Y-%m-%d')
    joined=df.merge(independent,on='date',validate='one_to_one')
    if not len(joined):raise ValueError('No validation dates overlap')
    result={}
    for p,c in COLUMNS.items():
        if p not in independent:continue
        a=pd.to_numeric(joined[p],errors='coerce').replace(-999,np.nan)
        # CSV must be AG, LST, with units identical to canonical output; solar checked in evidence file.
        valid=a.notna() & joined[c].notna()
        result[p]={'n':int(valid.sum()),'max_abs_error':float((a[valid]-joined.loc[valid,c]).abs().max()) if valid.any() else None}
    report={'method':'separate POWER CSV transport; same underlying provider, not independent weather truth',
      'results':result,'input_sha256':__import__('hashlib').sha256(Path(path).read_bytes()).hexdigest(),
      'passed':len(result)==7 and all(r['n']>0 and r['max_abs_error']<=.011 for r in result.values())}
    dump(out/'power_csv_validation.json',report);return report

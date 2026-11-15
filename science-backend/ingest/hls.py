import math,hashlib,time
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from .common import dump,read,now,table
COLLECTIONS=['hls2-l30','hls2-s30']
CATALOG='https://planetarycomputer.microsoft.com/api/stac/v1'

def ndvi(red,nir,qa,covered):
    valid=covered & (qa!=255) & ((qa & 62)==0) & (((qa>>6)&3)!=3)
    valid &= (red>=0)&(nir>=0)&(red<12000)&(nir<12000)
    r,n=red.astype(float)*.0001,nir.astype(float)*.0001
    valid &= np.isfinite(r)&np.isfinite(n)&((r+n)>1e-10)
    v=np.full(r.shape,np.nan);np.divide(n-r,n+r,out=v,where=valid)
    return v,valid

def mosaic(parts,shape):
    # Lexically sorted scene order; first valid pixel wins. Each target pixel counted once.
    values=np.full(shape,np.nan);coverage=np.zeros(shape,bool);owner=np.full(shape,-1,dtype='int32')
    for i,(scene,v,valid,covered) in enumerate(sorted(parts,key=lambda p:p[0])):
        take=valid & ~np.isfinite(values);values[take]=v[take];owner[take]=i;coverage |= covered
    return values,coverage,owner

def seasonal(frame,start,end,pid):
    rows=[]
    for year in range(int(start[:4]),int(end[:4])+1):
        for name,m0,m1 in [('annual',1,12),('spring',3,5),('summer',6,8),('autumn',9,11),('winter_jan_feb',1,2),('winter_dec',12,12)]:
            dates=pd.to_datetime(frame.observation_date,utc=True) if len(frame) else pd.Series([],dtype='datetime64[ns, UTC]')
            g=frame.loc[(dates.dt.year==year)&dates.dt.month.between(m0,m1)] if len(frame) else frame
            usable=g.loc[g.valid_pixel_fraction>=.5] if len(g) else g
            v=usable.ndvi_median.dropna() if len(usable) else pd.Series([],dtype=float)
            unique=pd.DatetimeIndex(pd.to_datetime(usable.observation_date,utc=True)).unique().sort_values() if len(usable) else pd.DatetimeIndex([],tz='UTC')
            first=pd.Timestamp(year,m0,1,tz='UTC');last=pd.Timestamp(year,m1,1,tz='UTC')+pd.offsets.MonthEnd(1)
            first=max(first,pd.Timestamp(start,tz='UTC'));last=min(last,pd.Timestamp(end,tz='UTC'))
            if first>last:continue
            endpoints=pd.DatetimeIndex([first,*unique,last]).sort_values()
            gaps=(endpoints[1:]-endpoints[:-1]).days
            rows.append({'polygon_id':pid,'year':year,'season':name,'observations':len(g),'usable_observations':len(usable),
              'ndvi_median_of_observations':float(v.median()) if len(v) else None,
              'ndvi_min_observed':float(v.min()) if len(v) else None,'ndvi_max_observed':float(v.max()) if len(v) else None,
              'max_gap_days_including_edges':int(max(gaps)) if len(gaps) else 0,
              'summary_status':'observed_summary' if len(v) else 'insufficient_observations'})
    return pd.DataFrame(rows)

def ingest(feature,geom,start,end,out,offline=False):
    import rasterio
    from rasterio.warp import reproject,transform_geom,Resampling
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin
    from pyproj import CRS,Transformer
    from shapely.ops import transform
    from pystac_client import Client
    from pystac_client.stac_api_io import StacApiIO
    from urllib3.util.retry import Retry
    import planetary_computer as pc
    out=Path(out);raw=out/'raw/hls';raw.mkdir(parents=True,exist_ok=True)
    manifest=raw/'search.json'
    query={'collections':COLLECTIONS,'intersects':feature['geometry'],'datetime':f'{start}T00:00:00Z/{end}T23:59:59Z'}
    if manifest.exists():
        search=read(manifest)
        if search['query']!=query:raise ValueError('Different HLS query in existing output; use a fresh output directory')
        items=search['items']
    else:
        if offline:raise RuntimeError('HLS search cache missing')
        api=Client.open(CATALOG,stac_io=StacApiIO(timeout=90,max_retries=Retry(total=4,backoff_factor=1,status_forcelist=[429,500,502,503,504])))
        items=[i.to_dict() for i in api.search(**query).items()]
        dump(manifest,{'catalog':CATALOG,'query':query,'retrieved_at':now(),'items':items})
    if not items:raise RuntimeError('No HLS scenes returned; no vegetation evidence')
    lon,lat=geom.representative_point().coords[0]
    if not -80<lat<84:raise ValueError('Current canonical-grid implementation requires UTM-valid latitude')
    zone=min(60,max(1,int((lon+180)//6)+1));epsg=(32600 if lat>=0 else 32700)+zone
    crs=f'EPSG:{epsg}';tr=Transformer.from_crs(4326,epsg,always_xy=True)
    g=transform(tr.transform,geom);x0,y0,x1,y1=g.bounds
    left,bottom=math.floor(x0/30)*30,math.floor(y0/30)*30
    right,top=math.ceil(x1/30)*30,math.ceil(y1/30)*30
    width,height=int(round((right-left)/30)),int(round((top-bottom)/30))
    if width*height>4_000_000:raise ValueError('AOI too large for local demo processing; reduce AOI')
    affine=from_origin(left,top,30,30);shape=(height,width)
    inside=geometry_mask([g.__geo_interface__],shape,affine,invert=True,all_touched=False)
    denominator=int(inside.sum())
    if not denominator:raise ValueError('AOI has no 30-m pixel centers')
    dump(raw/'grid.json',{'crs':crs,'transform':list(affine),'shape':shape,'aoi_pixel_count':denominator,
      'rule':'30m UTM canonical target, nearest neighbor, pixel centers; all fractions denominator full AOI pixel count'})
    groups=defaultdict(list);scene_rows=[];sample_checks=[]
    for item in sorted(items,key=lambda i:i['id']):
        collection=item['collection'];scene=item['id'];dt=item['properties']['datetime']
        nir_key='B05' if collection=='hls2-l30' else 'B8A'
        keys=['B04',nir_key,'Fmask']
        token=hashlib.sha256((collection+scene).encode()).hexdigest()
        cache=raw/(token+'.npz')
        if cache.exists():
            with np.load(cache) as z: red,nir,qa=z['red'],z['nir'],z['qa']
        else:
            if offline:raise RuntimeError('HLS raster cache missing for '+scene)
            arrays=[]
            for key in keys:
                href=item['assets'][key]['href'];last_error=None
                for attempt in range(4):
                    try:
                        with rasterio.Env(GDAL_HTTP_MAX_RETRY=3,GDAL_HTTP_RETRY_DELAY=2,GDAL_HTTP_TIMEOUT=90):
                            with rasterio.open(pc.sign(href)) as src:
                                a=np.full(shape,255 if key=='Fmask' else -9999,dtype='int32')
                                reproject(source=rasterio.band(src,1),destination=a,src_transform=src.transform,src_crs=src.crs,
                                  src_nodata=255 if key=='Fmask' else -9999,dst_transform=affine,dst_crs=crs,
                                  dst_nodata=255 if key=='Fmask' else -9999,resampling=Resampling.nearest)
                                arrays.append(a);last_error=None;break
                    except Exception as e:last_error=e;time.sleep(2**attempt)
                if last_error:raise RuntimeError(f'HLS asset failed {scene}/{key}: {last_error}')
            red,nir,qa=arrays;qa=qa.astype('uint8')
            np.savez_compressed(cache,red=red,nir=nir,qa=qa)
            # Preserve one source-grid pixel for an independent scalar computation, before target-grid processing.
            indices=np.argwhere(inside & (qa!=255) & (red>0) & (nir>0))
            if len(indices):
                rr,cc=map(int,indices[len(indices)//2]);xx,yy=rasterio.transform.xy(affine,rr,cc)
                scalar={}
                for key in keys:
                    with rasterio.open(pc.sign(item['assets'][key]['href'])) as src:
                        px,py=Transformer.from_crs(crs,src.crs,always_xy=True).transform(xx,yy)
                        scalar[key]=int(next(src.sample([(px,py)]))[0])
                dump(raw/(token+'.sample.json'),{'scene_id':scene,'target_row':rr,'target_col':cc,'source_samples':scalar,
                  'target_values':{'B04':int(red[rr,cc]),nir_key:int(nir[rr,cc]),'Fmask':int(qa[rr,cc])}})
        footprint=transform_geom('EPSG:4326',crs,item['geometry'])
        footprint_mask=geometry_mask([footprint],shape,affine,invert=True,all_touched=False)
        covered=inside & footprint_mask & (qa!=255) & (red!=-9999) & (nir!=-9999)
        values,valid=ndvi(red,nir,qa,covered)
        groups[(collection,dt[:10])].append((scene,values,valid,covered))
        vals=values[valid];q=np.percentile(vals,[25,50,75]).tolist() if len(vals) else [None]*3
        scene_rows.append({'polygon_id':feature['properties']['polygon_id'],'dataset_id':collection,'scene_id':scene,
          'acquisition_datetime':dt,'observation_date':dt[:10],'ndvi_p25':q[0],'ndvi_median':q[1],'ndvi_p75':q[2],
          'valid_pixel_count':int(valid.sum()),'valid_pixel_fraction':float(valid.sum()/denominator),
          'spatial_coverage_fraction':float(covered.sum()/denominator),'aoi_pixel_count':denominator})
        samplefile=raw/(token+'.sample.json')
        if samplefile.exists():
            sample=read(samplefile);s=sample['source_samples'];t=sample['target_values']
            aligned=all(s[k]==t[k] for k in keys)
            r,n=s['B04'],s[nir_key];qflag=s['Fmask']
            usable=qflag!=255 and (qflag&62)==0 and ((qflag>>6)&3)!=3 and 0<=r<12000 and 0<=n<12000 and r+n>0
            expected=(float(n)-float(r))/(float(n)+float(r)) if usable else None
            rr,cc=sample['target_row'],sample['target_col'];actual=values[rr,cc]
            same=(expected is None and not np.isfinite(actual)) or (expected is not None and np.isfinite(actual) and abs(expected-actual)<1e-12)
            sample_checks.append({'scene_id':scene,'source_target_alignment':aligned,'independent_scalar_matches':bool(same),
              'valid_scalar_sample':usable,'passed':bool(aligned and same)})
    rows=[]
    for (collection,date),parts in sorted(groups.items()):
        v,coverage,owner=mosaic(parts,shape);valid=inside & np.isfinite(v);vals=v[valid]
        q=np.percentile(vals,[25,50,75]).tolist() if len(vals) else [None]*3
        fraction=float(valid.sum()/denominator)
        scene_ids=sorted(p[0] for p in parts)
        times=[s['acquisition_datetime'] for s in scene_rows if s['scene_id'] in scene_ids]
        rows.append({'polygon_id':feature['properties']['polygon_id'],'dataset_id':collection,'dataset_version':'2.0','observation_date':date,
          'acquisition_datetimes':times,'scene_ids':scene_ids,'ndvi_p25':q[0],'ndvi_median':q[1],'ndvi_p75':q[2],
          'valid_pixel_count':int(valid.sum()),'valid_pixel_fraction':fraction,
          'spatial_coverage_fraction':float((coverage & inside).sum()/denominator),'aoi_pixel_count':denominator,
          'quality_flag':'no_valid_pixels' if not len(vals) else ('low_valid_fraction' if fraction<.5 else 'usable'),
          'observation_status':'observed' if len(vals) else 'masked_out'})
        np.savez_compressed(raw/(collection+'_'+date+'_mosaic.npz'),ndvi=v,owner=owner,inside=inside)
    frame=pd.DataFrame(rows);table(frame,out,'vegetation');table(pd.DataFrame(scene_rows),out,'vegetation_scenes')
    summaries=seasonal(frame,start,end,feature['properties']['polygon_id']);table(summaries,out,'vegetation_seasonal')
    report={'source':'NASA HLS v2.0, distributed by Microsoft Planetary Computer','collections':COLLECTIONS,'catalog':CATALOG,
      'scene_count':len(scene_rows),'composite_count':len(rows),'grid_crs':crs,'pixel_size_m':30,
      'mask_policy':'Fmask bits 1–5 and high aerosol (bits 6–7=3); fill; DN<0 or >=12000; zero denominator',
      'scale':.0001,'overlap_policy':'One composite per collection/UTC date; lexical scene ID first VALID target pixel wins',
      'coverage_denominator':'ALL AOI pixel centers on canonical grid, not scene-only pixels',
      'seasonal_policy':'Observation summaries only; >=0.5 valid fraction is assumed display threshold, no interpolation',
      'limitations':['UTC daily composites may combine multiple acquisition times; times retained',
        'L30 and S30 remain separate observations, not independent days for temporal weighting',
        'No crop identity, yield, soil health, residue or planting-date inference',
        '30m nearest-neighbor resampling changes sampling; target-grid statistics, not exact native-grid statistics',
        'Seasonal summaries combine collection observations; not time-weighted and not phenology estimates'],
      'independent_pixel_checks':sample_checks,
      'pixel_validation_passed':bool(sample_checks) and all(s['passed'] for s in sample_checks) and any(s['valid_scalar_sample'] for s in sample_checks)}
    dump(out/'vegetation_metadata.json',report);return report

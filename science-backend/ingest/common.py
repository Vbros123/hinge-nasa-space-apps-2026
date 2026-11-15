import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pairs(items):
    d={}
    for k,v in items:
        if k in d: raise ValueError(f'Duplicate JSON key: {k}')
        d[k]=v
    return d

def read(path): return json.loads(Path(path).read_text(),object_pairs_hook=pairs)
def dump(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False,default=str));tmp.replace(p)

def client():
    s=requests.Session()
    retry=Retry(total=4,backoff_factor=1,status_forcelist=[429,500,502,503,504],
      allowed_methods=['GET','POST'],respect_retry_after_header=True)
    s.mount('https://',HTTPAdapter(max_retries=retry));return s

def retrieve(url,args,raw,post=False,offline=False):
    spec={'url':url,'method':'POST' if post else 'GET','arguments':args}
    key=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
    base=Path(raw)/key
    metadata=base.with_suffix('.meta.json');bodyfile=base.with_suffix('.response')
    if metadata.exists() and bodyfile.exists():
        meta=read(metadata)
        if sha(bodyfile)!=meta['response_sha256']: raise ValueError('Corrupt raw cache')
        content=bodyfile.read_text()
    else:
        if offline: raise RuntimeError('OFFLINE_CACHE_MISS '+key)
        r=client().request(spec['method'],url,timeout=(15,120),**({'json':args} if post else {'params':args}))
        base.parent.mkdir(parents=True,exist_ok=True)
        if not r.ok:
            dump(base.with_suffix('.error.json'),dict(spec,status=r.status_code,body=r.text,retrieved_at=now()))
        r.raise_for_status()
        content=r.text
        json.loads(content,object_pairs_hook=pairs)
        bodyfile.write_text(content)
        meta=dict(spec,retrieved_at=now(),response_sha256=sha(bodyfile),request_id=key)
        dump(metadata,meta)
    return json.loads(content,object_pairs_hook=pairs),meta

def table(df,out,name):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    df.to_parquet(out/(name+'.parquet'),index=False)
    dump(out/(name+'.json'),json.loads(df.to_json(orient='records')))

def aoi(path):
    from shapely.geometry import shape
    d=read(path)
    if d.get('type')=='FeatureCollection':
        if len(d['features'])!=1:raise ValueError('Exactly one AOI required')
        d=d['features'][0]
    g=shape(d['geometry']); pid=d.get('properties',{}).get('polygon_id')
    if not pid or not g.is_valid or g.is_empty or g.geom_type not in ['Polygon','MultiPolygon']:
        raise ValueError('Valid Polygon/MultiPolygon and properties.polygon_id required')
    x0,y0,x1,y1=g.bounds
    if not (-180<=x0<=x1<=180 and -90<=y0<=y1<=90):raise ValueError('WGS84 lon/lat required')
    return d,g,pid

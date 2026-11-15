from pathlib import Path
import math
import pandas as pd
from .common import retrieve,dump,table
URL='https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest'

def query(sql,out,offline=False):
    b,m=retrieve(URL,{'query':sql,'format':'JSON+COLUMNNAME'},Path(out)/'raw/ssurgo',post=True,offline=offline)
    if 'Table' not in b:raise ValueError('SDA Table missing: '+str(b))
    t=b['Table'];return [dict(zip(t[0],r)) for r in t[1:]] if t else [],m

def num(v):
    if v in (None,''):return None
    x=float(v)
    return x if math.isfinite(x) else None

def storage(horizons,depth,restriction=None):
    if depth<=0 or (restriction is not None and restriction<0):raise ValueError('Invalid depth')
    limit=min(depth,restriction) if restriction is not None else depth
    segments=[];notes=[];total=0.
    for h in horizons:
        a,b,w=[num(h.get(k)) for k in ['hzdept_r','hzdepb_r','awc_r']]
        if a is None or b is None or a>=b:notes.append('invalid_horizon_depth');continue
        a,b=max(0,a),min(limit,b)
        if b<=a:continue
        if w is None or not 0<=w<=1:notes.append('missing_or_invalid_awc');continue
        segments.append((a,b));total+=(b-a)*10*w
    cursor=0.
    for a,b in sorted(segments):
        if a<cursor-1e-6:notes.append('overlap')
        if a>cursor+1e-6:notes.append('gap')
        cursor=max(cursor,b)
    if cursor<limit-1e-6:notes.append('incomplete_profile')
    valid=not notes
    if restriction is None:notes.append('restriction_unknown')
    return {'estimated_storage_mm':total if valid else None,
      'known_horizon_storage_mm':None if 'overlap' in notes else total,
      'integration_bottom_cm':limit,'target_depth_cm':depth,'uncertainty_notes':sorted(set(notes))}

def ingest(feature,geom,out,depth=100,offline=False):
    from shapely import wkt
    from shapely.ops import transform,unary_union
    from pyproj import Transformer
    out=Path(out);w=geom.wkt.replace("'","''")
    sql=f"""~DeclareGeometry(@aoi)~
SELECT @aoi=geometry::STGeomFromText('{w}',4326);
~GetClippedMapunits(@aoi,polygon,geo,@clipped)~
SELECT id AS mukey,geom.STAsText() AS clipped_wkt FROM @clipped;"""
    clipped,spatial=query(sql,out,offline)
    if not clipped:raise RuntimeError('No SSURGO polygons returned')
    keys=sorted({str(r['mukey']) for r in clipped})
    if any(not k.isdigit() for k in keys):raise ValueError('Non-numeric mapunit ID')
    keylist=','.join("'"+k+"'" for k in keys)
    sql=f"""SELECT m.mukey,m.muname,c.cokey,c.compname,c.comppct_r,c.drainagecl,
h.chkey,h.hzdept_r,h.hzdepb_r,h.awc_l,h.awc_r,h.awc_h,
l.areasymbol,s.saverest,
(SELECT TOP 1 t.texdesc FROM chtexturegrp t WHERE t.chkey=h.chkey AND t.rvindicator='Yes') AS texture
FROM mapunit m JOIN legend l ON l.lkey=m.lkey
LEFT JOIN sacatalog s ON s.areasymbol=l.areasymbol
LEFT JOIN component c ON c.mukey=m.mukey
LEFT JOIN chorizon h ON h.cokey=c.cokey WHERE m.mukey IN ({keylist})
ORDER BY m.mukey,c.cokey,h.hzdept_r;"""
    rows,tabular=query(sql,out,offline)
    restrictions,rm=restrictions_verified(keylist,out,offline)
    tr=Transformer.from_crs(4326,6933,always_xy=True).transform
    area=transform(tr,geom).area;mapunits=[]
    for key in keys:
        pieces=[wkt.loads(r['clipped_wkt']) for r in clipped if str(r['mukey'])==key]
        g=unary_union(pieces).intersection(geom);a=transform(tr,g).area
        mapunits.append({'mapunit_id':key,'clipped_wkt':g.wkt,'area_m2':a,'aoi_fraction':a/area})
    groups={}
    for r in rows:
        if not r.get('cokey'):continue
        groups.setdefault(str(r['cokey']),[]).append(r)
    components=[];horizons=[]
    for cokey,hs in groups.items():
        r=hs[0];pct=num(r['comppct_r'])
        if pct is not None and not 0<=pct<=100:raise ValueError('Bad component percent')
        rs=[x for x in restrictions if str(x['cokey'])==cokey]
        depths=[num(x['resdept_r']) for x in rs if num(x['resdept_r']) is not None]
        restriction=min(depths) if depths else None
        c={'polygon_id':feature['properties']['polygon_id'],'mapunit_id':str(r['mukey']),
          'component_id':cokey,'component_name':r['compname'],'component_fraction':None if pct is None else pct/100,
          'drainage_class':r['drainagecl'],'restrictive_depth_cm':restriction,'restrictions':rs,
          'classification':'surveyed; storage is derived','source_metadata':{'areasymbol':r['areasymbol'],'saverest':r['saverest']}}
        c.update(storage(hs,depth,restriction));components.append(c)
        for h in hs:
            horizons.append({'polygon_id':c['polygon_id'],'mapunit_id':c['mapunit_id'],'component_id':cokey,
              'horizon_id':str(h['chkey']) if h['chkey'] else None,'horizon_top_cm':num(h['hzdept_r']),
              'horizon_bottom_cm':num(h['hzdepb_r']),'available_water_capacity':num(h['awc_r']),
              'awc_low':num(h['awc_l']),'awc_high':num(h['awc_h']),'soil_texture':h['texture']})
    table(pd.DataFrame(horizons),out,'soil_horizons')
    sums={k:sum(c['component_fraction'] or 0 for c in components if c['mapunit_id']==k) for k in keys}
    report={'source':'USDA NRCS SSURGO','url':URL,'polygon_id':feature['properties']['polygon_id'],
      'mapunits':mapunits,'components':components,'component_fraction_sums':sums,
      'mapped_aoi_fraction':sum(m['aoi_fraction'] for m in mapunits),'requests':[spatial,tabular,rm],
      'units':{'AWC':'cm3/cm3','horizon_depth':'cm','storage':'mm'},
      'assumptions':{'integration_target_cm':depth,'restriction_policy':'minimum recorded restriction regardless of kind; requires agronomic review'},
      'limitations':['Components are not spatially located within mapunits','No contemporaneous soil moisture measurement',
       'No missing component renormalization','No field-average storage asserted','Minimum restriction may not be crop-root limiting']}
    dump(out/'soils.json',report);return report

def validate_profile(out,reference):
    # Reference is a normalized CSV separately exported from USDA WSS/SSURGO, not from this pipeline.
    from .common import sha
    a=pd.read_parquet(Path(out)/'soil_horizons.parquet');b=pd.read_csv(reference,dtype={'component_id':str,'horizon_id':str})
    keys=['component_id','horizon_id'];cols=['horizon_top_cm','horizon_bottom_cm','available_water_capacity']
    if b.empty or not set(keys+cols).issubset(b):raise ValueError('Reference schema invalid')
    j=a.merge(b,on=keys,suffixes=('_pipeline','_reference'),validate='one_to_one')
    component_ids=set(b.component_id.astype(str))
    expected=a.loc[a.component_id.astype(str).isin(component_ids)]
    complete=len(component_ids)==1 and len(j)==len(b)==len(expected) and len(j)>0
    comparisons={}
    for c in cols:
        x=pd.to_numeric(j[c+'_pipeline'],errors='coerce');y=pd.to_numeric(j[c+'_reference'],errors='coerce')
        comparisons[c]=bool(x.notna().all() and y.notna().all() and ((x-y).abs()<=1e-6).all())
    report={'passed':complete and all(comparisons.values()),'matched_horizons':len(j),'reference_horizons':len(b),
      'checks':comparisons,'reference_sha256':sha(reference),'independence':'separate USDA export, same underlying survey; evidence required'}
    dump(Path(out)/'soil_profile_validation.json',report);return report

def restrictions_verified(keylist, out, offline=False):
    """Interpret an empty SDA restriction result only after a nonempty count result."""
    if not keylist or any(c not in "0123456789', " for c in keylist):
        raise ValueError('Invalid SQL mapunit key list')
    sql = ("SELECT r.cokey,r.reskind,r.reshard,r.resdept_r FROM corestrictions r "
           "JOIN component c ON c.cokey=r.cokey WHERE c.mukey IN (" + keylist + ")")
    original_meta = None
    original_error = None
    try:
        rows, original_meta = query(sql, out, offline)
    except ValueError as exc:
        if str(exc) != 'SDA Table missing: {}':
            raise
        rows = []
        original_error = str(exc)
    if rows:
        return rows, original_meta
    count_sql = (
        "SELECT COUNT_BIG(*) AS component_count, "
        "(SELECT COUNT_BIG(*) FROM corestrictions r JOIN component c2 "
        "ON c2.cokey=r.cokey WHERE c2.mukey IN (" + keylist + ")) AS restriction_count "
        "FROM component c WHERE c.mukey IN (" + keylist + ")"
    )
    counts, count_meta = query(count_sql, out, offline)
    if len(counts) != 1:
        raise ValueError('Restriction verification did not return exactly one count row')
    normalized = {str(k).lower(): v for k,v in counts[0].items()}
    from decimal import Decimal, InvalidOperation
    def exact_nonnegative_integer(name):
        try:
            value = Decimal(str(normalized[name]))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ValueError('Missing or invalid restriction count: ' + name) from exc
        if not value.is_finite() or value < 0 or value != value.to_integral_value():
            raise ValueError('Invalid restriction count: ' + name)
        return int(value)
    component_count = exact_nonnegative_integer('component_count')
    restriction_count = exact_nonnegative_integer('restriction_count')
    if component_count <= 0:
        raise ValueError('Cannot verify empty restrictions: no matching components')
    if restriction_count != 0:
        raise ValueError('Restrictions response empty but count is nonzero: ' + str(restriction_count))
    return [], {
        'interpretation': 'verified_zero_matching_corestrictions_rows',
        'component_count': component_count,
        'restriction_count': restriction_count,
        'original_result_metadata': original_meta,
        'original_error': original_error,
        'verification_request': count_meta,
        'scientific_limit': 'No recorded restrictions is not evidence of unrestricted rooting depth'
    }


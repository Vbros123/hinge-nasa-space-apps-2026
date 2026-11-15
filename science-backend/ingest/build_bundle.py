import argparse,traceback,sys,platform,subprocess,shutil
from pathlib import Path
from .common import aoi,dump,read,now,sha
from . import __version__

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--aoi',required=True);p.add_argument('--out',required=True)
    p.add_argument('--only',choices=['all','power','ssurgo','hls','validate'],default='all')
    p.add_argument('--start-year',type=int,default=1981);p.add_argument('--end-year',type=int,default=2025)
    p.add_argument('--hls-start',default='2025-01-01');p.add_argument('--hls-end',default='2025-12-31')
    p.add_argument('--soil-depth-cm',type=float,default=100)
    p.add_argument('--power-reference-csv');p.add_argument('--soil-reference-csv');p.add_argument('--evidence')
    p.add_argument('--offline',action='store_true');args=p.parse_args()
    if args.start_year>args.end_year:p.error('start year > end year')
    feature,geom,pid=aoi(args.aoi);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'field.geojson').exists() and read(out/'field.geojson')!=feature:
        raise ValueError('AOI changed: use fresh output directory and versioned polygon_id')
    dump(out/'field.geojson',feature)
    from . import power,ssurgo,hls
    from .validate import validate
    manifest_path=out/'manifest.json'
    manifest=read(manifest_path) if manifest_path.exists() else {'products':{}}
    manifest.update({'schema_version':'hinge.environment.v2','pipeline_version':__version__,'polygon_id':pid,
      'updated_at':now(),'command':sys.argv,'python':platform.python_version(),'platform':platform.platform(),
      'acceptance_status':'INCOMPLETE','aoi_sha256':sha(out/'field.geojson')})
    failures=[]
    jobs={'power':lambda:power.ingest(feature,geom,args.start_year,args.end_year,out,args.offline),
      'ssurgo':lambda:ssurgo.ingest(feature,geom,out,args.soil_depth_cm,args.offline),
      'hls':lambda:hls.ingest(feature,geom,args.hls_start,args.hls_end,out,args.offline)}
    for name,job in jobs.items():
        if args.only not in ('all',name):continue
        try:
            report=job();manifest['products'][name]={'status':'executed','completed_at':now()}
        except Exception as e:
            failures.append(name);manifest['products'][name]={'status':'failed','error':str(e),'traceback':traceback.format_exc()}
        dump(manifest_path,manifest)
    for label,action in [
      ('power_csv',lambda:power.compare_csv(out,args.power_reference_csv)),
      ('soil_reference',lambda:ssurgo.validate_profile(out,args.soil_reference_csv))]:
        enabled=args.power_reference_csv if label=='power_csv' else args.soil_reference_csv
        if enabled:
            try:action()
            except Exception as e:failures.append(label);manifest[label+'_error']=str(e)
    for reference,name in [(args.power_reference_csv,'power_reference.csv'),(args.soil_reference_csv,'usda_profile.csv')]:
        if reference:
            dest=out/'validation'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            if Path(reference).resolve()!=dest.resolve():shutil.copyfile(reference,dest)
    if args.evidence:
        dest=out/'validation_evidence.json'
        if Path(args.evidence).resolve()!=dest.resolve():shutil.copyfile(args.evidence,dest)
    acceptance=validate(out)
    manifest['acceptance_status']='AUTOMATED_GATES_PASSED_REVIEW_REQUIRED' if acceptance['passed'] and not failures else 'INCOMPLETE'
    manifest['validation']=acceptance
    freeze=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True)
    (out/'environment.freeze.txt').write_text(freeze.stdout)
    try:
        manifest['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True).strip()
    except Exception:manifest['git_commit']=None
    manifest['file_sha256']={str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f!=manifest_path}
    dump(manifest_path,manifest)
    print(manifest['acceptance_status'])
    if failures or not acceptance['passed']:raise SystemExit(2)

if __name__=='__main__':main()

"""HLS observations displayed separately from hypothetical modeled cover."""
import json, os

def vegetation_context(data_dir):
    with open(os.path.join(data_dir, 'vegetation.json')) as f:
        records = json.load(f)
    with open(os.path.join(data_dir, 'vegetation_seasonal.json')) as f:
        seasons = json.load(f)
    usable = [r for r in records if r['quality_flag'] == 'usable' and r.get('ndvi_median') is not None]
    return {'classification': 'observed HLS vegetation context; no rotation attribution',
            'observations': records, 'seasonal_summaries': seasons,
            'total_observations': len(records), 'usable_observations': len(usable),
            'limitations': ['NDVI is not percent living cover or yield', '2025 observations cannot validate historical or hypothetical rotation outcomes', 'cloud/invalid observations are missing, not zero']}

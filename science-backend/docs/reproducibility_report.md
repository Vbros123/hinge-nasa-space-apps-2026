# Reproducibility

Environment: Python 3.12, pandas, NumPy, PyYAML, pyarrow and pytest versions recorded in `output/real_environment/model_manifest.json` (pyarrow separately in the execution report). Exact config and environmental input SHA-256 values are recorded there; full archived source hash list is in the untouched environmental manifest. Run:

```bash
python -m pip install -r requirements.txt
python -m pytest -q -rs
python run_integrated.py --data data/real_environment --out output/real_environment
sha256sum output/real_environment/*.json > output/real_environment/repro_before.sha256
python run_integrated.py --data data/real_environment --out output/real_environment
sha256sum -c output/real_environment/repro_before.sha256
```

The repeated execution checks exact bytes for all eight JSON results. Source request retrieval timestamps are in the cached upstream manifest but model outputs have no execution timestamp. The source archive is preserved; model-only replay does not make network requests.

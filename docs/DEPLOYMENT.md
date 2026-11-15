# Reproduce and deploy HINGE

## Frontend

Run `npm ci`, `npm test`, `npm run lint`, and `npm run build`. Serve `dist/` on a static HTTPS host or run `npm run preview` locally. The app uses static JSON under `/science/v1/`. Map background tiles come from OpenStreetMap.

For Vercel, link this repository to a Vite project. Use `npm ci` as the install command, `npm run build` as the build command, and `dist` as the output directory. No environment variables are required. A configured Git connection needs access to the private repository. For target validation, open the app, confirm the default science mode and test a rotation comparison after switching its historical window and parameter set.

## Science reproducibility

Use the team’s `HINGE_PERSON2_PHASE3_INTEGRATED.zip` archive with engine, inputs, configurations, tests, and recorded outputs. Raw imagery, Parquet inputs and the Python engine are contained in that archive.

```bash
unzip HINGE_PERSON2_PHASE3_INTEGRATED.zip
cd hinge-integrated
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
sha256sum -c output/real_environment/repro_before.sha256
python run_integrated.py --data data/real_environment --out /tmp/hinge-rebuilt
```

Compare all eight rebuilt files to the archived files. Use the pinned dependency versions recorded in the model manifest for byte-by-byte comparisons. In the frontend repository, activate the same Python environment, then run:

```bash
python scripts/package_science.py /absolute/path/to/hinge-integrated
npm test
npm run build
```

The packaging command requires the recorded output hashes and verifies model input hashes. For a new scientific release, verify the regenerated results, record the corresponding hashes, and rerun frontend contract and interaction checks. The versioned asset layout is documented in the [integration audit](FINAL_INTEGRATION_AUDIT.md).

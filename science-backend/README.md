# HINGE scientific engine

This directory publishes the Python calculation and ingestion source used to produce HINGE's archived results. Start with the [scientific methodology](docs/scientific_methodology.md), [input contract](docs/data_contract_requirements.md), [validation report](docs/real_data_validation.md), and [source audit](docs/person1_data_audit.md).

## Set up the replay environment

From this directory, use Python 3.12.14 for exact comparison with the recorded manifest.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-replay.txt
python tools/make_mock_environment.py --out tests/fixtures/mock_environment
```

The generated mock fixture is for software tests. The source-only suite is runnable with `python -m pytest -q -rs --ignore=tests/test_real_environment.py`.

## Reproduce the released results

Obtain the original Person 2 Phase 3 archive, `HINGE_PERSON2_PHASE3_INTEGRATED.zip`, from the HINGE team. It contains the validated observations, cached upstream responses and reference checks. The team must grant access to that external artifact for an exact replay. Copy only its complete `hinge-integrated/data/real_environment/` directory into this directory's `data/` directory.

```bash
python -m pytest -q -rs
python run_integrated.py --data data/real_environment --out output/real_environment
sha256sum -c provenance/repro_before.sha256
cp provenance/repro_before.sha256 output/real_environment/
python ../scripts/package_science.py .
```

The last command rebuilds the browser assets after validating the recorded digests. The original environment manifest verifies 1,265 archived input files. The [model manifest](provenance/model_manifest.json) also records hashes of the primary model inputs and configurations. The published source and mock tests run independently of the archive. Full numerical and environmental replay requires the cached bundle.

## Acquire observations again

The [study polygon](data/field.geojson) and ingestion code document the acquisition inputs. Install `requirements_ingest.txt` and use `python -m ingest.build_bundle --help` for the source options. The archived scope is NASA POWER daily LST weather for 1981–2025, SSURGO component estimates at the 100 cm integration target, and NASA HLS 2.0 observations for 2025. The source audit documents the original validation references, and the [HLS notes](docs/hls_vegetation_integration.md) describe imagery access. New acquisitions may yield updated data and manifests. They cannot substitute for the exact archived package when comparing the published hashes.

> Phase 2 update: the suite now has 117 tests (1 skipped: Parquet needs pyarrow). The authoritative, regenerated validation record is `numerical_validation_phase2.md` (`python tools/validate_phase2.py`). The table below is the Phase 1 mapping and still applies.

# Model validation

Run: `python -m unittest discover -s tests -p "test_*.py"` (works under pytest as well). 48 tests, all passing at time of writing.

| Brief test | Where | What is checked |
|---|---|---|
| A mass conservation | test_water_balance, test_mass_balance | residual < 1e-9 mm every day, for storages of 30-400 mm and for every day of every rotation x block x parameter set in a replay |
| B storage bounds | same | 0 <= S <= Smax; ETa <= ETd; L in [0,1]; Kc > 0 (fallow never zero) |
| C zero rainfall | test_water_balance | storage never increases; no drainage |
| D hand calculation | test_hand_calculation | 3-day example with drainage, partial demand, and water-limited extraction (ETa 5, 3, 47; deficit 53) |
| E identical schedules | test_water_balance, test_scenarios | frames and full replay records identical on re-run |
| F same weather for all rotations | test_scenarios | one weather fingerprint per (parameter set, block) across all rotations |
| G missing data | test_missing_inputs, test_evapotranspiration | missing precip/temperature/wind, -999 fill, quality flags, incomplete or trailing partial year, invalid Kc, missing soil, invalid dates, mixed units: raise or exclude; nothing zero-filled |
| H feasibility rejection | test_constraints | planting before harvest, outside sourced window, cover-termination gap, cover planted before cash harvest, unsupported or unavailable termination method, missing equipment, no market access, excluded crop, unknown crop, sequence restriction |
| I sensitivity reproducibility | test_scenarios | identical records on repeat; no random numbers anywhere; CLI output is byte-identical across runs |
| J benchmark | test_evapotranspiration | FAO-56 Example 18 (Uccle, 6 July): Ra 41.09, ea 1.409, Rn 13.28, ET0 3.88 vs published 3.9 mm/day (our 3.8801 vs reference implementation 3.8801) |

Additional sanity tests: storage sensitivity ordering (more storage gives less deficit), termination-date sets leave the cover-free rotation unchanged,
cover rotation has more living-cover days and a lower rainfall-low-cover index than baseline.

Not validated: any agreement with field data, any NASA POWER value (no real data was available when this was written; the smoke run uses a synthetic fixture and its numbers carry no agronomic meaning).
Parquet reading was not exercised in the build sandbox (no pyarrow); CSV reading was.

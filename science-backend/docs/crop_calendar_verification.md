# Crop calendar verification (Phase 2, Task 1)

Method: sources were searched and read by the build agent on 2026-11-14 (web search and page fetch). **No human agronomist has reviewed them.** Evidence ids refer to `config/evidence_register.yaml`, which carries title, URL, location, publication date, geography, evidence type (direct / inferred / secondary) and uncertainty for each entry.

Status classes in `config/crops_nc.yaml`: `sourced` (prescriptive, violation is a hard constraint), `sourced_descriptive` (usual practice or rule of thumb; outside-range is flagged for verification, never rejected), `sourced_secondary`, `assumed`.

## Headline result
The most useful new source is the USDA NASS **North Carolina Agricultural Statistics, "Usual Planting and Harvesting Dates" (p. 58)**, which gives statewide Begin / Most-active / End dates for corn, soybeans and wheat (ev_nass_usual_dates). It replaced four assumed windows. It is statewide and descriptive, so it supports `feasible` only with explicit caveats (`STATEWIDE_USUAL_DATES`, `NO_HUMAN_REVIEW`). The same bulletin's county tables show Johnston County grows all three crops (2023 planted acres: corn 7,300; soybeans 49,000; wheat 9,600; ev_nass_johnston).

## Parameter-by-parameter record

| Parameter | Value in config | Status | Source (evidence id) and location | Geography | Direct / inferred | Uncertainty |
|---|---|---|---|---|---|---|
| Corn planting | Apr 1 - May 20; most active Apr 10-25 | sourced_descriptive | NASS NC Ag Statistics p.58 (ev_nass_usual_dates) | NC statewide | direct | usual practice, not an agronomic limit |
| Corn late-planting extension | to Jun 20 (warning, not rejection) | sourced_descriptive | NC State "Management for Late Planted Corn" (ev_ncsu_corn_late) | Piedmont NC (2001-02 trials) and VA | direct for "mid to late June"; Jun 20 is our reading | date not shown on page; old trials; no yield penalty quantified here |
| Corn harvest | Aug 20 - Oct 10; most active Sep 10 - Oct 10 | sourced_descriptive | NASS p.58 | NC statewide | direct | as above |
| Corn hybrid maturity | 108-114 d | sourced (late planting only) | NC State late-planted corn page | Piedmont | direct | applies to late-planted hybrids; used as hard minimum duration |
| Soybean planting (any) | May 1 - Jul 20; most active May 20 - Jun 30 | sourced_descriptive | NASS p.58 | NC statewide | direct | mixes full-season and double-crop |
| Soybean full-season | May 1 - Jun 10 | sourced_descriptive | press quote of NC State Soybean Production Guide (ev_soy_guide_press); NC State "Plant Full-Season Soybeans by Mid-May" (ev_ncsu_soy_fullseason) | NC | secondary + direct (direction only) | the Production Guide itself was not read; NC State says yield falls when planting slips past mid-May |
| Soybean double-crop | Jun 8 - Jul 5 | sourced_descriptive | NC State Soybean Extension 2022 (ev_ncsu_soy_double) | NC | direct ("2nd week of June to early July") | descriptive of practice |
| Soybean harvest | Oct 10 - Dec 20; most active Nov 10 - Dec 5 | sourced_descriptive | NASS p.58 | NC statewide | direct | maturity-group dependence not verified |
| Wheat planting | Sep 20 - Dec 20; most active Oct 15 - Nov 20 | sourced_descriptive | NASS p.58; Person Co. (Oct 15-20 start, ev_wheat_start, secondary); Sampson Co. (optimum late Oct to Thanksgiving, ev_wheat_sampson) | statewide; Piedmont; Coastal Plain county next to Johnston | direct + secondary | AG-850 start-date map for Johnston not retrieved |
| Wheat harvest | May 30 - Jul 25; most active Jun 10-30 | sourced_descriptive | NASS p.58 | NC statewide | direct | |
| Rye planting, Coastal Plain | possible Sep 30 - Dec 15; preferred to Nov 15 | sourced (hard) | NC State AG-439-58 Table 4 (ev_ncsu_cover_crops) | Coastal Plain | direct | |
| Rye planting, Piedmont | possible Sep 15 - Nov 15; preferred to Oct 15 | sourced (hard, used when site.region = piedmont) | same | Piedmont | direct | Johnston County region assignment unverified |
| Crimson clover planting | Coastal Plain Sep 1 - Oct 30 (preferred to Sep 30); Piedmont Aug 25 - Oct 1 | sourced | same, Table 1 | | direct | not used in the three templates |
| Cover termination | Mar 25 - Apr 30 | sourced_descriptive | same, "kill near April 1 in the east, mid to late April in the piedmont" | | **inferred** bounds | the bounds are our spread around a rule of thumb |
| Cover termination to cash planting gap | 7-14 d | sourced (hard) | same, "Cover Crop Mixtures" | | direct for corn | applied to soybean by analogy only |

## Early versus late planting: what the sources support
- Corn: usual planting ends May 20; NC State reports planting in mid to late June can still have a reasonable opportunity for profit (Piedmont trials). Penalty size not extracted. Hybrid and year-specific optimum guidance (NC State publishes a corn climate dashboard) was not retrieved.
- Soybean: NC State shows lower yield when full-season planting slips past mid-May; the usual (NASS) planting runs to Jul 20 because double-crop is included.
- Wheat: planting too early raises fall tiller, insect (Hessian fly) and spring-freeze risk (Person Co.); yield may fall after Thanksgiving (Sampson Co.).
- Cover crops: late seeding reduces biomass (crimson clover 0.4 t/ac on Nov 19 vs 1.5 t/ac on Oct 12 after soybean MG5; one site, AG-439-58 Table 3).

## Changes made and why
| Change | Reason |
|---|---|
| Full-season soybean harvest 10-05 to 10-15 in all templates | NASS usual soybean harvest begins Oct 10; Oct 5 would be flagged `OUTSIDE_USUAL_RANGE` |
| Wheat harvest 06-05 to 06-10; double-crop soybean planting 06-12 to 06-15 | NASS wheat harvest most-active starts Jun 10; slack of 5 days kept |
| Rye after soybean planted 10-25 (was 10-20) | follows the later soybean harvest with 10 days of slack |
| Corn window Apr 10 - Jun 15 (assumed) replaced by Apr 1 - May 20 usual + Jun 20 late extension | usual dates found; mid-June kept only as flagged late extension |
| Wheat Kc ini 0.4 to 0.7 | see crop_water_parameter_validation.md |

Phase 1 files are preserved in `config/phase1_frozen/`; `tests/test_phase1_regression.py` shows the Phase 1 numbers are still reproduced from them.

## Resulting feasibility statuses (default management, coastal_plain region)
| Rotation | Status | Evidence classes behind the operation dates | Caveats raised |
|---|---|---|---|
| rotation_a | feasible | 6 sourced_descriptive | STATEWIDE_USUAL_DATES, NO_HUMAN_REVIEW |
| rotation_b | feasible | 8 sourced_descriptive, 2 sourced (rye planting) | + REGION_UNVERIFIED |
| rotation_c | feasible | 8 sourced_descriptive | + CROP_FAMILY_REPEAT warning (corn then wheat, both Poaceae) |

I did **not** promote everything: any window still marked `assumed` returns `feasible_pending_verification` (tested). `feasible` here means calendar-feasible under statewide usual practice and NC State cover-crop tables. It does not mean agronomically optimal for Johnston County.

## Unresolved (not verified)
1. NC Small Grain Production Guide (AG-850) planting-date map and Johnston County start date. Only secondary references to it were read.
2. NC State Soybean Production Guide read directly (only a press quote and NC State blog posts).
3. Soybean maturity-group-dependent harvest dates, and which group fits a May 15 planting.
4. Corn: Johnston-specific optimum window and the size of late-planting yield loss.
5. Whether Johnston County is classed Coastal Plain or Piedmont in NC State's tables (model runs coastal_plain by default; `piedmont` is supported and tested).
6. Soybean harvest of Oct 15 sits before the most-active period (Nov 10 - Dec 5); flagged `OUTSIDE_MOST_ACTIVE` as a warning. Wheat duration 200-230 d and soybean duration 100-140 d remain assumed (only used as lower bounds).
7. Cover termination bounds (Mar 25 - Apr 30) are inferred.
8. Human review of every cited page.

# Agricultural sources (Phase 2 revision)

Full per-parameter evidence lives in `config/evidence_register.yaml` and is summarised with locations, dates and uncertainty in `crop_calendar_verification.md` (calendars) and `crop_water_parameter_validation.md` (Kc). Pages were read by the build agent; none has been confirmed by a human reviewer.

## Sources used
| Source | URL | Used for |
|---|---|---|
| USDA NASS, North Carolina Agricultural Statistics, "Usual Planting and Harvesting Dates" p.58 and county tables | https://www.nass.usda.gov/Statistics_by_State/North_Carolina/Publications/Annual_Statistical_Bulletin/AgStat/Section05.pdf | statewide usual corn, soybean, wheat planting and harvest windows; Johnston County acreage |
| NC State Extension, Winter Annual Cover Crops (AG-439-58), Tables 1, 3, 4 and text | https://content.ces.ncsu.edu/winter-annual-cover-crops | cover-crop planting windows by region, termination rule of thumb, 7-14 d gap, Hessian fly note |
| NC State Corn Extension, Management for Late Planted Corn | https://corn.ces.ncsu.edu/corn-production-information/management-for-late-planted-corn | late-planting extension, hybrid maturity |
| NC State Soybean Extension (2022, 2023) | https://soybeans.ces.ncsu.edu/2022/03/what-is-the-best-soybean-maturity-group-to-plant-behind-wheat ; https://soybeans.ces.ncsu.edu/2023/05/plant-full-season-soybeans-by-mid-may-to-prevent-yield-loss/ | double-crop timing; yield decline past mid-May |
| Southeast Farm Press (quotes NC State Soybean Production Guide) | https://www.farmprogress.com/management/early-planting-key-to-top-soybean-yields | full-season optimum May 1 - Jun 10 (secondary) |
| NC State Extension Person Co. and Sampson Co. wheat posts | https://person.ces.ncsu.edu/2023/09/should-i-plant-wheat-early/ ; https://sampson.ces.ncsu.edu/2025/10/wheat-planting-recommendations/ | wheat start dates and optimum period |
| FAO Irrigation and Drainage Paper 56 (Allen et al. 1998), Ch. 6 Tables 11-12; Ch. 2-4 equations | https://www.fao.org/4/x0490e/x0490e00.htm | Kc, stage lengths, Penman-Monteith |
| Secondary reproductions of FAO-56 Tables 11-12 (Clemson LGP, irrigationcalculators.com, ASABE chapter) | https://lgpress.clemson.edu/publication/irrigation-scheduling-methods-checkbook-vs-fao-56/ ; https://irrigationcalculators.com/reference/crop-coefficient-table | cross-check of Kc values and stage rows |
| CSLSevap R package test suite | https://rdrr.io/github/WDNR-Water-Use/CSLSevap/src/tests/testthat/test_FAO.R | independent expected values for FAO Examples 17 and 18 |

## Not retrieved
NC Small Grain Production Guide AG-850, the NC State Soybean Production Guide, NC State corn production guide planting-date tables, USDA NRCS publications, SARE "Managing Cover Crops Profitably" (listed in the brief; not used for any numeric value here).

## Prior art
APSIM (apsim.info), DSSAT (dssat.net), FAO-56, NC State Extension, SARE. Hinge does not claim to replace them.

# Integration test results

| Check | Result |
| --- | --- |
| Frontend unit, archive contract, and interaction tests | 21 passed, including 6 integration tests. |
| TypeScript and Vite production build | Passed. |
| Frontend lint | Passed. |
| Python scientific tests | 122 passed, 1 skipped. The skip covers the absence-of-PyArrow branch because PyArrow was installed. |
| Scientific archive regeneration | All 8 JSON files matched byte for byte. |
| Scientific asset mapping | 2,880 records validated across 40 windows. Source hashes, rotations, scenarios, parameter keys and sample values verified. |
| Local production browser check | Chromium passed the five science screens, parameter and window changes, mode switch, source value checks, mobile navigation and 503 retry. External map tile requests were intercepted for this run. |

Scientific assumptions and screening applicability are summarized in the [integration report](INTEGRATION_REPORT.md).

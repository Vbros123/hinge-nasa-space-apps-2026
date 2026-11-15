# HINGE final release verification

**Status — DEPLOYMENT_BLOCKED**

- Repository — [Vbros123/hinge-nasa-space-apps-2026](https://github.com/Vbros123/hinge-nasa-space-apps-2026)
- Starting main commit — `dfc7ceac986e3d75dec46a0420bb3969c396f7d6` with Phase 3 integration already merged.
- Tested release candidate — [`82412890e43901d5651e11bbd49bd894f4de1a7b`](https://github.com/Vbros123/hinge-nasa-space-apps-2026/commit/82412890e43901d5651e11bbd49bd894f4de1a7b). The following documentation commit adds the verification record.
- Release branch — `release/hinge-submission`.
- Public production URL — pending. The connected Vercel account has no project linked to the repository. Its project creation request returned HTTP 403. Production build logs and public-browser results require a deployment.

## Checks rerun on the final candidate

| Check | Executed result |
| --- | --- |
| GitHub baseline audit | 54 selected remote blobs matched the audited local version, including the catalog, all 40 window files, the lockfile, science application code, and documentation. |
| Clean frontend install | `npm ci` installed 209 packages. |
| Frontend and integration tests | 23 passed, including 8 archive-contract and science interaction tests. |
| Lint and production build | Both passed. |
| Scientific tests | 122 passed and 1 skipped. The PyArrow-absence check was skipped because PyArrow was present. The run emitted existing dependency deprecation warnings. |
| Deterministic scientific replay | All eight regenerated outputs matched the recorded SHA-256 digests. The cached source manifest and its 1,265 checksums passed validation. |
| Scientific frontend mapping | All 2,880 static records matched the source metric rows by window, parameter set, and rotation. Metric units matched. |
| Chromium against the local production build | All five screens, objective and parameter changes, 40 available windows, mode switching, refresh, keyboard focus, failed-fetch recovery and desktop/tablet/mobile layout passed. External map tiles were intercepted. |
| Public production verification | Pending Vercel access and deployment. |

## Representative scientific values

Reference parameter set, 1984–1986. Values below are carried through from the archived model. The browser rounds to two decimal places.

| Rotation | Water deficit (mm) | Low-cover rainfall exposure (mm) |
| --- | ---: | ---: |
| Baseline | 72.605162 | 1731.392222 |
| Rye cover | 73.252013 | 1131.272222 |
| Wheat followed by double-crop soybean | 174.977936 | 1350.901333 |

## Local production payload

Vite reports 239.66 kB for the entry JavaScript chunk (76.07 kB gzip; additional chart and map chunks load separately). The archived catalog occupies 520,107 uncompressed bytes. The 1984–1986 window occupies 101,380 uncompressed bytes. Chromium confirmed the initial farm view requests the catalog and defers the window until a comparison view uses it. These measurements describe the local build and do not estimate Vercel latency.

## Reproduce and deploy

The [Python source and replay guide](../science-backend/README.md) includes pinned dependency versions and instructions for generating the mock fixture and obtaining the original cached scientific inputs. Reviewers need access to the private GitHub repository and a separately supplied environmental archive for exact data replay. The raw environmental and satellite archive is kept outside Git.

Deploy the verified branch from an authorized Vercel project with access to this private GitHub repository. Configure Vite, `npm ci`, `npm run build`, and the `dist` output. Verify the production SHA, catalog, case assets, and public browser flows after deployment. See the [deployment guide](DEPLOYMENT.md) for the checklist.

The model supports screening at one provisional study area. Historical windows overlap, management assumptions require local agronomic review, and HLS context carries no rotation attribution. See the [scientific limitations](LIMITATIONS.md).

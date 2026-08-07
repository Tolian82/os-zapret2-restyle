# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_12` / `os-zapret2-restyle-0.3.3_12.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=13`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_12` is the latest owner-tested package. Live Scenario 1 on `_12` reproduced two independent blockers after the third-audit source/CI series: an immediate stage-50 family-runner failure and a deterministic stage-90 restoration failure on FreeBSD.

## Third audit corrective series

Status: **SOURCE/CI COMPLETE — LIVE SCENARIO 1 REOPENED BY `_12` EVIDENCE**

Authoritative audit: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

All seven third-audit findings `SL3-001` through `SL3-007` remain implemented in source and protected by their focused regressions plus the mandatory Strategy Lab corrective matrix. The `_12` live run exposed additional defects outside those findings; therefore source/CI closure did not satisfy the live gate.

## Patch evidence

- Patch 1 — PR #115, main `ed82ddff891ece514fac01895c197ef07d844557`.
- Patch 2 (`SL3-001` + `SL3-005`) — PR #116, main `dd95d77e4d75e6751315ff893798cc2ea66a9330`; CI `31151805919`; FreeBSD 15 artifact `8983642442`, package `_7`.
- Patch 3 (`SL3-002`) — PR #117, main `f0c43de7133f8ba337a5458de0803409949a0096`; CI `31152455413`; artifact `8983891990`, package `_8`.
- Patch 4 (`SL3-003` + `SL3-006`) — PR #118, main `15ed2b057ca94a1a780ecf9da9f304d0e6cd652c`; CI `31154664416`; artifact `8984745215`, package `_9`.
- Patch 5 (`SL3-004`) — PR #119, main `41ccadd47136375cb58a64e527f2fecff9f1630e`; CI `31155184080`; artifact `8984931432`, package `_10`.
- Patch 6 (`SL3-007`) — PR #120, main `00107d38f287462a2c0627a04629f6381774d05c`; CI `31156513189`; artifact `8985427611`, package `_11`.
- Patch 7 (integrated regression gate) — PR #121, exact latest head `dd2a484a4aa3711834b722aae0cc025d3fd4758e`, main `256ffa09452dabfb001665b729c1f4c3d3462688`; title check `31157848071` PASS; CI `31157848056` PASS; FreeBSD 15 artifact `8985927074` contains `os-zapret2-restyle-0.3.3_11.pkg` and passed manifest inspection.
- Patch 8 — PR #122, main `124cdef9fb68a9d749c052d1c806b637c8878bf9`; documentation-only source/CI closure and live handoff; no runtime behavior change.
- Final roll-up — package revision `_12`; no new product behavior; owner-installed testing prerelease `v0.3.3_12`.
- Live `_12` Scenario 1 — failed. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_12-scenario-01-freebsd-timeout-restoration.md`.
- Corrective `_13` — stage-90 FreeBSD timeout/reaper correction in progress. It is intentionally limited to exact restoration safety; stage 50 remains a separate next correction.

## Current verification boundary

Live OPNsense matrix: **FAILED ON `_12` — CORRECTIVE `_13` REQUIRED**.

The `_12` live watcher proved that the normal Zapret2 runtime became fully healthy during stage 90 and remained healthy for approximately 38 seconds, but `/usr/bin/timeout` without `-f` retained reaper ownership of daemon descendants. At the configured 45-second restoration timeout it terminated the already restored dvtws2/supervisor tree. The lifecycle code then repeated the same sequence once and ended `RESTORE_FAILED` with the normal service stopped.

The `_13` correction changes lifecycle service-action timeout invocation to FreeBSD foreground mode (`timeout -f`) and adds a deterministic regression that refuses lifecycle timeout calls without foreground mode.

Scenario 1 itself will still encounter the independent stage-50 blocker until that next logical defect is corrected. After `_13` passes CI and FreeBSD 15 package verification, owner-assisted testing must confirm that an error-path Strategy Lab run restores initial RUNNING to RUNNING instead of leaving Zapret2 stopped. Only then proceed to the separate stage-50 correction.

Authoritative live plan: `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## Current GitHub delivery authority

Evidence-first GitHub operations remain authoritative through:

- repository-root `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
- `docs/GITHUB_WORKFLOW.md`.

The connected GitHub plugin is the mandatory first repository interface. One logical scope uses one task branch and one Ready PR; same-scope repairs stay in that PR; the latest head must pass required checks; merge is squash with the expected head SHA; published `main` history is not rewritten.

## Release gate

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

Testing prerelease publication follows `docs/GITHUB_PUBLICATION.md`. The `_13` source correction itself does not imply stable release or pkg-repository promotion.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action: **complete `_13` stage-90 restoration correction, verify CI/FreeBSD 15 package, then retest the `_12` failure path on OPNsense to confirm exact RUNNING restoration before correcting stage 50.**

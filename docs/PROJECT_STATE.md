# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=12`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` remains the latest owner-tested package. `_6` corrected confirmed `_5` stage-50/stage-90 failures but was never owner-tested and was superseded by the third audit before its planned retest.

## Third audit corrective series

Status: **SOURCE/CI COMPLETE — FINAL `_12` PACKAGE ROLL-UP IN PROGRESS**

Authoritative audit: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

All seven third-audit findings `SL3-001` through `SL3-007` are implemented in source and protected by focused regressions plus the mandatory Strategy Lab corrective matrix. This statement is source/CI scope only and is not a live OPNsense PASS claim.

## Patch evidence

- Patch 1 — PR #115, main `ed82ddff891ece514fac01895c197ef07d844557`.
- Patch 2 (`SL3-001` + `SL3-005`) — PR #116, main `dd95d77e4d75e6751315ff893798cc2ea66a9330`; CI `31151805919`; FreeBSD 15 artifact `8983642442`, package `_7`.
- Patch 3 (`SL3-002`) — PR #117, main `f0c43de7133f8ba337a5458de0803409949a0096`; CI `31152455413`; artifact `8983891990`, package `_8`.
- Patch 4 (`SL3-003` + `SL3-006`) — PR #118, main `15ed2b057ca94a1a780ecf9da9f304d0e6cd652c`; CI `31154664416`; artifact `8984745215`, package `_9`.
- Patch 5 (`SL3-004`) — PR #119, main `41ccadd47136375cb58a64e527f2fecff9f1630e`; CI `31155184080`; artifact `8984931432`, package `_10`.
- Patch 6 (`SL3-007`) — PR #120, main `00107d38f287462a2c0627a04629f6381774d05c`; CI `31156513189`; artifact `8985427611`, package `_11`.
- Patch 7 (integrated regression gate) — PR #121, exact latest head `dd2a484a4aa3711834b722aae0cc025d3fd4758e`, main `256ffa09452dabfb001665b729c1f4c3d3462688`; title check `31157848071` PASS; CI `31157848056` PASS; FreeBSD 15 artifact `8985927074` contains `os-zapret2-restyle-0.3.3_11.pkg` and passed manifest inspection.
- Patch 8 — PR #122, main `124cdef9fb68a9d749c052d1c806b637c8878bf9`; documentation-only source/CI closure and live handoff; no runtime behavior change.
- Final roll-up — package revision `_12`; no new product behavior. Its purpose is to build one newest FreeBSD 15 package from the complete post-Patch-8 repository state before owner-assisted live verification.

Patch 7 remains the final integrated runtime-regression qualification. Revision `_12` does not alter that runtime logic; it advances package identity so the installation candidate is built after every approved Patch 1–8 repository change is present.

## Current verification boundary

Live OPNsense matrix: **READY — SCENARIO 1 PENDING OWNER**.

Designated candidate: `os-zapret2-restyle-0.3.3_12.pkg`, FreeBSD 15 amd64. The exact GitHub Actions artifact must come from the successful `_12` candidate build and is the package to install for Scenario 1.

Scenario 1 must be executed first on the owner's OPNsense appliance. Scenarios 2–18 remain blocked until scenario 1 passes. No source test, CI run, package build, mock, or integration fixture substitutes for owner-provided appliance evidence.

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

Testing prerelease publication of `_12` is not part of this roll-up and still requires separate exact owner authorization. This work does not publish a release, tag, GitHub Release asset, Pages repository, or pkg-repository package.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action after successful `_12` build: **owner-assisted live Scenario 1 on `os-zapret2-restyle-0.3.3_12.pkg`**.
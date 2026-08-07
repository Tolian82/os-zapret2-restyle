# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_13` / `os-zapret2-restyle-0.3.3_13.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=14`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_13` is the latest owner-tested package. Live Scenario 1 on `_13` proved that the `_13` stage-90 restoration correction works on OPNsense: after the run failed earlier, stage 90 restored the initially RUNNING Zapret2 service completely and left it healthy. The same run exposed the next independent blocker at stage 40: a FreeBSD `timeout(1)` wrapper falsely reports the mandatory DNS lookup as failed even though `drill` itself resolves the target immediately.

## Third audit corrective series

Status: **SOURCE/CI COMPLETE — LIVE SCENARIO 1 BLOCKED AT STAGE 40; `_14` CORRECTION IN PROGRESS**

Authoritative audit: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

All seven third-audit findings `SL3-001` through `SL3-007` remain implemented in source and protected by their focused regressions plus the mandatory Strategy Lab corrective matrix. Subsequent owner-assisted runs are now correcting additional FreeBSD live defects one logical defect at a time.

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
- Live `_12` Scenario 1 — stage 50 failed and stage 90 failed because FreeBSD timeout reaped the successfully restored daemon runtime. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_12-scenario-01-freebsd-timeout-restoration.md`.
- Corrective `_13` — PR #125, main `9a9879c6f88d77ab64c06647dd8d1e2437fc5f25`; published testing prerelease `v0.3.3_13`; FreeBSD stage-90 `strategy-lab-start` uses `timeout -f`.
- Live `_13` Scenario 1 — stage 90 PASS and normal Zapret2 remained healthy; stage 40 failed because `/usr/bin/timeout 2 /usr/bin/drill rutracker.org A` returned 124 with zero output while direct `drill` and `timeout -f` both returned `NOERROR`. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_13-scenario-01-stage40-freebsd-dns-timeout.md`.
- Corrective `_14` — FreeBSD stage-40 DNS request timeout correction in progress. It is intentionally limited to the live-proven timeout wrapper defect; `target_type:"A"` and stage 50 remain separate later corrections.

## Current verification boundary

Live OPNsense matrix: **FAILED AT STAGE 40 ON `_13` — CORRECTIVE `_14` REQUIRED**.

The `_13` live run verified the stage-90 safety requirement: initial RUNNING was restored to a complete healthy RUNNING state with no manual restart required.

The stage-40 failure is not a resolver outage. On the appliance, `/usr/bin/drill rutracker.org A` returned `rc=0`, `NOERROR`, and both A records in 96 ms. The exact Strategy Lab wrapper `/usr/bin/timeout 2 /usr/bin/drill rutracker.org A` returned `rc=124` after exactly two seconds with zero output. The identical call with `/usr/bin/timeout -f 2` returned `rc=0` and `NOERROR` in 30 ms.

The `_14` correction applies FreeBSD foreground timeout mode (`timeout -f`) only to `strategy_lab_dns_request()`; non-FreeBSD DNS requests retain the existing timeout semantics. A focused regression requires that exact platform split and is automatically executed by the mandatory corrective matrix.

The observed `baseline.json` value `target_type:"A"` is a separate confirmed shell-variable namespace defect and is not part of `_14`. The previously identified stage-50 family-runner defect also remains separate. Scenario 1 must first advance beyond the corrected stage 40 before those later defects are changed or requalified.

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

Testing prerelease publication follows `docs/GITHUB_PUBLICATION.md`. The `_14` source correction itself does not imply testing-prerelease publication, stable release, or pkg-repository promotion.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action: **complete `_14` source/CI/FreeBSD 15 package verification, then owner-assisted Scenario 1 must confirm that stage 40 no longer falsely fails on the FreeBSD DNS timeout wrapper while stage 90 remains PASS.**

# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_14` / `os-zapret2-restyle-0.3.3_14.pkg`
Latest owner-tested testing candidate: `v0.3.3_14` / `os-zapret2-restyle-0.3.3_14.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=15`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_14` is the latest owner-tested package. Live Scenario 1 on `_14`, job
`job.mCqg7Y`, proved that the `_14` FreeBSD DNS timeout correction works on OPNsense:
stage 40 passed with `DNS: OK`, a 416-byte `drill` result containing `NOERROR` and two A
records, and the blocked clean TLS 1.3 baseline correctly continued to candidate testing.
Stage 90 also passed and restored the initially RUNNING Zapret2 service completely.

The same live run exposed the next independent blocker at stage 50. The worker log
reported:

`strategy_lab_family_runner.sh: STRATEGY_LAB_TIMEOUT_BIN: parameter not set`

The family summary remained `total:7, completed:0`, proving that the runner aborted before
the first family candidate completed.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md`.

## Third audit corrective series

Status: **SOURCE/CI COMPLETE — LIVE SCENARIO 1 BLOCKED AT STAGE 50; `_15` CORRECTION IN PROGRESS**

Authoritative audit: `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

All seven third-audit findings `SL3-001` through `SL3-007` remain implemented in source
and protected by their focused regressions plus the mandatory Strategy Lab corrective
matrix. Subsequent owner-assisted runs are correcting additional FreeBSD live defects one
logical defect at a time.

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
- Corrective `_14` — PR #126, main `36e34414c869ff6e1062e37b91772aa8cdc05455`; published testing prerelease `v0.3.3_14`; FreeBSD DNS requests use foreground timeout mode.
- Live `_14` Scenario 1 — stage 40 PASS, stage 90 PASS, stage 50 FAIL before the first family because `STRATEGY_LAB_TIMEOUT_BIN` was unset in the family runner context. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md`.
- Corrective `_15` — family module owns the timeout executable default and a focused regression invokes the production family runner under `set -u` with no caller-provided timeout variable.

## Current verification boundary

Live OPNsense matrix: **FAILED AT STAGE 50 ON `_14` — CORRECTIVE `_15` REQUIRED**.

The `_14` live run verified two safety/flow sub-gates:

- stage 40 now advances correctly on FreeBSD with `DNS: OK` and a blocked clean TLS 1.3 baseline;
- stage 90 restores the initial RUNNING Zapret2 service completely and leaves it healthy.

The current stage-50 root cause is deterministic. `strategy_lab_family_runner.sh` enables
`set -eu` and sources `common.sh`, `result.sh`, and `family.sh`. In `_14`, `family.sh`
uses `${STRATEGY_LAB_TIMEOUT_BIN}` without defining it, so the runner aborts before the
first family candidate. `_15` limits the product change to ownership of that default in
the family module.

Authoritative live plan: `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## Confirmed defect backlog

The following defects are confirmed and must remain documented until corrected and live
or source-qualified as applicable. They are intentionally outside the `_15` stage-50
scope unless stated otherwise.

1. **Stage-50 family timeout variable ownership — correcting in `_15`.** The family runner aborts under `set -u` because `STRATEGY_LAB_TIMEOUT_BIN` is not owned by a sourced module.
2. **Baseline target-type corruption — pending.** `baseline.json` records `target_type:"A"` for a domain because DNS helpers reuse the shell-global `_strategy_lab_type` variable.
3. **Immediate stale GUI error after Run — pending.** A newly created job id can be displayed together with the previous terminal job's visible `ERROR` state before fresh polling renders the new state.
4. **GUI progress stuck at 0% while backend advances — pending.** On job `job.mCqg7Y`, the UI stayed at `0%` until completion while authoritative `status.json` advanced through 18%, 27%, 36%, 91%, and 100%.
5. **DNS answer parser accepts question lines — pending.** The current raw-output grep can match `IN A`/`IN AAAA` in `QUESTION SECTION`; it does not prove a real answer record.
6. **DNS failure diagnostics flatten distinct failures — pending.** Endpoint DNS failures are collapsed to generic return/exit code 1, losing timeout versus command failure versus parser rejection.
7. **Terminal-result reload/state presentation — pending.** Scenario 15 requires a completed/error job not to be resurrected as the active state of a newly opened Diagnostics page; the current initial status path still reads retained latest-job state and is part of the GUI state correction scope.

Live/source evidence for items 2–6 is preserved in
`docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md`.

## Current GitHub delivery authority

Evidence-first GitHub operations remain authoritative through:

- repository-root `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-07-installable-patch-shorthand.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
- `docs/GITHUB_WORKFLOW.md`.

The connected GitHub plugin is the mandatory first repository interface. One logical
scope uses one task branch and one Ready PR; same-scope repairs stay in that PR; the
latest head must pass required checks; merge is squash with the expected head SHA;
published `main` history is not rewritten.

## Release gate

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

The owner's current installable-package instruction authorizes publication of the next
deterministically derived testing prerelease after the `_15` ordinary PR/CI/squash cycle.
It does not authorize stable release or pkg-repository promotion.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action: **complete `_15` source/CI/FreeBSD 15 package verification, squash-merge it, publish testing prerelease `v0.3.3_15`, then owner-assisted Scenario 1 must confirm that stage 50 actually enters family execution while stage 40 and stage 90 remain PASS.**

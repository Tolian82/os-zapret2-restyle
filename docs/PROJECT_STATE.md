# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_16` / `os-zapret2-restyle-0.3.3_16.pkg`
Latest owner-tested testing candidate: `v0.3.3_16` / `os-zapret2-restyle-0.3.3_16.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=17`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_16` is the latest owner-tested package. Live Scenario 1 on `_16`, job
`job.VmWk32`, passed stages 00–40, failed at stage 50 with
`Temporary candidate runtime failed internally.`, skipped stages 60–85, then passed stage
90 and completely restored the initially RUNNING Zapret2 service.

Unlike earlier stage-50 failures, `_16` created the full temporary candidate runtime. The
candidate resolved `rutracker.org`, prepared rule 19100 and divert port 9989, started
dvtws2, loaded the hostlist, bound the divert socket, and dropped to UID/GID 65534. dvtws2
then exited on its post-drop file-access check:

```text
Running as UID=65534 GID=65534
file_open_test: Permission denied
cannot access hostlist file '/var/run/zapret2-restyle/strategy-lab/jobs/job.VmWk32/candidate-runtime/hostlist.txt'
```

The hostlist itself is mode 0644. The live/source root cause is the private random job
directory created with `mktemp -d`: after dvtws2 switches to `nobody`, the nested hostlist
cannot be reopened unless the parent job directory grants search permission.

The same `_16` run reconfirmed the separate GUI defects: a new job can immediately display
stale `ERROR`, active progress remains visually at 0%, and the UI jumps to 100% only at
terminal output. It also reconfirmed baseline `target_type:"A"` corruption.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md`.

## Third audit corrective series

Status: **SOURCE/CI COMPLETE — LIVE SCENARIO 1 BLOCKED AT STAGE 50; `_17` CORRECTION IN PROGRESS**

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
- Patch 7 (integrated regression gate) — PR #121, main `256ffa09452dabfb001665b729c1f4c3d3462688`; CI `31157848056` PASS; FreeBSD 15 artifact `8985927074`.
- Patch 8 — PR #122, main `124cdef9fb68a9d749c052d1c806b637c8878bf9`; documentation-only source/CI closure and live handoff.
- Final roll-up — package revision `_12`; owner-installed testing prerelease `v0.3.3_12`.
- Live `_12` — stage 50 failed and stage 90 failed because FreeBSD timeout reaped the successfully restored daemon runtime.
- Corrective `_13` — PR #125, main `9a9879c6f88d77ab64c06647dd8d1e2437fc5f25`; stage-90 FreeBSD `timeout -f`; owner live stage 90 PASS.
- Corrective `_14` — PR #126, main `36e34414c869ff6e1062e37b91772aa8cdc05455`; FreeBSD DNS foreground timeout; owner live stage 40 PASS and stage 90 PASS.
- Corrective `_15` — PR #127, main `6807bd7068f960832bf0ee42005c58cdf9d355ff`; family module owns its timeout executable default.
- Live `_15` — stage 50 still failed; source review found synchronous resident FreeBSD `daemon(8)` supervision blocked candidate readiness.
- Corrective `_16` — PR #128, main `88d33360be7b9fda8ddd8a8e903296cd775aae41`; published `v0.3.3_16`; temporary candidate daemon supervision detached and resident-supervisor regression added.
- Live `_16` — stage 40 PASS, stage 90 PASS, stage 50 FAIL after dvtws2 successfully starts/binds/drops privileges but cannot reopen its nested hostlist through the private job directory. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md`.
- Corrective `_17` — temporary search-only job-directory access is granted only while a hostlist-backed candidate runs and private 0700 mode is restored on every candidate cleanup; regression models post-drop access and cleanup privacy.

## Current verification boundary

Live OPNsense matrix: **FAILED AT STAGE 50 ON `_16` — CORRECTIVE `_17` REQUIRED**.

The `_16` live run verifies these sub-gates:

- stage 40 advances correctly on FreeBSD with `DNS: OK` and a blocked clean TLS 1.3 baseline;
- `_16` candidate startup reaches real dvtws2 execution, divert binding, and privilege drop;
- stage 90 restores the initial RUNNING Zapret2 service completely and leaves it healthy;
- temporary Strategy Lab firewall/runtime residue is removed at terminal completion.

The current stage-50 blocker is deterministic: dvtws2 is intentionally started with
`--user=nobody`; after dropping privileges it reopens the hostlist, but the hostlist is
nested below a random `mktemp -d` job directory that is private. `_17` keeps the job
private by default, grants only search traversal during hostlist-backed candidate lifetime,
and restores private mode during cleanup.

Authoritative live plan: `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## Confirmed defect backlog

The following defects are confirmed and must remain documented until corrected and live
or source-qualified as applicable. They are intentionally outside the `_17` stage-50
scope unless stated otherwise.

1. **Stage-50 post-drop hostlist access — correcting in `_17`.** dvtws2 loads the hostlist as root but, after `--user=nobody`, cannot reopen it because the random parent job directory does not grant search permission.
2. **Baseline target-type corruption — pending.** `baseline.json` records `target_type:"A"` for a domain because DNS helpers reuse the shell-global `_strategy_lab_type` variable.
3. **Immediate stale GUI error after Run — pending.** A newly created job id can be displayed together with the previous terminal job's visible `ERROR` state before fresh polling renders the new state. Reconfirmed on `_16` job `job.VmWk32`.
4. **GUI progress stuck at 0% while backend advances — pending.** The UI remains at 0% during active work and jumps to 100% only at terminal completion; backend evidence already proves stage progress itself advances normally.
5. **DNS answer parser accepts question lines — pending.** The raw-output match can accept `IN A`/`IN AAAA` from `QUESTION SECTION`; it does not prove an answer record.
6. **DNS failure diagnostics flatten distinct failures — pending.** Endpoint DNS failures collapse timeout, command failure, and parser rejection to generic code 1.
7. **Terminal-result reload/state presentation — pending.** A retained terminal job can be resurrected as active-looking state when Diagnostics is reopened.
8. **Candidate fatal-log classifier misses hostlist-access failure — pending.** `_16` persisted `log_clean:true` even though dvtws2 logged `file_open_test: Permission denied` and `cannot access hostlist file`.

Live/source evidence for these items is preserved in the `_14`, `_15`, and `_16` Scenario 1
evidence records under `docs/verification/evidence/`.

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

The owner's installable-package instruction authorizes publication of the next
deterministically derived testing prerelease after the `_17` ordinary PR/CI/squash cycle.
It does not authorize stable release or pkg-repository promotion.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action: **complete `_17` source/CI/FreeBSD 15 package verification, squash-merge it, publish testing prerelease `v0.3.3_17`, then owner-assisted Scenario 1 must confirm that stage 50 survives post-drop hostlist access and enters real family execution while stages 40 and 90 remain PASS.**

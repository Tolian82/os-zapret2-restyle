# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current source line: `VERSION=0.3.3`
Current corrective package revision: `PLUGIN_REVISION=7`
Target ABI: **FreeBSD:15:amd64 only**

## Historical live boundary

`v0.3.3_5` remains the latest owner-tested package. Its Scenario 1 attempt proved the prior PID/evidence correction but failed later at stage 50 and stage 90. Revision `_6` corrected those confirmed defects and passed source/CI/package verification, but `_6` was neither published nor owner-tested before the third audit reopened the corrective series.

Historical evidence remains under `docs/verification/evidence/` and the `_6` reconciliation ledger remains `docs/devlog/2026-08-07-v0.3.3_6-repository-reconciliation.md`.

## Third audit corrective series

Status: **IN PROGRESS**

Authoritative plan:

`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`

Stable findings:

- `SL3-001` — ordinary stale-worker recovery can falsely report semantic restoration;
- `SL3-002` — circular stale-worker recovery lacks lifecycle ownership;
- `SL3-003` — load-order override breaks Extended circular eligibility;
- `SL3-004` — `worker_skip_unfinished()` bypasses serialized state mutation;
- `SL3-005` — synchronous recovery caller timeouts are shorter than legitimate restoration;
- `SL3-006` — obsolete hook/load-order surfaces remain after declared cleanup;
- `SL3-007` — `cancel_requested` presentation is not completely localized.

## Patch progress

### Patch 1 — documentation and corrective plan

Status: **MERGED AND VERIFIED**

Merged as `ed82ddff891ece514fac01895c197ef07d844557` after PR #115 latest-head CI and FreeBSD 15 package validation passed. Patch 1 changed no package metadata.

### Patch 2 — ordinary stale recovery and timeout chain

Status: **SOURCE IMPLEMENTED — PR/CI VERIFICATION PENDING**

Package revision: `_7`.

Implemented scope for `SL3-001` + `SL3-005`:

- ordinary stale recovery no longer executes public `status/start/stop` shortcuts from the launcher;
- `zapret_service.sh strategy-lab-recover` now runs a dedicated recovery worker under the Strategy Lab lifecycle lock and owner environment;
- the recovery worker loads the existing lifecycle snapshot and reuses `strategy_lab_restore_initial_service_state()` and semantic evidence verification;
- launcher accepts recovery only when persisted evidence proves `verified=true`, `strategy_unchanged=true`, `temporary_runtime_clean=true`, and exact initial/final service-state equality;
- inconsistent or failed recovery is forced to `RESTORE_FAILED` and `.restoration.verified=false`;
- ordinary Strategy Lab configd control requests use a 180-second envelope, MVC uses 190 seconds, and browser AJAX uses 200 seconds, preserving `inner < outer` ordering around the bounded restoration transaction;
- focused stale-worker and ownership/timeout regressions cover the new contract.

Implementation log:

`docs/devlog/2026-08-07-v0.3.3_7-stale-recovery.md`

## Remaining approved sequence

3. **Patch 3 — circular stale recovery lifecycle ownership.** Close `SL3-002`.
4. **Patch 4 — remove load-order overrides and obsolete hooks.** Close `SL3-003` + `SL3-006`.
5. **Patch 5 — serialize worker state transitions.** Close `SL3-004`.
6. **Patch 6 — complete RU/EN progress localization.** Close `SL3-007`.
7. **Patch 7 — integrated third-audit regression gate.** Exercise corrected paths together and require the complete corrective matrix, repository CI, and FreeBSD 15 package build.
8. **Patch 8 — source/CI closure and live-test handoff.** Record exact evidence and designate the resulting FreeBSD 15 package for owner-assisted live verification.

Each packaged behavior patch keeps `VERSION=0.3.3`, increments `PLUGIN_REVISION` once, uses one task branch and Ready PR, passes focused validation plus required CI/package gates, and squash-merges to `main` with the expected head SHA. Documentation/CI-only patches do not increment package metadata.

## Current verification boundary

Live OPNsense matrix: **PAUSED PENDING THIRD-AUDIT SOURCE/CI COMPLETION**.

No `_6` live retest is required. Scenario 1 resumes only after Patch 8 designates the new corrective candidate; scenarios 2–18 remain blocked until Scenario 1 passes.

The authoritative live plan remains:

`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`

No source/CI result substitutes for owner-provided live OPNsense evidence.

## Release gate

Stable release preparation and pkg-repository promotion: **BLOCKED ON THIRD-AUDIT CORRECTIVE SERIES AND LIVE MATRIX**.

Testing prerelease publication for a later live candidate requires separate exact owner authorization.

Current product authority:

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Next action after Patch 2 merge/verification: **Patch 3 — circular stale recovery lifecycle ownership**.

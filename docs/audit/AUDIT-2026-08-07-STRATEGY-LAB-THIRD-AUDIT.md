# Strategy Lab third audit — 2026-08-07

Audited baseline: `main` at `b5b98679838c1a73c074fc132d675440d9294123` (`VERSION=0.3.3`, `PLUGIN_REVISION=6`).

Status: **SOURCE/CI CORRECTIVE SERIES COMPLETE — LIVE VERIFICATION PENDING**

This audit reopened Strategy Lab source/CI closure after a third source review of the rewritten blockcheck/Strategy Lab implementation. Seven stable findings (`SL3-001` through `SL3-007`) were registered. The approved Patch 1–8 sequence has now completed its source/CI scope. No finding below is marked live-verified: owner-assisted OPNsense verification remains a separate mandatory gate.

## Final source/CI qualification

The final integration-gate source state is Patch 7:

- PR #121;
- exact latest PR head: `dd2a484a4aa3711834b722aae0cc025d3fd4758e`;
- title check: `31157848071` — PASS;
- mandatory repository CI: `31157848056` — PASS;
- mandatory Strategy Lab corrective matrix inside that run — PASS;
- FreeBSD 15 package build and manifest inspection — PASS;
- GitHub Actions artifact: `8985927074`;
- package: `os-zapret2-restyle-0.3.3_11.pkg`;
- squash-merged `main`: `256ffa09452dabfb001665b729c1f4c3d3462688`.

Patch 8 changes documentation and live-handoff state only. It does not change runtime behavior or package metadata. Therefore the Patch 7 `_11` artifact above is the package designated for the next owner-assisted live Scenario 1.

## Stable findings and closure evidence

### SL3-001 — Ordinary stale-worker recovery can falsely report semantic restoration

Original classification: `broken / requires live test`.

Original problem: ordinary stale recovery could trust public `status/start/stop` exit codes and persist `.restoration.verified=true` without proving semantic equality of runtime arguments, effective configuration, and normal firewall state.

Implemented in Patch 2:

- stale recovery delegates to a lifecycle-owned semantic recovery transaction;
- verified recovery requires semantic equality, `strategy_unchanged=true`, and `temporary_runtime_clean=true`;
- contradictory or unavailable proof is normalized to `RESTORE_FAILED`;
- initial RUNNING and STOPPED stale states are covered.

Automated evidence:

- `scripts/test-strategy-lab-stale-worker-recovery.sh`;
- `scripts/test-strategy-lab-stale-recovery-contract.sh`;
- `scripts/test-strategy-lab-semantic-restoration.sh` through the established e2e delegation;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**.

### SL3-002 — Circular stale-worker recovery lacks lifecycle ownership

Original classification: `broken / requires live test`.

Original problem: circular stale recovery called protected normal-service restoration outside a valid lifecycle-owned Strategy Lab transaction; the old focused test mocked away the protected restore path.

Implemented in Patch 3:

- circular stale-owner detection delegates restoration to the lifecycle-owned `strategy-lab-recover` transaction;
- the recovery worker binds private circular-session state and uses the real semantic restoration path;
- inconsistent proof becomes `restore_failed/RESTORE_FAILED` and retry remains blocked;
- focused coverage no longer replaces protected restoration inside `circular_owner.sh` with a success-only mock.

Automated evidence:

- `scripts/test-strategy-lab-circular-owner.sh`;
- `scripts/test-strategy-lab-circular-recovery-contract.sh`;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**, with special attention in Scenario 12.

### SL3-003 — Load-order override breaks Extended circular eligibility

Original classification: `broken / duplicate`.

Original problem: `worker_result.sh` used the TLS 1.3 `circular_count/circular_items` subset, but a later definition from `worker_state_serialization.sh` used general `.count/.items`, so source order could select incorrect Extended circular eligibility.

Implemented in Patch 4:

- `worker_state_serialization.sh` was removed after its useful serialized persistence responsibilities were moved to canonical module owners;
- `worker_result.sh` is the single circular-eligibility owner;
- `profile.sh` is the single unified-shortlist owner;
- circular eligibility is based only on the TLS 1.3 circular subset;
- a namespace gate rejects duplicate function definitions among modules loaded together by the main worker.

Automated evidence:

- `scripts/test-strategy-lab-unified-shortlist.sh` proves an Extended general shortlist of five protocol entries with a three-entry TLS 1.3 circular subset;
- `scripts/test-strategy-lab-module-namespace.sh`;
- `scripts/test-strategy-lab-obsolete-surfaces.sh`;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**.

### SL3-004 — `worker_skip_unfinished()` bypasses state serialization

Original classification: `broken / concurrency risk`.

Original problem: cancel/API state writes used `strategy_lab_state_transform()` while `worker_skip_unfinished()` independently replaced `status.json`, allowing cancellation evidence, timestamps, or revision ordering to be overwritten.

Implemented in Patch 5:

- unfinished-stage skipping uses the canonical state transform and per-job lock;
- cancel, skip, and finalization writes are revisioned;
- original `cancel_requested_at` survives repeated/concurrent cancellation and finalization;
- terminal state remains irreversible.

Automated evidence:

- `scripts/test-strategy-lab-state-race.sh` performs concurrent cancel/skip writes and checks revisions, stage 90/99 preservation, cancellation timestamp, and terminal irreversibility;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**, especially Scenario 8.

### SL3-005 — Recovery caller timeout chain is shorter than legitimate restoration

Original classification: `broken / timeout contract`.

Original problem: a valid bounded semantic recovery could outlive the earlier 10-second configd/MVC and 15-second browser caller budgets.

Implemented with SL3-001 in Patch 2:

- synchronous Strategy Lab recovery/control actions use a 180-second configd envelope;
- MVC waits 190 seconds;
- browser AJAX waits 200 seconds;
- native lifecycle restoration remains bounded inside the outer callers rather than extending asynchronous search duration.

Automated evidence:

- `scripts/test-strategy-lab-stale-recovery-contract.sh`;
- `scripts/test-strategy-lab-circular-recovery-contract.sh` for the equivalent circular envelope;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**.

### SL3-006 — Obsolete hook/load-order surfaces remain after declared cleanup

Original classification: `duplicate / unused`.

Original problem: transitional skip hooks and repeated function definitions remained in jointly loaded modules after documentation claimed those surfaces were removed.

Implemented with SL3-003 in Patch 4:

- obsolete `strategy_lab_skip_unfinished()` and `strategy_lab_skip_remaining()` control-flow hooks were removed from transitional modules;
- the old TLS-only shortlist owner in `stability.sh` was removed;
- source-order behavior selection is prohibited by active architecture documentation and the module namespace regression.

Automated evidence:

- `scripts/test-strategy-lab-obsolete-surfaces.sh`;
- `scripts/test-strategy-lab-module-namespace.sh`;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER** where applicable through integrated behavior.

### SL3-007 — `cancel_requested` is not completely localized in Diagnostics

Original classification: `broken / presentation`.

Original problem: backend state `cancel_requested` had no `CANCEL_REQUESTED` entry in the Diagnostics status dictionary, allowing raw technical vocabulary in the Russian UI.

Implemented in Patch 6:

- RU: `CANCEL_REQUESTED` → `ОСТАНОВКА ЗАПРОШЕНА`;
- EN: `CANCEL_REQUESTED` → `CANCELLATION REQUESTED`;
- circular `stop_requested` remains a separate machine/presentation contract;
- the regression creates a real backend cancellation state, derives its presentation key, and requires both mappings.

Automated evidence:

- `scripts/test-strategy-lab-progress-localization.sh`;
- mandatory corrective matrix in Patch 7 CI `31157848056`.

Source/CI result: **IMPLEMENTED AND REGRESSION-COVERED**.
Live result: **PENDING OWNER**, especially Scenario 16.

## Corrective patch sequence — completed source/CI record

### Patch 1 — Third-audit documentation and corrective plan

Status: **COMPLETE**. PR #115, main `ed82ddff891ece514fac01895c197ef07d844557`.

### Patch 2 — Ordinary stale recovery and timeout chain

Status: **COMPLETE**. SL3-001 + SL3-005. PR #116, main `dd95d77e4d75e6751315ff893798cc2ea66a9330`; CI `31151805919`; FreeBSD 15 artifact `8983642442`, package `_7`.

### Patch 3 — Circular stale recovery lifecycle ownership

Status: **COMPLETE**. SL3-002. PR #117, main `f0c43de7133f8ba337a5458de0803409949a0096`; CI `31152455413`; artifact `8983891990`, package `_8`.

### Patch 4 — Remove load-order overrides and obsolete hooks

Status: **COMPLETE**. SL3-003 + SL3-006. PR #118, main `15ed2b057ca94a1a780ecf9da9f304d0e6cd652c`; CI `31154664416`; artifact `8984745215`, package `_9`.

### Patch 5 — Serialize worker state transitions

Status: **COMPLETE**. SL3-004. PR #119, main `41ccadd47136375cb58a64e527f2fecff9f1630e`; CI `31155184080`; artifact `8984931432`, package `_10`.

### Patch 6 — Complete RU/EN progress localization

Status: **COMPLETE**. SL3-007. PR #120, main `00107d38f287462a2c0627a04629f6381774d05c`; CI `31156513189`; artifact `8985427611`, package `_11`.

### Patch 7 — Integrated third-audit regression gate

Status: **COMPLETE**. No product behavior or package revision change. PR #121, exact latest head `dd2a484a4aa3711834b722aae0cc025d3fd4758e`; title `31157848071` PASS; CI `31157848056` PASS; FreeBSD 15 artifact `8985927074`, package `_11`; main `256ffa09452dabfb001665b729c1f4c3d3462688`.

The integration contract binds ordinary/circular stale recovery, semantic mismatch, Extended mixed shortlist/TLS13 circular subset, cancel race, long recovery envelope, saved Traffic Strategy immutability, and residue cleanup to the single mandatory matrix without duplicate orchestration.

### Patch 8 — Source/CI closure and live-test handoff

Status: **DOCUMENTATION HANDOFF**. No product behavior and no package revision change. It records the exact Patch 7 evidence above and designates `os-zapret2-restyle-0.3.3_11.pkg` / artifact `8985927074` for owner-assisted live Scenario 1. It makes no live PASS claim and publishes no release.

## Live gate after Patch 8

The owner-assisted OPNsense matrix may now resume. Scenario 1 is first and is **PENDING OWNER — RETEST REQUIRED** on `_11`. Scenarios 2–18 remain blocked until Scenario 1 passes.

Special attention remains required for cancellation, timeout, initial RUNNING/STOPPED restoration, circular start/stop, circular stale-worker recovery, Settings lifecycle coordination, persisted reload, retention, localization, and residue cleanup.

A live failure opens a new finding and corrective patch; it does not retroactively convert earlier failed evidence to PASS and does not authorize skipping dependent scenarios.

## Current release boundary

- Third-audit source/CI corrective series: **COMPLETE**.
- Owner-assisted live matrix: **PENDING**.
- Stable release: **BLOCKED ON LIVE MATRIX**.
- pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.
- Testing prerelease publication: **NOT AUTHORIZED BY THIS HANDOFF; REQUIRES SEPARATE EXACT OWNER AUTHORIZATION**.
- Next action: **owner-assisted Scenario 1 on `os-zapret2-restyle-0.3.3_11.pkg`**.

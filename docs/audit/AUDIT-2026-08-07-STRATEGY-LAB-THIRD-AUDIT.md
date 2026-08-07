# Strategy Lab third audit — 2026-08-07

Audited baseline: `main` at `b5b98679838c1a73c074fc132d675440d9294123` (`VERSION=0.3.3`, `PLUGIN_REVISION=6`).

Status: **CORRECTIVE SERIES OPEN**

This audit reopens Strategy Lab source/CI closure after a third source review of the rewritten blockcheck/Strategy Lab implementation. The earlier `_6` package build and CI results remain valid historical evidence for the code they tested, but `_6` is no longer the candidate for owner-assisted live scenario 1. Live verification is paused until the corrective series below is source/CI complete.

## Stable findings

### SL3-001 — Ordinary stale-worker recovery can falsely report semantic restoration

Classification: `broken / requires live test`

Affected locations:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh`
  - `strategy_lab_recovery_restore_service()`
  - `strategy_lab_reconcile_stale_job()`
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/lifecycle.sh`
- `scripts/test-strategy-lab-stale-worker-recovery.sh`
- retention logic that trusts `.restoration.verified`.

Evidence:

The ordinary stale-worker path uses public transaction `status/start/stop` exit codes and can set `.restoration.verified=true` while writing `strategy_unchanged=false`. It does not compare the initial and final semantic service evidence used by normal stage 90.

Impact:

A dead worker can be recorded as semantically restored without proof that runtime arguments, effective configuration, or normal firewall state match the initial snapshot. Retention may later treat that record as verified evidence.

Remediation plan:

Reuse the stage-90 semantic restoration contract for stale ordinary jobs: temporary cleanup, bounded service recovery, final semantic evidence collection, equality verification, truthful restoration result, and `RESTORE_FAILED` when proof is unavailable.

Acceptance criteria:

- `restoration.verified=true` is impossible when semantic evidence differs;
- verified recovery records `strategy_unchanged=true` and `temporary_runtime_clean=true`;
- corrupted runtime/config/firewall evidence yields `RESTORE_FAILED`;
- focused stale-worker regression covers initial RUNNING and STOPPED states.

Planned patch: **Patch 2**.

### SL3-002 — Circular stale-worker recovery lacks lifecycle ownership

Classification: `broken / requires live test`

Affected locations:

- `strategy_lab/circular_owner.sh`
- `strategy_lab_circular_launcher.sh`
- `zapret_service.sh`
- `scripts/test-strategy-lab-circular-owner.sh`.

Evidence:

Circular stale recovery calls `strategy_lab_restore_initial_service_state()` outside the service-owned Strategy Lab worker transaction. Internal actions `strategy-lab-status`, `strategy-lab-evidence`, `strategy-lab-start`, and `strategy-lab-stop` require a valid lifecycle owner and return `77` without it. The focused circular-owner test currently mocks the restore function and therefore does not exercise this guard.

Impact:

After a real circular worker dies, cleanup may be able to remove temporary state but semantic restoration of the normal Zapret2 service cannot reliably run under the required lifecycle lock/ownership contract.

Remediation plan:

Move stale circular restoration into a lifecycle-owned transaction or equivalent service-owned recovery runner. The launcher may detect stale ownership but must not directly perform protected normal-service actions.

Acceptance criteria:

- stale circular recovery owns the lifecycle lock before protected service actions;
- the real semantic restoration path is exercised without mocking it away;
- recovery proves the initial RUNNING/STOPPED semantic state or persists `RESTORE_FAILED` and blocks retry.

Planned patch: **Patch 3**.

### SL3-003 — Load-order override breaks Extended circular eligibility

Classification: `broken / duplicate`

Affected locations:

- `strategy_lab_worker.sh`
- `strategy_lab/worker_result.sh`
- `strategy_lab/worker_state_serialization.sh`
- `strategy_lab/profile.sh`
- `strategy_lab/circular.sh`
- `scripts/test-strategy-lab-unified-shortlist.sh`.

Evidence:

`worker_result.sh` defines circular eligibility using `circular_count/circular_items` and TLS 1.3 eligibility. `worker_state_serialization.sh`, sourced later by the real worker, redefines the same function using the general `.count/.items` shortlist. Extended mode may contain non-TLS13 entries in the general shortlist while circular validation intentionally uses only the TLS13 subset.

Impact:

The persisted `circular_candidate_count` can disagree with the circular backend, causing false ineligibility or false eligibility in Extended mode. Runtime behavior depends on module source order, which is forbidden by the corrective contract.

Remediation plan:

Keep one canonical circular-eligibility implementation with serialized state persistence. Remove the duplicate definition and add a module-namespace regression that detects unintended duplicate function definitions among modules loaded together by the main worker.

Acceptance criteria:

- one canonical `worker_result_set_circular_eligibility()` remains;
- Extended general shortlist size may differ from TLS13 circular subset without affecting correctness;
- regression loads the same module set/order as the real worker;
- no undocumented duplicate function definition can silently select behavior by load order.

Planned patch: **Patch 4**.

### SL3-004 — `worker_skip_unfinished()` bypasses state serialization

Classification: `broken / concurrency risk`

Affected locations:

- `strategy_lab/worker_stage_machine.sh`
- `strategy_lab/state.sh`
- `strategy_lab/worker_control.sh`
- `scripts/test-strategy-lab-state-race.sh`.

Evidence:

Normal state mutation uses `strategy_lab_state_transform()` with a per-job lock, atomic replacement, and monotonic `.revision`. `worker_skip_unfinished()` independently reads and replaces `status.json` without that lock or revision increment. Cancel/API and worker finalization can therefore race with this write.

Impact:

A newer cancel transition can be overwritten by an older worker copy, losing `cancel_requested_at`, regressing visible state, or violating revision ordering.

Remediation plan:

Route `worker_skip_unfinished()` and any other concurrently reachable direct `status.json` writer through the canonical serialized state transform.

Acceptance criteria:

- skip/finalize/cancel transitions share one state lock;
- `.revision` is monotonic for every state mutation;
- `cancel_requested=true` and its original timestamp survive concurrent finalization;
- the race regression repeatedly produces valid monotonic terminal JSON.

Planned patch: **Patch 5**.

### SL3-005 — Recovery caller timeout chain is shorter than legitimate restoration

Classification: `broken / timeout contract`

Affected locations:

- `src/opnsense/service/conf/actions.d/actions_zapret.conf`
- `StrategyLabController.php`
- `diagnostics.volt`
- ordinary and circular stale-recovery launcher paths.

Evidence:

Stage-90 restoration permits a 45-second bounded service action, while Strategy Lab configd actions and the PHP backend default to 10 seconds and the browser request timeout is 15 seconds. Synchronous stale reconciliation can therefore outlive its outer caller.

Impact:

The GUI/configd caller may terminate or abandon a valid recovery in progress, leaving stale pointers, repeated timeout responses, or an interrupted restoration transaction.

Remediation plan:

Make the entire synchronous recovery chain monotonic: native/service operation < configd action < MVC backend wait < browser AJAX wait, with bounded margins. Do not lengthen ordinary asynchronous job execution itself; only the synchronous recovery/control response envelope must contain the legitimate inner transaction.

Acceptance criteria:

- no outer timeout is shorter than the bounded recovery it supervises;
- a recovery lasting longer than the previous 10/15-second limits still returns a structured response;
- ordinary polling remains responsive when no stale recovery is needed.

Planned patch: **Patch 2** together with SL3-001 because both affect the same ordinary stale-recovery transaction boundary.

### SL3-006 — Obsolete hook/load-order surfaces remain after declared cleanup

Classification: `duplicate / unused`

Affected locations:

- `strategy_lab/expansion.sh`
- `strategy_lab/stability.sh`
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`
- `scripts/test-strategy-lab-obsolete-surfaces.sh`
- other jointly loaded Strategy Lab modules found by namespace inventory.

Evidence:

`strategy_lab_skip_unfinished()` remains defined in expansion/stability code even though documentation states the old state-level hook was removed and worker orchestration uses explicit stage functions. Additional repeated function names exist across modules, including the confirmed behavior-changing circular-eligibility duplicate.

Impact:

Dead transitional code obscures the active control flow and leaves future source-order regressions possible.

Remediation plan:

Remove the obsolete hook definitions and helpers that become unreachable; inventory jointly loaded modules; add a regression that rejects undocumented duplicate shell function definitions.

Acceptance criteria:

- no obsolete `strategy_lab_skip_unfinished()` definition remains;
- no jointly loaded module can override another module's function unintentionally;
- obsolete-surface documentation matches the actual tree.

Planned patch: **Patch 4** together with SL3-003 because both are one load-order/obsolete-surface cleanup scope.

### SL3-007 — `cancel_requested` is not completely localized in Diagnostics

Classification: `broken / presentation`

Affected locations:

- `src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt`
- `scripts/test-strategy-lab-progress-localization.sh`.

Evidence:

The backend has the non-terminal state `cancel_requested`, while the Diagnostics status-label map lacks `CANCEL_REQUESTED`. The fallback renderer can therefore display the raw technical state in the Russian UI.

Impact:

The progress/localization contract is incomplete and live localization scenario 16 can expose implementation vocabulary to the user.

Remediation plan:

Add RU/EN labels for `CANCEL_REQUESTED` and make the localization regression compare the actual backend state/outcome/status vocabulary against GUI mappings.

Acceptance criteria:

- every persisted Strategy Lab state/outcome/stage status has deliberate RU and EN presentation;
- `cancel_requested` never falls through to raw-key rendering;
- localization regression fails when a new backend state is introduced without presentation coverage.

Planned patch: **Patch 6**.

## Approved corrective patch sequence

The owner approved the following strictly ordered working plan on 2026-08-07.

### Patch 1 — Third-audit documentation and corrective plan

Scope: documentation only. Register SL3-001…SL3-007, reopen source/CI closure, freeze the patch order, and pause `_6` live scenario 1. No runtime behavior and no package revision change.

Verification: documentation consistency and path-applicable CI.

### Patch 2 — Ordinary stale recovery and timeout chain

Scope: SL3-001 + SL3-005. Replace command-exit stale recovery with the semantic stage-90 contract and make the synchronous configd/MVC/browser timeout envelope contain the bounded restore transaction.

Verification: focused stale-worker and semantic-restoration tests, timeout-chain regression, full corrective matrix, package CI.

### Patch 3 — Circular stale recovery lifecycle ownership

Scope: SL3-002. Ensure stale circular restoration runs only inside a real lifecycle-owned transaction and tests the real protected service path.

Verification: circular-owner recovery regression without a mocked restore, full corrective matrix, package CI.

### Patch 4 — Remove load-order overrides and obsolete hooks

Scope: SL3-003 + SL3-006. Centralize circular eligibility, remove dead transitional hooks, inventory jointly loaded module namespaces, and prohibit unintended duplicate definitions.

Verification: real-order Extended shortlist regression, namespace/obsolete-surface regression, full corrective matrix, package CI.

### Patch 5 — Serialize worker state transitions

Scope: SL3-004. Route skip/finalization state writes through the canonical state lock/revision transform and close cancel/finalize races.

Verification: concurrent cancel/skip/finalize regression plus full corrective matrix and package CI.

### Patch 6 — Complete RU/EN progress localization

Scope: SL3-007. Complete `cancel_requested` presentation and enforce vocabulary coverage between backend and GUI.

Verification: localization regression plus full corrective matrix and package CI.

### Patch 7 — Integrated third-audit regression gate

Scope: no new product behavior. Extend the integration harness to exercise the corrected paths together: ordinary stale RUNNING/STOPPED recovery, semantic mismatch failure, circular stale recovery under ownership, Extended mixed shortlist/TLS13 circular subset, cancel race, long recovery response envelope, cleanup residue, and saved Traffic Strategy immutability.

Verification: one complete mandatory Strategy Lab corrective matrix, repository CI, FreeBSD 15 package build and manifest verification.

### Patch 8 — Source/CI closure and live-test handoff

Scope: documentation only. Mark each SL3 finding implemented only where source + focused regression + mandatory matrix + package CI provide evidence. Do not claim live PASS. Designate the resulting FreeBSD 15 package candidate for owner-assisted live verification.

Verification: documentation consistency and path-applicable CI.

## Live gate after Patch 8

Only after Patch 8 may the owner-assisted OPNsense live matrix resume. Scenario 1 is executed first on the new candidate. Dependent scenarios remain blocked until scenario 1 passes. Special attention is required for cancel, timeout, initial RUNNING/STOPPED restoration, circular start/stop, circular stale-worker recovery, Settings lifecycle coordination, persisted reload, retention, localization, and residue cleanup.

A live failure opens a new finding and corrective patch; it does not retroactively convert earlier failed evidence to PASS and does not authorize skipping dependent scenarios.

## Current release boundary

- Stable release: **BLOCKED**.
- pkg-repository promotion: **BLOCKED**.
- `_6` owner live retest: **CANCELLED AS NEXT ACTION; SUPERSEDED BY THIS CORRECTIVE SERIES**.
- Next action after this documentation patch: **Patch 2 — ordinary stale recovery and timeout chain**.

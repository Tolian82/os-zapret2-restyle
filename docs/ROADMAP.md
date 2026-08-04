# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation and delivery stages.

Updated when:
A stage starts, completes, changes order, or gains approved work.

Read after:
`docs/DEVLOG.md`.

Do not store here:
Detailed history, architecture rationale, or complete procedures.

==================================================
CURRENT STAGE
==================================================

Milestone 8 — GUI maintenance and managed upstream components

Current source candidate:
`v0.3.2_5`

Current work package:
Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Specialist plan:
`docs/architecture/STRATEGY_LAB.md`

==================================================
SERIAL DELIVERY GATE
==================================================

Patch N+1 is not prepared until Patch N has passed every PR check, been squash merged,
completed every merge-triggered GitHub workflow, removed its task branch, and been
verified on `main` with no unresolved processing.

Manual checks requiring project-owner participation remain deferred until all 13
implementation patches pass this gate.

==================================================
PATCH STATUS
==================================================

Patch 1 — Documentation and approved architecture
Status: COMPLETE

Patch 2 — Asynchronous job and dormant GUI shell
Status: COMPLETE

- PR #51 checks and FreeBSD package build passed;
- squash merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- post-merge processing and task-branch cleanup completed.

Patch 3 — Lifecycle stop, cleanup, and restoration
Status: IN DELIVERY

- [x] Route the detached Strategy Lab job through `zapret_service.sh`.
- [x] Hold the existing shared lifecycle lock for the complete transaction.
- [x] Require inherited descriptor 9 for internal status/stop/start actions.
- [x] Snapshot complete RUNNING or STOPPED state.
- [x] Fail closed on incomplete or unknown state.
- [x] Stop and verify normal Zapret2 before later test stages.
- [x] Restore RUNNING to RUNNING and STOPPED to STOPPED.
- [x] Execute stage 90 after normal completion, cancel, signal, timeout, and error.
- [x] Return explicit RESTORE_FAILED when final state cannot be restored.
- [x] Preserve approved Russian and English canceled-stage messages.
- [x] Add focused lifecycle, cancellation, failure-injection, and lock-ownership tests.
- [x] Advance package candidate to `0.3.2_5` without changing VERSION.
- [x] Synchronize state, roadmap, workflow, audit, patch note, and devlog.

Patch 4 — Targets, network precheck, and clean baseline
Status: BLOCKED BY PATCH 3 GATE

Patch 5 — One isolated temporary candidate runtime
Status: BLOCKED

Patch 6 — TLS 1.3 family screening
Status: BLOCKED

Patch 7 — Accepted-family parameter expansion
Status: BLOCKED

Patch 8 — Stability, shortlist, and report
Status: BLOCKED

Patch 9 — Extended TLS 1.2 and HTTP
Status: BLOCKED

Patch 10 — QUIC strategy branch
Status: BLOCKED

Patch 11 — Arbitrary UDP strategy branch
Status: BLOCKED

Patch 12 — Temporary circular live validation
Status: BLOCKED

Patch 13 — Final synchronous Blockcheck replacement
Status: BLOCKED

==================================================
POST-PATCH-13 VERIFICATION
==================================================

After every patch completes the serial GitHub gate, run the consolidated owner-assisted
OPNsense verification matrix recorded in `docs/architecture/STRATEGY_LAB.md`.

==================================================
OTHER MILESTONE 8 WORK
==================================================

Do not mix these tasks into Strategy Lab patches:

- passive newer stable-release notification;
- additional BLOB repository management after an owner-approved repository contract;
- unrelated route, lifecycle, and audit backlog.

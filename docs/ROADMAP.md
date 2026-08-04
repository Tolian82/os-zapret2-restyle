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
`v0.3.2_4`

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

- documentation-only atomic commit;
- PR #50 checks and FreeBSD package build passed;
- squash merged to `main`;
- task branch removed and verified absent.

Patch 2 — Asynchronous job and dormant GUI shell
Status: IN DELIVERY

- [x] Add start/status/cancel/result launcher modes.
- [x] Add detached framework worker.
- [x] Add common and state modules.
- [x] Return an immediate generated `job_id`.
- [x] Enforce one active job.
- [x] Write atomic `status.json` and ordered `events.ndjson`.
- [x] Add cancel marker and partial canceled result.
- [x] Preserve exact `SKIPPED — отменено` / `SKIPPED — canseled` output.
- [x] Add four configd actions.
- [x] Add four Diagnostics API actions.
- [x] Add dormant progress, polling, and Stop test GUI helpers.
- [x] Keep the current Blockcheck button on the legacy path.
- [x] Add focused mocked CI coverage.
- [x] Advance package candidate to `0.3.2_4` without changing VERSION.
- [x] Synchronize audit, state, roadmap, changelog, patch note, and devlog.

Patch 3 — Lifecycle stop, cleanup, and restoration
Status: BLOCKED BY PATCH 2 GATE

- shared lifecycle exclusion;
- initial RUNNING/STOPPED snapshot;
- normal Zapret2 stop and complete absence verification;
- cleanup after success, cancellation, timeout, signal, and error;
- exact RUNNING-to-RUNNING and STOPPED-to-STOPPED restoration;
- explicit RESTORE_FAILED;
- automated lifecycle mocks only; owner-assisted checks remain deferred.

Patch 4 — Targets, network precheck, and clean baseline
Status: BLOCKED

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

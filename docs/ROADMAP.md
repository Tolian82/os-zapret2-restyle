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
`v0.3.2_6`

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

Patch 3 — Lifecycle stop, cleanup, and restoration
Status: COMPLETE

- clean replacement PR #53 passed all checks and FreeBSD package build;
- squash merged as `100f324d09539e672586b12e3cd96c26baf351b2`;
- task branch cleanup and `main` verification completed.

Patch 4 — Targets, network precheck, and clean baseline
Status: IN DELIVERY

- [x] Normalize and classify domain or IPv4 input.
- [x] Reject malformed target values.
- [x] Persist explicit required endpoints.
- [x] Add the approved Telegram endpoint pair.
- [x] Run IPv4, IPv6, and fixed QUIC/IPv4 controls concurrently.
- [x] Require both an IPv6 default route and control connection.
- [x] Use only QUIC command exit status for classification.
- [x] Enforce the six-second stage-30 budget.
- [x] Run explicit clean TLS 1.3 GET probes for domain endpoints.
- [x] Run direct TCP/443 baseline for IPv4 targets.
- [x] Enforce the five-second stage-40 budget.
- [x] Return `TARGET_ACCESSIBLE` when every required endpoint works cleanly.
- [x] Separate valid negative results, timeout, and internal errors.
- [x] Preserve mandatory restoration on every path.
- [x] Add focused mocked precheck/baseline/timeout coverage.
- [x] Advance package candidate to `0.3.2_6` without changing VERSION.
- [x] Synchronize state, roadmap, workflow, audit, changelog, patch note, and devlog.

Patch 5 — One isolated temporary candidate runtime
Status: BLOCKED BY PATCH 4 GATE

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

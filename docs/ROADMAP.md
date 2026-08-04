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

Current source candidate: `v0.3.2_9`
Current work package: Strategy Lab asynchronous replacement of synchronous Diagnostics Blockcheck.
Specialist plan: `docs/architecture/STRATEGY_LAB.md`

==================================================
SERIAL DELIVERY GATE
==================================================

Patch N+1 is not prepared until Patch N has passed every PR check, been squash merged, completed every merge-triggered GitHub workflow, removed its task branch, and been verified on `main` with no unresolved processing.

Manual checks requiring project-owner participation remain deferred until all 13 implementation patches pass this gate.

==================================================
PATCH STATUS
==================================================

Patch 1 — Documentation and approved architecture: COMPLETE
Patch 2 — Asynchronous job and dormant GUI shell: COMPLETE
Patch 3 — Lifecycle stop, cleanup, and restoration: COMPLETE
Patch 4 — Targets, network precheck, and clean baseline: COMPLETE
Patch 5 — One isolated temporary candidate runtime: COMPLETE
Patch 6 — TLS 1.3 family screening: COMPLETE

Patch 7 — Accepted-family parameter expansion: IN DELIVERY

- [x] Expand only families accepted by stage 50.
- [x] Keep different candidate strategies strictly sequential.
- [x] Reuse the isolated runtime and target-scoped rules.
- [x] Add bounded family-specific variants.
- [x] Stop after five working candidates or catalog exhaustion.
- [x] Preserve every completed result atomically.
- [x] Classify per-candidate timeout as rejection.
- [x] Enforce the 60-second stage budget.
- [x] Add focused accepted-only, order, early-stop, and timeout coverage.
- [x] Advance package candidate to `0.3.2_9` without changing VERSION.

Patch 8 — Stability, shortlist, and report: BLOCKED BY PATCH 7 GATE
Patch 9 — Extended TLS 1.2 and HTTP: BLOCKED
Patch 10 — QUIC strategy branch: BLOCKED
Patch 11 — Arbitrary UDP strategy branch: BLOCKED
Patch 12 — Temporary circular live validation: BLOCKED
Patch 13 — Final synchronous Blockcheck replacement: BLOCKED

==================================================
POST-PATCH-13 VERIFICATION
==================================================

After every patch completes the serial GitHub gate, run the consolidated owner-assisted OPNsense verification matrix recorded in `docs/architecture/STRATEGY_LAB.md`.

==================================================
OTHER MILESTONE 8 WORK
==================================================

Do not mix these tasks into Strategy Lab patches:

- passive newer stable-release notification;
- additional BLOB repository management after an owner-approved repository contract;
- unrelated route, lifecycle, and audit backlog.

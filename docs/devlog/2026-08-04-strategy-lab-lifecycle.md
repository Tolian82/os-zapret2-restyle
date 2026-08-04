# 2026-08-04 — Strategy Lab lifecycle transaction

Logical change:
Implement Strategy Lab stages 10, 20, and 90 without adding network probes or a
temporary candidate runtime.

Baseline:
`962f8de7728477ab8d47c375aec24cb147381c0f`

Completed:

- added a lifecycle module for complete service-state classification;
- routed the Strategy Lab worker through the existing shared lifecycle lock;
- added owner-only internal status, stop, and start actions;
- captured RUNNING or STOPPED before mutation and rejected incomplete state;
- stopped and verified the normal service before later test stages;
- made cleanup and exact restoration mandatory after normal completion,
  cancellation, signal, and error;
- preserved RUNNING-to-RUNNING and STOPPED-to-STOPPED behavior;
- added explicit `RESTORE_FAILED` handling;
- ensured cancellation skips only unexecuted stages and never skips stage 90;
- advanced the package candidate to `0.3.2_5`.

Automated validation:

- POSIX shell syntax passed for every modified and new shell file;
- RUNNING initial state was stopped and restored to RUNNING;
- STOPPED initial state remained STOPPED without an unnecessary start;
- Russian and English cancellation paths restored the original state;
- injected restore failure produced stage 90 FAIL and `RESTORE_FAILED`;
- incomplete initial state failed closed before service mutation;
- internal lifecycle actions rejected execution without worker ownership of the
  lifecycle lock;
- the existing synchronous Blockcheck caller remained unchanged.

Not performed:

No owner-assisted OPNsense commands. Those checks remain deferred until Patch 13
and the complete implementation series have passed GitHub processing.

Next:
Patch 4 adds target validation, IPv4/IPv6/QUIC capability prechecks, and the clean
baseline only after Patch 3 completes its full GitHub serial-delivery gate.

==================================================
DELIVERY RESULT
==================================================

The first delivery attempt, PR #52, was closed without merge because the existing
branch-hygiene regression test hard-coded package revision 3. All Strategy Lab lifecycle
checks had passed. The clean replacement changed that assertion to require a positive
numeric package revision, retained one atomic implementation commit, and opened PR #53.

PR #53 passed title validation, Validate Project, and the FreeBSD package build. It was
squash merged as `100f324d09539e672586b12e3cd96c26baf351b2`; the task branch was removed
and the resulting `main` was verified before Patch 4 preparation.

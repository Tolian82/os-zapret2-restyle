# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Version, package revision, delivery stage, verification state, priority, blockers, or
next action changes.

Read after:
`docs/INDEX.md`.

Do not store here:
Detailed decision history, permanent procedures, full architecture, or product
requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
`os-zapret2-restyle`

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
`main`

Current published release:
`v0.3.2`

Current published package:
`os-zapret2-restyle-0.3.2_1.pkg`

Current source/package candidate:
`os-zapret2-restyle-0.3.2_5.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
Strategy Lab Patch 3 is an ordinary package patch. `VERSION=0.3.2` remains unchanged
and `PLUGIN_REVISION` advances from `4` to `5`. No tag, GitHub Release, release asset,
or pkg-repository publication is authorized.

==================================================
VERIFIED BASELINE
==================================================

The project owner verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that its functionality works correctly.

DIAG-002 remains resolved and owner live verified.

Strategy Lab Patch 1 is complete and merged as
`76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`.

Strategy Lab Patch 2 is complete:

- PR #51 passed Pull request title, Validate Project, and FreeBSD package build;
- squash merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- post-merge processing completed;
- task branch was removed;
- `main` was verified before Patch 3 preparation.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Specialist authority:
`docs/architecture/STRATEGY_LAB.md`

Current patch:
Patch 3 — lifecycle snapshot, service stop, cleanup, and exact restoration.

Implemented in the candidate:

- Strategy Lab execution enters the existing service-owned
  `/var/run/zapret2-lifecycle.lock` boundary;
- the lock is held from snapshot through mandatory stage 90 restoration;
- internal status/stop/start actions require both inherited ownership and open descriptor
  9 and cannot be invoked as ordinary unlocked service commands;
- initial state is accepted only as complete `RUNNING` or complete `STOPPED`;
- incomplete or unknown state fails closed before mutation;
- a running service is stopped and verified fully stopped before later test stages;
- a stopped service remains stopped;
- success, cancellation, signal, timeout/error paths converge on stage 90;
- exact `RUNNING → RUNNING` and `STOPPED → STOPPED` restoration is verified;
- restoration failure produces `RESTORE_FAILED`;
- cancellation keeps completed results, marks unexecuted test stages with the approved
  selected-language `SKIPPED` message, and still runs stage 90;
- network probes, temporary candidate runtime, and firewall candidate rules remain
  outside Patch 3.

==================================================
AUTOMATED VERIFICATION
==================================================

The focused mocked lifecycle contract passed for:

- `RUNNING → STOPPED → RUNNING`;
- `STOPPED → STOPPED` without an accidental start;
- cancellation after normal service stop;
- exact Russian and English canceled-stage text;
- one-active-job busy response;
- explicit `RESTORE_FAILED` after injected start failure;
- fail-closed incomplete initial state with no mutation;
- idle cleanup and unsafe target rejection;
- service-owned lifecycle transaction with inherited descriptor 9;
- rejection of internal lifecycle actions without lock ownership;
- POSIX shell syntax and legacy Blockcheck-path preservation.

Owner-assisted OPNsense checks remain deferred until all 13 Strategy Lab patches are
published and fully processed by GitHub.

==================================================
SERIAL DELIVERY STATE
==================================================

Patch 1:
COMPLETE

Patch 2:
COMPLETE

Patch 3:
IN DELIVERY

Patch 4:
BLOCKED until Patch 3 completes every PR check, squash merge, post-merge workflow,
automatic branch cleanup, `main` verification, branch-absence verification, and all
remaining GitHub processing.

==================================================
NEXT ACTION
==================================================

Publish and completely process Patch 3. Do not prepare Patch 4 before the complete
serial delivery gate for Patch 3 is satisfied.

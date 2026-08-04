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
`os-zapret2-restyle-0.3.2_4.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
Strategy Lab Patch 2 is an ordinary package patch. `VERSION=0.3.2` remains unchanged
and `PLUGIN_REVISION` advances from `3` to `4`. No project release, tag, GitHub Release,
release asset, or pkg-repository publication is authorized.

==================================================
VERIFIED BASELINE
==================================================

The project owner verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that its functionality works correctly.

DIAG-002 is resolved and owner live verified. Positive and negative Test Domain
Connectivity results render correctly.

Patch `v0.3.2_3` localized initial Blockcheck guidance and is merged to `main`.

Strategy Lab Patch 1 is complete:

- architecture and 13-patch sequence recorded;
- PR checks and FreeBSD package build passed;
- PR #50 squash merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- task branch removed;
- `main` verified before Patch 2 preparation.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Specialist authority:
`docs/architecture/STRATEGY_LAB.md`

Current patch:
Patch 2 — asynchronous job and dormant GUI shell.

Implemented in the candidate:

- `strategy_lab_launcher.sh` with start, status, cancel, and result modes;
- `strategy_lab_worker.sh` detached through `daemon(8)`;
- shared `common.sh` and `state.sh` modules;
- one active-job pointer and non-blocking launcher lock;
- atomically replaced `status.json`;
- ordered `events.ndjson`;
- per-job PID, cancel marker, and log paths;
- generated `job_id` returned immediately;
- busy result for a second start while one job is active;
- completed partial result for the framework-only worker;
- cancellation that preserves the job record and marks unfinished stages `SKIPPED`;
- exact approved canceled messages:
  - `SKIPPED — отменено`;
  - `SKIPPED — canseled`;
- four Diagnostics API actions and four configd actions;
- dormant Diagnostics progress/Stop shell with one-second polling helpers;
- current Blockcheck button and synchronous execution path intentionally unchanged;
- focused mocked contract test added to CI.

Patch 2 does not:

- perform DNS, TLS, QUIC, IPv6, HTTP, or UDP probes;
- stop or start normal Zapret2;
- launch a temporary candidate dvtws2;
- modify firewall rules;
- replace the active Blockcheck button path.

==================================================
AUTOMATED VERIFICATION
==================================================

Completed before publication:

- POSIX shell syntax for all new Strategy Lab scripts;
- PHP syntax for DiagnosticsController;
- mocked asynchronous start and immediate `job_id` response;
- normal partial framework completion;
- one-active-job busy behavior;
- Russian and English cancellation result text;
- atomic status and active-job cleanup contract;
- idle status after completion;
- unsafe target rejection;
- static configd, API, dormant GUI, and legacy-path preservation checks.

Owner-assisted OPNsense checks remain deferred until all 13 patches are published and
fully processed by GitHub.

==================================================
SERIAL DELIVERY STATE
==================================================

Patch 1:
COMPLETE

Patch 2:
IN DELIVERY

Patch 3:
BLOCKED until Patch 2 completes PR checks, squash merge, every post-merge workflow,
automatic branch cleanup, `main` verification, branch-absence verification, and all
remaining GitHub processing.

==================================================
NEXT ACTION
==================================================

Publish and completely process Patch 2. Do not prepare Patch 3 before the complete
serial delivery gate for Patch 2 is satisfied.

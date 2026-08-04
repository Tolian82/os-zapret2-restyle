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
`os-zapret2-restyle-0.3.2_7.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
Strategy Lab Patch 5 is an ordinary package patch. `VERSION=0.3.2` remains unchanged
and `PLUGIN_REVISION` advances from `6` to `7`. No tag, GitHub Release, release asset,
or pkg-repository publication is authorized.

==================================================
VERIFIED BASELINE
==================================================

The project owner verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that its functionality works correctly.
DIAG-002 remains resolved and owner live verified.

Strategy Lab delivery baseline:

- Patch 1 merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- Patch 2 merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- Patch 3 merged as `100f324d09539e672586b12e3cd96c26baf351b2`;
- Patch 4 PR #54 passed title validation, Validate Project, and the FreeBSD package
  build;
- Patch 4 squash merged as `ad58111aa2f00588060d167358a73c010abd8ae4`;
- its task branch was removed and `main` was verified before Patch 5 preparation.

The first Patch 3 delivery attempt, PR #52, was closed without merge because the
branch-hygiene regression test incorrectly required stale `PLUGIN_REVISION=3`. The clean
replacement fixed that test to accept a positive numeric revision and passed completely.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Specialist authority:
`docs/architecture/STRATEGY_LAB.md`

Current patch:
Patch 5 — one isolated temporary Zapret2 candidate runtime.

Implemented in the candidate:

- one job-specific temporary runtime, PID file, log, argument file, hostlist, and
  resolved IPv4 address list;
- exactly one temporary dvtws2 process without supervisor restart behavior;
- lifecycle-lock descriptor 9 closed before child creation;
- reserved divert port 9989 and IPFW range 19100–19131, separate from normal rules;
- temporary TCP/443 rules limited to resolved IPv4 addresses of required endpoints;
- up to two required endpoints tested concurrently under the same active strategy;
- Zapret2-only smoke fixture `--lua-desync=multisplit:pos=1`;
- structured `candidate_smoke` state with exact strategy, endpoint results, and
  `all_pass`;
- unconditional teardown after success, failure, timeout, cancellation, or signal;
- repeated safety cleanup in mandatory stage 90;
- worker internals split into message, control, and flow modules without changing the
  asynchronous contract;
- lifecycle test fixtures split into bounded helper files for stable CI execution.

Patch 5 does not add the seven-family catalog, family acceptance, parameter expansion,
stability scoring, shortlist, extended protocols, circular validation, active GUI
switch-over, or legacy Blockcheck removal.

==================================================
AUTOMATED VERIFICATION
==================================================

Focused mocked coverage passes for:

- one temporary dvtws2 process and no supervisor;
- target-scoped TCP/443 IPFW rules in the reserved range;
- two endpoints under one active strategy;
- structured candidate result storage;
- teardown after success;
- teardown after injected firewall failure;
- no remaining candidate PID, process, or temporary rule;
- RUNNING→RUNNING, STOPPED→STOPPED, cancellation, timeout, and restore-failure
  lifecycle regressions;
- all prior target, precheck, baseline, async-job, API/configd, and legacy-path
  contracts.

Owner-assisted OPNsense checks remain deferred until all 13 Strategy Lab patches are
published and fully processed by GitHub.

==================================================
SERIAL DELIVERY STATE
==================================================

Patch 1: COMPLETE

Patch 2: COMPLETE

Patch 3: COMPLETE

Patch 4: COMPLETE

Patch 5: IN DELIVERY

Patch 6:
BLOCKED until Patch 5 completes every PR check, squash merge, post-merge workflow,
automatic branch cleanup, `main` verification, branch-absence verification, and all
remaining GitHub processing.

==================================================
NEXT ACTION
==================================================

Publish and completely process Patch 5. Do not prepare Patch 6 before the complete
serial delivery gate for Patch 5 is satisfied.

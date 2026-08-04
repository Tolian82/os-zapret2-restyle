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
`os-zapret2-restyle-0.3.2_3.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
The active Strategy Lab Patch 1 is documentation only. `VERSION=0.3.2` and
`PLUGIN_REVISION=3` remain unchanged. No project release, tag, GitHub Release, release
asset, or pkg-repository publication is authorized.

==================================================
VERIFIED PRODUCT STATE
==================================================

The project owner personally verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that everything in it works correctly.

DIAG-002 is resolved and owner live verified. Positive and negative Test Domain
Connectivity results render correctly.

Release `v0.3.2` preserves that runtime baseline and adds GitHub publication governance.

Patch `v0.3.2_3` localized the initial Diagnostics Blockcheck guidance according to the
selected OPNsense language and is merged to `main`.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Architecture status:
Approved for implementation.

Specialist authority:
`docs/architecture/STRATEGY_LAB.md`

Decision:
`docs/decisions/DEC-2026-08-04-strategy-lab.md`

Audit expansion:
`docs/audit/DIAG-001-strategy-lab.md`

Patch 1 scope:

- documentation only;
- record all approved product, lifecycle, timeout, stage, reporting, localization,
  cancellation, strategy-search, verification, and delivery decisions;
- record the complete 13-patch implementation order;
- record that owner-assisted manual OPNsense checks occur only after all implementation
  patches are published and fully processed by GitHub;
- record the blocking rule that Patch N+1 is not prepared until Patch N has completed
  PR checks, squash merge, post-merge workflows, branch cleanup, `main` verification,
  and branch-absence verification.

==================================================
APPROVED STRATEGY LAB SUMMARY
==================================================

- asynchronous start/status/events/cancel/result job model;
- numbered stages 00 through 99;
- normal Zapret2 stopped and verified absent during tests;
- exact initial service-state restoration after every exit path;
- one active job and one active candidate strategy;
- up to two endpoints under the same candidate;
- fixed QUIC precheck: `yandex.ru:443`, IPv4, ALPN `h3`, timeout 2 seconds, exit status
  only;
- standard overall budget 150 seconds;
- separate extended budget 120 seconds;
- family-first TLS 1.3 search;
- 3/3 stability for every required endpoint;
- shortlist of three to five stable strategies;
- English default and Russian for OPNsense `ru*`;
- cancellation preserves completed results, shows remaining stages as skipped, and
  performs mandatory restoration;
- approved cancellation output:
  - `SKIPPED — отменено`;
  - `SKIPPED — canseled`;
- final patch removes or reduces the old synchronous `blockcheck.sh` to an asynchronous
  compatibility adapter.

==================================================
SERIAL DELIVERY STATE
==================================================

Current patch:
Patch 1 — Strategy Lab documentation and approved architecture.

Next patch:
Patch 2 — asynchronous job and GUI shell.

Blocking gate:
Patch 2 preparation must not begin until Patch 1 has completed every GitHub check and
post-merge workflow, its task branch has been deleted, `main` has been verified, and no
GitHub processing remains unresolved.

==================================================
MANUAL VERIFICATION STATE
==================================================

No owner-assisted manual commands are requested during Patches 1 through 13.

Each patch receives automated focused tests, syntax/static validation, standard CI,
package build where applicable, and complete post-merge GitHub processing.

After Patch 13, one consolidated owner-assisted OPNsense matrix verifies the complete
Strategy Lab implementation.

==================================================
NEXT ACTION
==================================================

Publish and completely process Strategy Lab Patch 1 through the mandatory atomic PR,
CI, squash merge, post-merge workflow, automatic cleanup, `main` verification, and
branch-absence sequence. Do not prepare Patch 2 before that sequence is complete.

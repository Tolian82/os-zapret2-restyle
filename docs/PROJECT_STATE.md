# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Version, package revision, delivery stage, verification state, priority, blockers, or next action changes.

Read after:
`docs/INDEX.md`.

Do not store here:
Detailed decision history, permanent procedures, full architecture, or product requirements.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Repository: https://github.com/Tolian82/os-zapret2-restyle
Primary branch: `main`
Published release: `v0.3.2`
Published package: `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_9.pkg`
Delivery stage: `DEVELOPMENT`

Patch 7 is an ordinary package patch. `VERSION=0.3.2` remains unchanged and `PLUGIN_REVISION` advances from `8` to `9`. No tag, GitHub Release, release asset, or pkg-repository publication is authorized.

==================================================
STRATEGY LAB SERIAL BASELINE
==================================================

- Patch 1: complete.
- Patch 2: complete.
- Patch 3: complete.
- Patch 4: complete.
- Patch 5: PR #55 passed all checks and package build; squash merged as `2fb51bebafc95a9c0b6cd4b6d6bbc4aa0574dacd`; branch removed.
- Patch 6: PR #56 passed title validation, Validate Project, and FreeBSD package build; squash merged as `d4bd184a16aa67c6070088547578c201a275b86c`; branch removed.

Owner-assisted OPNsense verification remains deferred until all 13 Strategy Lab implementation patches complete the serial GitHub gate.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab Patch 7 — accepted-family parameter expansion.

Implemented in the candidate:

- a bounded TLS 1.3 expansion catalog;
- expansion only for families accepted by stage 50;
- strictly sequential candidate execution;
- the same isolated candidate runtime and target-scoped firewall ownership as Patch 5;
- up to two required endpoints under one active candidate;
- five-second per-candidate timeout and 60-second stage budget;
- early stop after five working candidates;
- atomic result persistence after every completed candidate;
- timeout classified as a failed candidate rather than an internal error;
- stage-60 state and progress output without changing the legacy active Diagnostics path.

Patch 7 does not add stability scoring, shortlist/report, extended protocols, circular validation, GUI activation, or legacy Blockcheck removal.

==================================================
NEXT ACTION
==================================================

Publish and completely process Patch 7. Patch 8 remains blocked until every Patch-7 PR, CI, package-build, squash-merge, cleanup, and `main` verification condition is complete.

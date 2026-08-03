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
`os-zapret2-restyle-0.3.2_2.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
`v0.3.2_2` is an ordinary package patch. `VERSION` remains `0.3.2`; no new tag,
GitHub Release, assets, or pkg-repository publication is authorized.

==================================================
VERIFIED PRODUCT STATE
==================================================

The project owner personally verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that everything in it works correctly.

DIAG-002 is resolved and owner live verified. Positive and negative Test Domain
Connectivity results render correctly.

Release `v0.3.2` preserves that runtime baseline and adds GitHub publication governance.

==================================================
REPOSITORY CLEANUP STATE
==================================================

Verified on 2026-08-03:

- the accidental branches `release/v0.3.2`, `release/v0.3.2-clean`,
  `release/v0.3.2-final`, `release/v0.3.2-atomic`, and
  `release/v0.3.2-publish` are absent;
- there are no open pull requests;
- `main` remains the v0.3.2 release commit;
- historical pre-existing branches remain outside this cleanup scope and must not be
  deleted without separate owner authority.

==================================================
PATCH v0.3.2_2
==================================================

Objective:
Prevent one delivery cycle from creating multiple remote branches and remove the need
for manual deletion of a normally merged task branch.

Included:

- branch creation only after final blobs/tree/commit preparation;
- exactly one remote task branch per logical cycle;
- prohibited preparatory suffix branches;
- required cleanup-path preflight;
- explicit patch-versus-release contract;
- automatic deletion of the merged same-repository head branch on `main` push;
- focused CI contract test;
- package revision advanced from 1 to 2 with `VERSION` unchanged.

==================================================
NEXT PRODUCT WORK
==================================================

1. Implement passive notification when a newer stable bol-van/zapret2 release exists.
2. Design additional BLOB repository management only after the owner supplies and
   approves its repository and technical contract.
3. Continue retained diagnostics timeout-chain and unrelated audit backlog as separate
   focused changes.

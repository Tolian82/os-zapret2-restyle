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
`v0.3.2_3` is an ordinary package patch. `VERSION` remains `0.3.2`; no new tag,
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
- `main` includes the merged v0.3.2_2 publication-governance patch;
- historical pre-existing branches remain outside this cleanup scope and must not be
  deleted without separate owner authority.

==================================================
PATCH v0.3.2_3
==================================================

Objective:
Make the initial Blockcheck guidance on Diagnostics follow the language selected in
OPNsense while preserving the exact approved English and Russian wording.

Included:

- English remains the default and no-JavaScript fallback;
- Russian is selected when the document language begins with `ru`;
- both approved texts are rendered as two text-only paragraphs;
- the obsolete English-only guidance is removed;
- focused localization contract coverage is added to CI;
- package revision advances from 2 to 3 with `VERSION` unchanged.

==================================================
NEXT PRODUCT WORK
==================================================

1. Implement passive notification when a newer stable bol-van/zapret2 release exists.
2. Design additional BLOB repository management only after the owner supplies and
   approves its repository and technical contract.
3. Continue retained diagnostics timeout-chain and unrelated audit backlog as separate
   focused changes.

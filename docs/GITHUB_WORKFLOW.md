# os-zapret2-restyle — GitHub workflow

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the official repository maintained and how are patches and releases controlled?

Purpose:
Define repository identity, source baseline, authorization boundaries, patch/release separation, release control, and distribution verification. Exact branch and PR event discipline is delegated to `GITHUB_PUBLICATION.md`.

Updated when:
Repository policy, patch semantics, release authorization, automation, or distribution verification changes.

Read after:
`REQUIREMENTS.md`.

Do not store here:
Runtime architecture, product requirements, current task status, or chronological history.

==================================================
OFFICIAL REPOSITORY
==================================================

Repository: https://github.com/Tolian82/os-zapret2-restyle
Primary branch: `main`
Default source baseline: exact current `main` recorded before work starts.

==================================================
AUTHORIZATION AND PATCH BOUNDARY
==================================================

Ordinary development requests authorize one atomic logical commit, exactly one final remote task branch, one ready PR, one complete check set, one squash merge, `main` verification, and automatic branch cleanup.

A package patch keeps `VERSION` unchanged and advances only `PLUGIN_REVISION`. It creates no tag, GitHub Release, release assets, or pkg-repository publication.

Published project release: `v0.3.2`
Published package: `os-zapret2-restyle-0.3.2_1.pkg`
Current patch candidate: `os-zapret2-restyle-0.3.2_9.pkg`

Patch `v0.3.2_9` adds accepted-family parameter expansion, bounded early stopping, and persistent stage-60 results. It keeps the legacy synchronous Blockcheck active and is not a project release.

==================================================
DELIVERY PROTOCOL
==================================================

`docs/GITHUB_PUBLICATION.md` is the specialist authority:

one logical change
        ↓
all blobs, one tree, one atomic commit
        ↓
exactly one remote branch at the final commit
        ↓
one ready pull request
        ↓
one complete check set
        ↓
one squash merge
        ↓
automatic branch deletion and verification

Strategy Lab adds a strict serial gate: no later patch is prepared until the previous patch completes every GitHub operation and leaves no unresolved processing.

Patch `v0.3.2_9` PR title:

`v0.3.2_9: Add Strategy Lab parameter expansion`

Its squash subject is an ordinary logical subject, not a release subject.

==================================================
RELEASE CONTROL
==================================================

Only an explicitly authorized new `VERSION` follows the release pipeline. Patch `v0.3.2_9` stops after ordinary merge, complete GitHub processing, branch cleanup, and `main` verification.

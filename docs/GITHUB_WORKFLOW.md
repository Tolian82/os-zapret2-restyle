# os-zapret2-restyle — GitHub workflow

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the official repository maintained and how are patches and releases controlled?

Purpose:
Define repository identity, source baseline, authorization boundaries, patch/release
separation, release control, and distribution verification. Exact branch and PR event
discipline is delegated to `GITHUB_PUBLICATION.md`.

Updated when:
Repository policy, patch semantics, release authorization, automation, or distribution
verification changes.

Read after:
`REQUIREMENTS.md`.

Do not store here:
Runtime architecture, product requirements, current task status, or chronological
history.

==================================================
OFFICIAL REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
`main`

Default source baseline:
The exact current `main` commit recorded before work starts.

==================================================
AUTHORIZATION BOUNDARIES
==================================================

Ordinary development or patch requests authorize one atomic logical commit, exactly one
remote task branch created only after the commit is final, one ready pull request, one
complete check set, one squash merge, `main` verification, and automatic branch cleanup.

A package patch keeps `VERSION` unchanged and advances only `PLUGIN_REVISION`. It does
not authorize a tag, GitHub Release, release assets, or pkg-repository publication.

A project release requires an explicit exact new version.

==================================================
CURRENT SOURCE AND PACKAGE STATE
==================================================

Published project release:
`v0.3.2`

Published package:
`os-zapret2-restyle-0.3.2_1.pkg`

Current patch candidate:
`os-zapret2-restyle-0.3.2_6.pkg`

Patch `v0.3.2_6` adds Strategy Lab target normalization, explicit endpoints, network
capability prechecks, clean TLS 1.3/TCP baselines, and stage-level time budgets. It
keeps the legacy Blockcheck path active and is not a project release.

==================================================
CURRENT DELIVERY PROTOCOL
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

Strategy Lab adds a stricter series gate: no later patch is prepared until the previous
patch also completes every merge-triggered workflow and leaves no unresolved GitHub
processing.

==================================================
PULL-REQUEST PROTOCOL
==================================================

Patch `v0.3.2_6` title:

`v0.3.2_6: Add Strategy Lab network baseline`

Its squash subject is an ordinary logical subject, not a release subject.

==================================================
ATOMIC API PUBLICATION
==================================================

1. Prepare every final file and mode without a branch.
2. Create all blobs.
3. Create one tree based on recorded `main`.
4. Create one commit with recorded `main` as sole parent.
5. Validate the commit and recheck `main`.
6. Verify branch-name absence and cleanup availability.
7. Create exactly one task branch.
8. Open one ready PR.

Never stream a multi-file change through sequential contents-API commits.

==================================================
RELEASE CONTROL
==================================================

Only an explicitly authorized new `VERSION` follows the release pipeline. Patch
`v0.3.2_6` stops after ordinary merge, complete GitHub processing, branch cleanup, and
`main` verification.

==================================================
HISTORY RESPONSIBILITY
==================================================

Completed work belongs in `DEVLOG.md` or `docs/devlog/`. Decisions belong in
`DECISIONS.md` or `docs/decisions/`. Patch notes belong under `docs/patches/`.

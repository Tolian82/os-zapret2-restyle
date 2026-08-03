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

Ordinary development or patch requests authorize:

- one atomic logical commit;
- exactly one remote task branch, created only after the commit is final;
- one ready pull request;
- one complete check set;
- one squash merge;
- verification of `main`;
- automatic deletion and absence verification of the task branch.

A request for patch `vX.Y.Z_N` keeps `VERSION=X.Y.Z` and sets
`PLUGIN_REVISION=N`. It does not authorize a tag, GitHub Release, release assets, or
pkg-repository publication.

A project release requires an explicit request for an exact new version. The assistant
must never infer or choose that version independently.

==================================================
CURRENT SOURCE AND PACKAGE STATE
==================================================

Published project release:
`v0.3.2`

Published package:
`os-zapret2-restyle-0.3.2_1.pkg`

Current patch candidate:
`os-zapret2-restyle-0.3.2_2.pkg`

Patch `v0.3.2_2` changes repository governance and automatic branch cleanup. It is not
a new project release.

==================================================
FORWARD-ONLY VERSION POLICY
==================================================

Published tags, releases, assets, and versions are immutable. Never move a tag, replace
assets, roll `VERSION` backward, reuse a version, or rewrite published history.

A later project release uses a higher explicitly approved version. A package patch may
advance only `PLUGIN_REVISION` while `VERSION` stays unchanged.

==================================================
CURRENT DELIVERY PROTOCOL
==================================================

`docs/GITHUB_PUBLICATION.md` is the specialist authority:

one logical change
        ↓
all blobs, one tree, one atomic commit
        ↓
exactly one remote branch created at the final commit
        ↓
one ready pull request
        ↓
one complete check set
        ↓
one squash merge
        ↓
automatic branch deletion and verification

The repository workflow `.github/workflows/cleanup-merged-branch.yml` deletes the
same-repository head branch associated with a new `main` commit. It is idempotent when
the branch has already been deleted by repository settings.

==================================================
PULL-REQUEST PROTOCOL
==================================================

Before opening a PR, inspect all workflows triggered by the event.

Patch `v0.3.2_2` title:

`v0.3.2_2: Prevent orphan publication branches`

Its squash subject is an ordinary logical subject, not `release: prepare v0.3.2`.

The release squash subject is reserved for an explicitly authorized new project version:

`release: prepare vX.Y.Z`

==================================================
ATOMIC API PUBLICATION
==================================================

For GitHub integration/API delivery:

1. Prepare all final content and modes without creating a branch.
2. Create one blob per changed file.
3. Create one tree based on current `main`.
4. Create one commit with current `main` as sole parent.
5. Validate the commit and recheck `main`.
6. Verify exact branch-name absence and cleanup availability.
7. Create exactly one branch at that commit.
8. Open one ready PR.

Never create preparatory sibling branches or stream a multi-file change through
sequential contents-API commits.

==================================================
RELEASE CONTROL
==================================================

Only an explicitly authorized new `VERSION` follows the release pipeline:

1. set the approved `VERSION`;
2. set `PLUGIN_REVISION=1`;
3. pass one atomic PR cycle;
4. squash merge as `release: prepare vX.Y.Z`;
5. let repository automation create the immutable tag and run release publication;
6. verify every public output before installation instructions.

Patch `v0.3.2_2` stops after ordinary merge, branch cleanup, and `main` verification.

==================================================
HISTORY RESPONSIBILITY
==================================================

Completed work belongs in `DEVLOG.md` or `docs/devlog/`. Decisions belong in
`DECISIONS.md` or `docs/decisions/`. Patch notes may be stored under `docs/patches/`.

# Patch v0.3.2_2 — GitHub branch hygiene

Date: 2026-08-03

Base commit:
`eb03d143546b57097a48aaf48bdf6a7a3ef98deb`

==================================================
SCOPE
==================================================

Prepare an ordinary package patch, not a project release.

Metadata:

- `VERSION=0.3.2`
- `PLUGIN_REVISION=2`
- package candidate `os-zapret2-restyle-0.3.2_2.pkg`
- no new tag;
- no GitHub Release;
- no release assets;
- no pkg-repository publication.

==================================================
REPOSITORY CHECK
==================================================

Read-only GitHub verification confirmed:

- all five accidental v0.3.2 preparation branches named in the owner cleanup command
  are absent;
- no pull request is open;
- `main` remains at the v0.3.2 release commit;
- historical branches not created by this cleanup remain untouched.

==================================================
IMPLEMENTED
==================================================

- Made one remote task branch the hard budget for one logical cycle.
- Moved branch creation after final blobs, tree, commit, validation, title, and cleanup
  preflight.
- Prohibited preparatory suffix branches.
- Added explicit package-patch versus project-release semantics.
- Added a `main` push workflow that resolves the associated merged same-repository PR
  and deletes its head branch idempotently.
- Added focused static contract coverage and CI integration.
- Corrected current state and roadmap from release preparation to published v0.3.2 plus
  patch candidate v0.3.2_2.
- Advanced package revision from 1 to 2 without changing `VERSION`.

==================================================
EXPECTED DELIVERY
==================================================

One final atomic commit is published through one branch and one ready PR. CI and the
FreeBSD package build run once. The squash merge uses the ordinary patch title, not a
release subject. The cleanup workflow then deletes that one task branch and the branch
list is checked for absence.

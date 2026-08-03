# DEC-2026-08-02 — Atomic GitHub publication, branch ownership, and release gates

Status: Approved and extended
Original date: 2026-08-02
Extended: 2026-08-03

## Decision

Every logical delivery cycle owns exactly one remote task branch.

The complete change is prepared before that branch exists:

1. all final blobs;
2. one tree;
3. one atomic commit based on recorded `main`;
4. validation of parent, scope, package candidate, title, branch name, and cleanup path;
5. exactly one branch creation at the final commit;
6. one ready pull request;
7. one complete check set;
8. one squash merge;
9. automatic branch deletion and absence verification.

Preparatory sibling branches such as `-clean`, `-final`, `-atomic`, `-fixed`,
`-retry`, and `-publish` are prohibited.

The repository workflow `.github/workflows/cleanup-merged-branch.yml` deletes the
same-repository PR head branch associated with a new `main` commit. It is idempotent
when repository settings already deleted the branch.

If a published cycle fails, its PR is closed and its branch is deleted before one clean
replacement cycle begins.

A package patch and a project release are separate operations:

- patch `vX.Y.Z_N` keeps `VERSION=X.Y.Z`, sets `PLUGIN_REVISION=N`, and stops
  after ordinary merge, cleanup, and `main` verification;
- a project release changes `VERSION`, requires explicit authority for that exact
  version, and may continue to immutable tag, GitHub Release, assets, and pkg repository.

Published versions remain forward-only and immutable.

## Reason

During v0.3.2 preparation, remote branches were created before the final atomic commit
was ready. Repeated attempts produced `release/v0.3.2`, `-clean`, `-final`, `-atomic`,
and `-publish` branches. Even after their refs were aligned with `main`, GitHub displayed
recent-push “Compare & pull request” banners and the owner had to delete them manually.

Git objects do not require branch refs during preparation. Delaying branch creation until
the final commit exists removes the cause of the clutter. Automatic merged-branch cleanup
removes the remaining normal task branch without owner action.

## Consequences

- One logical cycle calls branch creation once.
- Validation failure before branch creation leaves no remote branch.
- No sibling attempt branches are published.
- Cleanup capability is checked before branch creation.
- The merged task branch is deleted automatically and its absence is verified.
- Pre-existing owner branches are never included in broad cleanup.
- Patch requests do not accidentally trigger release automation.
- Patch `v0.3.2_2` keeps `VERSION=0.3.2` and advances only `PLUGIN_REVISION`.

## Current application

Verified absent:

- `release/v0.3.2`
- `release/v0.3.2-clean`
- `release/v0.3.2-final`
- `release/v0.3.2-atomic`
- `release/v0.3.2-publish`

No open pull request remained after cleanup.

## Affected documentation and controls

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/GITHUB_WORKFLOW.md`
- `docs/GITHUB_PUBLICATION.md`
- `docs/ROADMAP.md`
- `docs/devlog/DEVLOG-2026-08-03-PATCH-v0.3.2_2.md`
- `docs/patches/v0.3.2_2.md`
- `.github/workflows/cleanup-merged-branch.yml`
- `.github/workflows/ci.yml`
- `scripts/test-github-branch-hygiene.sh`
- `Makefile`

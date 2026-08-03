# GitHub publication discipline

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How must one logical change be delivered to GitHub without unnecessary branches,
commits, workflow runs, or manual cleanup?

Purpose:
Define the mandatory atomic branch, pull-request, check, merge, cleanup, patch, and
release procedure.

Updated when:
Delivery events, title protocols, branch lifecycle, patch semantics, release gates, or
publication verification change.

Read after:
The complete order in `docs/INDEX.md`, immediately before any GitHub mutation.

Do not store here:
Product requirements, runtime architecture, current task state, or release history.

==================================================
PERMANENT SEQUENCE
==================================================

one logical change
        ↓
complete code, tests, documentation, and modes without a remote task branch
        ↓
all blobs and one tree
        ↓
one atomic commit based on the recorded current `main`
        ↓
verify commit, title, branch name, cleanup path, and unchanged `main`
        ↓
create exactly one remote task branch at that final commit
        ↓
open one ready pull request
        ↓
one complete check set for the unchanged commit
        ↓
one squash merge
        ↓
automatic branch cleanup
        ↓
verify `main` and verify branch absence

The normal path does not use Draft → Ready or multiple remote preparation branches.

==================================================
REMOTE BRANCH BUDGET
==================================================

One logical delivery cycle has a budget of exactly one remote task branch.

Rules:

1. No remote branch is created during preparation.
2. Create blobs, the final tree, and the final atomic commit first.
3. Validate the commit and recheck `main`.
4. Verify the exact planned branch name is absent.
5. Verify a cleanup path exists:
   - repository automatic deletion;
   - `.github/workflows/cleanup-merged-branch.yml`; or
   - an authenticated transport that can delete the branch.
6. Create the branch once, directly at the final commit.
7. Never create sibling preparation branches such as `-clean`, `-final`, `-atomic`,
   `-fixed`, `-retry`, or `-publish`.
8. After merge, verify that the task branch no longer exists.

Unreferenced blobs, trees, and commits created before branch publication do not clutter
the branch list and are the correct preparation mechanism.

If preparation fails before branch creation, discard the unreferenced Git objects and
restart from current `main`. If failure occurs after branch publication, close the PR,
delete the branch, verify its absence, and only then start one clean replacement cycle.

Do not knowingly create a branch when the selected transport cannot clean it and
repository cleanup automation is unavailable.

==================================================
ATOMIC GITHUB/API PREPARATION
==================================================

For a multi-file change through the GitHub API:

1. Record the exact current `main` SHA.
2. Prepare every final file and Git mode.
3. Run focused validation and whitespace checks.
4. Create one blob for every changed file.
5. Create one tree based on the recorded `main` tree.
6. Create one commit whose sole parent is the recorded `main`.
7. Verify changed paths, parent, title protocol, and expected package candidate.
8. Re-read `main` and confirm it is unchanged.
9. Create exactly one remote task branch at the final commit.
10. Open one ready pull request.

Sequential contents-API commits, temporary workflow transport, and preparatory remote
branches are prohibited.

==================================================
PULL-REQUEST PREFLIGHT
==================================================

Before opening the pull request:

1. Read every workflow triggered by `pull_request`.
2. Derive the package candidate from `VERSION` and `PLUGIN_REVISION`.
3. Verify the branch contains one final atomic commit based on current `main`.
4. Verify the exact title before the `opened` event.
5. Confirm the branch will remain unchanged while checks run.

Title when revision is non-zero:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

A release squash subject is a different protocol field:

`release: prepare v<VERSION>`

==================================================
PATCH VERSUS RELEASE
==================================================

A package patch such as `v0.3.2_2` is not a project release.

Patch contract:

- keep `VERSION=0.3.2`;
- set `PLUGIN_REVISION=2`;
- use the ordinary package-candidate PR title;
- use an ordinary logical squash subject;
- do not create or move a tag;
- do not create a GitHub Release;
- do not publish release assets or a pkg repository;
- do not use `release: prepare ...`.

Release contract:

- requires explicit authority for an exact new `VERSION`;
- changes `VERSION`;
- resets `PLUGIN_REVISION` to `1`;
- uses the exact release squash subject;
- continues through tag, GitHub Release, assets, and Pages/pkg publication.

Ambiguous continuation language does not authorize a release.

==================================================
CHECK SET AND FAILURE
==================================================

Open one ready PR and start one check set for the unchanged final commit. Wait for the
complete result.

Do not edit the title, convert Draft/Ready, push repair commits, or repeatedly retrigger
checks merely to create another event.

A failed published cycle is replaced only after its PR is closed and its branch is
deleted and confirmed absent.

==================================================
MERGE AND CLEANUP
==================================================

After all required checks pass:

1. Verify mergeability and changed-file scope.
2. Squash merge once.
3. Use an ordinary package-candidate subject for a patch.
4. Use `release: prepare v<VERSION>` only for an authorized release.
5. Verify resulting `main`.
6. Let `.github/workflows/cleanup-merged-branch.yml` delete the associated same-repository
   head branch.
7. Query branches and verify absence of the exact task branch.

Cleanup failure is a delivery failure to diagnose. It is not a reason to create another
branch.

==================================================
RELEASE GATE
==================================================

Before changing `VERSION`, all answers must be yes:

1. Did the owner explicitly request this exact new version?
2. Are required implementation, CI, and live-verification gates complete?
3. Is owner acceptance recorded when required?
4. Does `PROJECT_STATE.md` authorize that release?
5. Will previous published versions remain unchanged?

If any answer is no, do not change `VERSION`, create a release branch, create a tag, or
dispatch a release workflow.

==================================================
POST-RELEASE VERIFICATION
==================================================

A release is not ready for installation until all are verified:

- expected `main` merge;
- tag at that exact commit;
- Release trigger success;
- Release workflow success;
- exact `.pkg` asset;
- `SHA256SUMS`;
- Pages deployment;
- `meta.conf`, `data.pkg`, and `packagesite.pkg`;
- exact version in the public pkg repository.

Patch publication to `main` does not imply any of these release outputs.

==================================================
CONCURRENCY AND SAFETY
==================================================

The recorded `main` SHA is the concurrency guard. If `main` changes before branch
creation, discard the prepared unreferenced commit, reconcile against new `main`, and
validate again.

Never force-update `main`, move a published tag, or delete a pre-existing owner branch.
Only the one task branch created by the current cycle is owned by the cycle.

==================================================
SPECIALIST AUTHORITY
==================================================

This document is the final authority for GitHub delivery mechanics. The active decision
is recorded in:

`docs/decisions/DEC-2026-08-02-atomic-github-publication.md`

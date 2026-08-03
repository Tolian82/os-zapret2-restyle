# GitHub publication discipline

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How must one logical change be delivered to GitHub without unnecessary commits,
workflow runs, failed protocol checks, or ambiguous repository state?

Purpose:
Define the mandatory atomic branch, pull-request, check, merge, and release-publication
procedure.

Updated when:
Delivery events, title protocols, check policy, release gates, or publication
verification change.

Read after:
The complete order in `docs/INDEX.md`, immediately before any GitHub mutation.

Do not store here:
Product requirements, runtime architecture, current task state, or release history.

==================================================
PERMANENT SEQUENCE
==================================================

one logical change
        ↓
complete code, tests, documentation, and file modes outside the published branch
        ↓
one atomic commit based on the recorded current `main`
        ↓
one ready pull request
        ↓
one complete check set for the unchanged final commit
        ↓
one squash merge
        ↓
verify `main`

The normal path does not use Draft → Ready. A pull request is opened only after the
final branch is ready. This prevents duplicate `opened`, `edited`, `synchronize`, and
`ready_for_review` check runs.

==================================================
DELIVERY STAGES
==================================================

Allowed current-stage values are:

- `DEVELOPMENT`
- `CI_PENDING`
- `LIVE_VERIFICATION_REQUIRED`
- `OWNER_ACCEPTANCE_REQUIRED`
- `RELEASE_AUTHORIZED`
- `RELEASE_IN_PROGRESS`
- `RELEASE_PUBLISHED`

`PROJECT_STATE.md` records the current stage. Work must not jump to a later stage.

Examples:

- `LIVE_VERIFICATION_REQUIRED` prohibits release preparation until evidence is
  recorded or the project owner explicitly confirms successful live verification.
- `OWNER_ACCEPTANCE_REQUIRED` prohibits choosing or publishing a release version.
- `RELEASE_AUTHORIZED` permits the complete named release path without repeated
  confirmations.

==================================================
REQUEST AND RELEASE AUTHORIZATION
==================================================

An ordinary request to fix, add, change, or implement authorizes the normal branch,
pull-request, CI, squash-merge, and `main` verification cycle.

A release requires an explicit project-owner request naming the version or
unambiguously referring to a version already approved in the current documented scope.
Phrases such as “continue”, “do it”, “let’s do this”, or “make it work” do not by
themselves authorize a release.

Never independently choose a new `VERSION` value.

Published history is forward-only and immutable:

- never move or recreate a published tag;
- never replace release assets under an existing version;
- never roll back `VERSION` to an earlier published value;
- never reuse a published version for different source;
- publish later work only under a higher explicitly approved version.

==================================================
ATOMIC GITHUB/API PREPARATION
==================================================

For a multi-file change through the GitHub API:

1. Record the exact current `main` commit SHA.
2. Prepare all final file contents and modes before publishing a task branch.
3. Run focused validation and whitespace checks.
4. Create one blob for every changed file.
5. Create one tree based on the recorded `main` tree.
6. Create one commit whose sole parent is the recorded `main` commit.
7. Re-read `main` and confirm it is unchanged.
8. Create or move the new task branch directly to that atomic commit.
9. Open one pull request.

Sequential contents-API commits are prohibited. Temporary workflow files, patch-part
transport, delivery-only trigger files, Actions self-modification, and experimental
commits are also prohibited.

If preparation fails before the pull request exists, abandon that unpublished branch
name and create a clean branch from the current `main`. Do not stream repairs into it.

==================================================
PULL-REQUEST PREFLIGHT
==================================================

Before creating the pull request:

1. Read every workflow triggered by `pull_request` and the relevant event types.
2. Derive the exact package candidate from `VERSION` and `PLUGIN_REVISION`.
3. Verify changed files, modes, base SHA, parent, and branch head.
4. Verify the title before the `opened` event is emitted.
5. Confirm the branch is final and will remain unchanged during checks.

Pull-request title when revision is non-zero:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

Example:

`v0.3.2_1: Improve GitHub publication discipline`

Release pull-request title and release squash subject are different protocol fields.

For release `v0.3.2`:

- pull-request title: `v0.3.2_1: Improve GitHub publication discipline`;
- squash subject on `main`: `release: prepare v0.3.2`.

Do not open a release pull request with `release: prepare ...` as its PR title when the
PR-title workflow requires the package-candidate prefix.

==================================================
CHECK SET
==================================================

Open the pull request as ready for review. Start the configured checks once for the
unchanged final commit. Wait until the complete set finishes before diagnosing any
failure.

Do not:

- edit the title after opening when it could have been computed beforehand;
- convert Draft/Ready merely to start another event;
- push repair commits while checks run;
- repeatedly rerun individual checks without correcting a proven transient platform
  failure;
- treat partial job success as a complete successful check set.

==================================================
FAILED DELIVERY CYCLE
==================================================

A failed pull-request cycle is replaced, not repaired:

1. Wait for every job in the check set to finish.
2. Diagnose the failure once.
3. Close the failed pull request without merging it.
4. Prepare the complete correction outside the published branch.
5. Re-read current `main`.
6. Create one new clean atomic commit, branch, pull request, and check set.

No repair commit, force-push, repeated title edit, or repeated event transition is used
to make a noisy pull request green.

==================================================
MERGE
==================================================

After all required checks pass for the exact final commit:

1. Verify mergeability and the complete changed-file scope.
2. Squash merge once.
3. For an ordinary change, retain the package-candidate logical title.
4. For a release preparation, use exactly `release: prepare v<VERSION>`.
5. Verify the resulting `main` SHA, message, tree, and expected files.
6. Delete only the temporary branch created for the completed task when the available
   transport supports safe branch deletion.

==================================================
RELEASE GATE
==================================================

Before changing `VERSION`, all answers must be yes:

1. Did the owner explicitly request this exact version?
2. Is the previous published version immutable and left unchanged?
3. Are required implementation, CI, and live-verification gates complete?
4. Is owner acceptance recorded when required?
5. Does `PROJECT_STATE.md` say `RELEASE_AUTHORIZED`?

If any answer is no, do not change `VERSION`, create a release branch, create a tag,
or dispatch a release workflow.

An explicit owner statement that a named package was tested and works is valid
owner-supplied live evidence. Record it honestly as owner verification, without
inventing commands or output that were not supplied.

==================================================
AUTHORIZED RELEASE PATH
==================================================

1. Prepare one atomic release commit from current `main`.
2. Set the explicitly approved `VERSION` and deterministic `PLUGIN_REVISION`.
3. Open one ready pull request with the exact package-candidate title.
4. Pass one complete check set.
5. Squash merge with `release: prepare v<VERSION>`.
6. Let `release-trigger.yml` create or verify the immutable tag at that merge.
7. Let `release.yml` build, verify, and publish the package and pkg repository.
8. Verify every distribution output before giving installation commands.

==================================================
POST-RELEASE VERIFICATION
==================================================

A release is not reported ready for installation until all are verified:

- `main` is the expected release merge;
- tag `v<VERSION>` resolves to that exact commit;
- Release trigger completed successfully;
- Release workflow completed successfully;
- GitHub Release exists;
- exact `.pkg` asset exists;
- `SHA256SUMS` exists;
- GitHub Pages deployment succeeded;
- `meta.conf`, `data.pkg`, and `packagesite.pkg` are published;
- the exact package version is present in the public pkg repository.

Only after these checks may user instructions contain `pkg update`, `pkg install`, or
`pkg upgrade` for the new release.

==================================================
CONCURRENCY AND SAFETY
==================================================

The recorded `main` SHA is the concurrency guard. If `main` changes before the atomic
commit is published, discard the prepared commit, reconcile against the new `main`, and
run validation again. Never force-update `main` or overwrite concurrent work.

Relevant owner changes that exist only in a local checkout remain a blocking exception
and must be committed, pushed, or transferred explicitly before remote preparation.

==================================================
SPECIALIST AUTHORITY
==================================================

This document is the final authority for GitHub delivery mechanics. The active decision
is recorded in:

`docs/decisions/DEC-2026-08-02-atomic-github-publication.md`

Historical Draft/Ready or incremental-repair wording elsewhere does not override this
current procedure.

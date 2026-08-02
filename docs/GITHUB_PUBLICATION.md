# GitHub publication discipline

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How must a logical change be delivered to GitHub without creating noisy or ambiguous repository state?

Purpose:
Define the mandatory atomic branch, commit, pull-request, check, and merge workflow.

Updated when:
The repository delivery process, pull-request naming convention, or check policy changes.

Read after:
`docs/INDEX.md` and the mandatory Engineering Memory sequence, immediately before any GitHub mutation.

Do not store here:
Product requirements, implementation architecture, release history, or current task status.

==================================================
PERMANENT RULE
==================================================

The permanent publication sequence is:

`one logical change -> one ready branch -> one atomic commit -> one pull request -> one complete check set -> one squash merge`

A GitHub branch is published only after the complete logical change is ready. Code, focused tests, documentation, file modes, and local checks are prepared before the branch exists on GitHub.

==================================================
REQUIRED ORDER
==================================================

1. Read the mandatory project documentation and the relevant source files.
2. Fetch the current official `main` state and record its exact full commit SHA.
3. Complete one logical change outside the pull-request branch.
4. Update every affected Engineering Memory document in the same logical change.
5. Run local syntax checks, focused regression tests, file-mode checks, and `git diff --check`.
6. Create one branch from the recorded `main` commit.
7. Publish the complete repository state as one atomic commit whose sole parent is the recorded `main` commit.
8. Open one pull request to `main`.
9. Leave the branch unchanged while checks are queued or running.
10. Evaluate the complete check set once.
11. After successful checks and review, squash merge the pull request.
12. Verify the resulting `main` commit before starting another logical change.

==================================================
PULL-REQUEST TITLE
==================================================

Every pull-request title begins with the exact package candidate represented by the branch.

The candidate is derived from:

- `VERSION`;
- `PLUGIN_REVISION` in `Makefile`.

When `PLUGIN_REVISION` is non-zero, the title format is:

`v<VERSION>_<PLUGIN_REVISION>: <logical change>`

Required example:

`v0.2.8_4: Add GUI Zapret2 service and release management`

When a branch advances the revision from `_4` to `_5`, its title must use `_5`. A title describing only the feature without the package candidate is invalid.

==================================================
FAILED CHECK OR DELIVERY CYCLE
==================================================

A failed pull-request cycle is not repaired incrementally.

1. Wait until the complete check set finishes.
2. Diagnose the failure once.
3. Close the failed pull request without merging it.
4. Prepare the correction outside GitHub.
5. Create a new clean branch from the current `main` commit.
6. Publish one new atomic commit and one new pull request.

Historical failed checks may remain visible. They do not affect `main` and must not be reused as evidence for the replacement pull request.

==================================================
PROHIBITED DELIVERY MECHANISMS
==================================================

The following are prohibited:

- temporary GitHub Actions workflows used to apply or generate the change;
- Actions-based self-modification of the repository;
- encoded patches or patch-part files committed as transport;
- delivery-only trigger files;
- sequential GitHub contents-API commits that stream an unfinished change;
- repeated changes to a pull-request branch while checks run;
- repeated manual check retriggers instead of correcting the cause;
- repair commits added to a failed delivery cycle;
- force-push repair of a published pull-request branch;
- merging a recovery, transport, experimental, or noisy pull request.

==================================================
CHECK SET AND MERGE
==================================================

A complete check set may contain several jobs, but it is started once for the unchanged final commit. All required jobs must finish successfully for that exact commit.

Final integration uses squash merge so `main` receives one logical commit. The squash title retains the exact package candidate and logical change description.

==================================================
REPOSITORY SAFETY
==================================================

`main` is never used as a staging area. Recovery branches and failed pull requests are closed and never merged. The exact final commit, package candidate, changed files, and check conclusions are verified before merge.

This document is the specialist authority for GitHub delivery discipline. The decision is recorded in `docs/decisions/DEC-2026-08-02-atomic-github-publication.md` and enforced at repository entry by `AGENTS.md`.

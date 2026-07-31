# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the project published and maintained on GitHub?

Purpose:
Define the official GitHub repository, authoritative development baseline,
atomic commit and publication procedure, optional branch/PR/patch modes, release
preparation, release assets, and publication verification.

Updated when:
The repository, branch policy, source-baseline rule, commit conventions,
publication procedure, release process, or release assets change.

Read after:
REQUIREMENTS.md

Do not store here:
General development procedures, architectural rationale, product requirements,
or a second development/publication history log.

==================================================
OFFICIAL REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
main

Direct publication to `main` is allowed only after explicit project-owner
instruction. A working branch, pull request, or patch is used when requested or
when validation must occur before `main` changes.

==================================================
AUTHORITATIVE DEVELOPMENT BASELINE
==================================================

The default authoritative baseline is an exact commit in this official GitHub
repository, normally the current `main` commit.

Before changing repository files:

1. Read the current `main`.
2. Record its full commit SHA.
3. Obtain all changed file content and Git file modes from that commit.
4. Confirm that no relevant project-owner state exists only in a local checkout.
5. Use the recorded SHA as the sole parent of the new logical commit.

No owner-supplied archive is required for state already committed and pushed to
GitHub. Model memory, chat excerpts, and standalone diffs are context only; they
are not substitutes for reading the recorded commit.

==================================================
LOCAL-ONLY STATE EXCEPTION
==================================================

GitHub cannot expose uncommitted or unpushed changes in
`/root/os-zapret2-restyle` on the project owner's OPNsense system.

If such state is relevant:

1. Stop before preparing the change.
2. Ask the owner to commit and push it, or explicitly transfer an archive or
   patch.
3. Record the resulting exact commit or transferred tree as the baseline.
4. Preserve its tracked modifications and file modes.
5. Never reconstruct, discard, or overwrite unpublished state from memory.

Backups of live configuration and runtime files outside the repository remain a
separate operational requirement.

==================================================
ATOMIC CHANGE PREPARATION
==================================================

Each logical change is one atomic commit.

The commit must contain:

- all required content changes;
- all required Git file-mode changes;
- every documentation update required by the synchronization rules;
- no unrelated work.

Before creating the commit:

1. Confirm the recorded base SHA.
2. Run `git diff --check` or equivalent whitespace validation.
3. Run the focused syntax or static tests required by the change.
4. Review the changed scope and diff.
5. Confirm that all affected documentation is synchronized.

An authenticated GitHub integration/API may create blobs, one tree, and one
commit atomically. Ordinary Git may also be used. GitHub CLI is not a mandatory
dependency.

==================================================
NORMAL VERIFICATION
==================================================

When a local checkout is used, normal Git verification is:

git status --short
git diff --check
git diff --stat

Review the complete `git diff` only when:

- performing a manual audit;
- investigating unexpected behaviour;
- reviewing a complex refactor;
- explicitly requested by the project owner.

Run the focused syntax and static tests required by the specific change before
commit. Package build and live OPNsense verification follow the published
logical commit unless an explicitly selected branch/PR workflow requires them
before `main` changes.

==================================================
COMMIT PROCEDURE
==================================================

Each commit must contain one logical change.

Before commit:

1. Confirm that the working source still derives from the recorded base SHA.
2. Confirm `git status --short` when a local checkout is used.
3. Confirm `git diff --check` or equivalent validation.
4. Run focused validation required by the change.
5. Confirm that all affected documentation is synchronized.
6. Stage explicit paths when using a local checkout.
7. Create one commit with the recorded base commit as its sole parent.

Commit messages must be concise, imperative, and describe the logical result.
Avoid vague messages such as `update`, `fix stuff`, or `changes`.

Example:

Docs: enforce context recovery workflow

==================================================
PUBLICATION MODES
==================================================

Direct `main` publication:

1. Require explicit project-owner instruction to publish directly to `main`.
2. Re-read `main` immediately before publication.
3. Confirm that `main` still equals the recorded base SHA.
4. Move `main` to the new commit as a fast-forward only.
5. Never use force-push.
6. Fetch or read the published commit and verify its SHA, parent, message, and
   changed files.

Working branch and pull request:

- Use when explicitly requested or when build/live validation must occur before
  `main` changes.
- The branch must start from the recorded base SHA.
- One logical change remains one commit unless the owner approves another review
  structure.
- Merging or deleting the branch requires separate authority when not already
  included in the request.

Unified patch:

- Use when explicitly requested or when GitHub does not contain relevant local
  state that is transferred separately.
- Generate the patch from the exact established baseline.
- Include content and file-mode changes.
- Require `git apply --check` against the unchanged baseline before delivery.

Creating a tag, release, package publication, force-push, or branch deletion is
never implied by permission to publish an ordinary commit.

Record completed meaningful publication work in `DEVLOG.md`. Do not create a
separate push log or publication history file.

==================================================
POST-PUBLICATION DEVELOPMENT CYCLE
==================================================

The normal cycle is:

one logical change
↓
one atomic commit
↓
one build
↓
one focused verification

If verification fails, record the result and correct it through a new logical
commit. Do not rewrite or force-update the published commit.

==================================================
RELEASE PREPARATION
==================================================

A release is prepared only from a committed and pushed source baseline.

Before publication:

1. Confirm the intended value in `VERSION`.
2. Confirm the package revision in `Makefile`.
3. Build the package from the committed baseline.
4. Run the release-package verification script directly.
5. Confirm package metadata and filename.
6. Complete focused package installation and runtime checks required for the
   release.
7. Update release-facing documentation when applicable.
8. Commit and publish every release-preparation change.
9. Create the GitHub Release from the intended commit/tag.
10. Attach the verified `.pkg` artifact.

Normal verification command:

./scripts/verify-release-package.sh dist/os-zapret2-restyle-<version>.pkg

==================================================
RELEASE ASSETS
==================================================

The release asset is the verified OPNsense package:

os-zapret2-restyle-<version>.pkg

Do not publish an unverified package or a package built from uncommitted source
changes.

Patch files used during development are delivery artifacts and are not release
assets unless the project owner explicitly chooses to publish one.

==================================================
RELEASE CHECKLIST
==================================================

- source baseline committed;
- source baseline published to `main`;
- `VERSION` correct;
- package revision correct;
- documentation synchronized;
- package built successfully;
- verification script succeeds when invoked directly;
- package metadata correct;
- focused installation/runtime checks completed;
- release tag points to the intended commit;
- verified `.pkg` attached;
- completed release work recorded in `DEVLOG.md`.

==================================================
HISTORY RESPONSIBILITY
==================================================

`DEVLOG.md` is the single project history log.

This document defines procedure only. It must not accumulate a chronological
list of pushes, releases, or publication events.

==================================================
CONCURRENCY AND REF SAFETY
==================================================

The recorded base SHA is also the concurrency guard.

If `main` changes after work begins:

1. Do not move the branch reference.
2. Fetch and inspect the new `main`.
3. Reconcile the logical change against the new baseline.
4. Re-run validation.
5. Create a new commit with the new base as parent.

Never overwrite concurrent work and never set `force: true` for normal
publication.

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

Ordinary requested development uses a working branch and pull request. Direct
publication to `main` is allowed only after explicit project-owner instruction.
An explicitly requested patch or narrower stopping point overrides the default.

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
STANDING AUTHORIZATION AND REQUEST BOUNDARIES
==================================================

For an ordinary request to fix, add, change, implement, or complete project work,
the project owner grants standing authority for this complete delivery path:

recorded `main` base
        ↓
working branch
        ↓
one atomic commit
        ↓
Draft PR
        ↓
required CI
        ↓
Ready for review
        ↓
squash merge
        ↓
verify `main`
        ↓
delete the temporary branch created for the task

Do not request separate confirmation for any step in that ordinary path. Choose
routine branch, commit, PR, and focused-test details from the current repository,
Finding or work-package scope, and project documentation.

The owner's explicit current wording sets a narrower boundary when it asks only
for analysis, diagnosis, review, preparation, a patch, a branch, or a PR. Stop at
that boundary.

One explicit request to make a release authorizes the full verified release path
for that requested version, including the release-preparation PR and merge, tag,
GitHub Release, package assets, GitHub Pages/pkg repository publication, and final
checks. An ordinary development request does not authorize release publication.

Stop for owner direction only when:

- materially different product or architecture choices are unresolved;
- relevant owner changes exist only in an unpublished local checkout;
- required CI, build, or verification fails and cannot be repaired within scope;
- new credentials, protected-environment approval, or external authority is needed;
- a destructive operation affects user data or a pre-existing owner branch, tag,
  release, package, or repository history;
- force-push, history rewriting, or direct publication to `main` is proposed;
- mandatory live OPNsense evidence can be supplied only by the owner.

When a boundary requires owner input, ask one consolidated question with the
relevant evidence and a recommended choice. Do not ask for information available
from the repository, GitHub, CI, documentation, or read-only diagnostics.

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

Publication transport is selected from the capabilities available in the current
environment, in this order:

1. authenticated GitHub integration/API;
2. ordinary Git using an already configured authenticated remote;
3. GitHub CLI when it is installed and authenticated.

Before declaring publication blocked, inspect the available GitHub integration
operations and the configured Git remote. The absence of one client, including
`gh`, is not a blocker while another approved authenticated transport can complete
the operation. Do not ask the project owner to choose the transport or install an
optional client when the current environment already exposes a safe path.

For integration/API publication of a multi-file change:

1. create one blob for every changed file and preserve its Git mode;
2. create one tree based on the recorded `main` tree;
3. create one commit whose sole parent is the recorded base SHA;
4. re-read `main` and confirm that it still equals that base;
5. create the task branch at the new commit;
6. open the Draft PR and continue through CI, Ready, squash merge, and verification.

Do not stop after local preparation and describe the branch, commit, PR, CI build,
or package artifact as "not created" merely because a preferred client is absent.
Stop only when every approved transport has been checked and a standing escalation
boundary actually applies.

An integration-created commit may have a different commit SHA than an equivalent
local commit because its author, committer, timestamp, or message metadata differs.
No owner confirmation is required when the parent is the recorded base and the
complete Git tree, file modes, and intended changed scope are identical. Verify
those facts before publishing the branch or merging the PR.

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

Default ordinary patch publication:

1. Create a task-specific working branch from the recorded base SHA.
2. Publish one atomic logical commit.
3. Open a Draft PR with the expected base and head branches.
4. Verify changed files, scope, parent/base relationship, and mergeability.
5. Wait for required CI. If Draft state prevents check registration, mark the PR
   Ready so the configured workflow can run.
6. Correct same-scope CI failures safely and re-run the required checks. If the
   branch is already published, add a correction commit rather than force-pushing;
   the later squash merge preserves one logical `main` commit.
7. After required checks pass, squash merge without a separate confirmation.
8. Verify the resulting `main` commit and expected tree.
9. Delete only the temporary branch created for this completed task. Never infer
   authority to delete a pre-existing owner branch.

The ordinary publication cycle is incomplete until the merged `main` commit has
been verified. A successful local patch or local test result is preparation, not
publication. The CI package artifact is part of the required build verification;
tag, GitHub Release, and pkg-repository publication additionally require release
authority.

Direct `main` publication:

1. Require explicit project-owner instruction to publish directly to `main`.
2. Re-read `main` immediately before publication.
3. Confirm that `main` still equals the recorded base SHA.
4. Move `main` to the new commit as a fast-forward only.
5. Never use force-push.
6. Fetch or read the published commit and verify its SHA, parent, message, and
   changed files.

Working branch and pull request:

- This is the default mode for ordinary requested development work.
- The branch must start from the recorded base SHA.
- One logical change remains one commit unless the owner approves another review
  structure.
- Required CI and any explicitly required pre-merge live validation must pass.
- Standing authority covers Ready transition, squash merge, and deletion of the
  temporary branch created for the completed task.
- A request to stop at the branch or PR boundary suppresses automatic merge.

Unified patch:

- Use when explicitly requested or when GitHub does not contain relevant local
  state that is transferred separately.
- Generate the patch from the exact established baseline.
- Include content and file-mode changes.
- Require `git apply --check` against the unchanged baseline before delivery.

Creating a tag, release, or package/pkg-repository publication is authorized only
by an explicit release request. Force-push and history rewriting are never implied.
Branch cleanup authority applies only to the temporary task branch created by this
workflow after its verified merge.

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

One explicit request to make the release is sufficient authority for all numbered
steps below. Do not pause for repeated confirmations between a successful
release-preparation merge, tag creation, GitHub Release publication, package asset
publication, Pages/pkg repository deployment, and final verification. Stop only on
one of the standing escalation boundaries above.

Package metadata handling does not require a separate confirmation when determined
by scope: increment `PLUGIN_REVISION` once for an ordinary packaged change while
`VERSION` is unchanged; reset it to `1` for an explicitly requested new project
version; change neither value for governance/documentation-only work outside package
contents. Standard CI may still build the unchanged package as its verification job.

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

# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the project published and maintained on GitHub?

Purpose:
Define the official GitHub repository, branch, patch-based change delivery,
commit and push procedure, release preparation, release assets, and publication
verification.

Updated when:
The repository, branch policy, patch workflow, commit conventions, push
procedure, release process, or release assets change.

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

Normal completed work is committed and pushed directly to `main` after the
required checks. A different branch workflow is used only when explicitly
approved for a specific change.

==================================================
MANDATORY PATCH DELIVERY
==================================================

Tracked repository files are changed only through an actual reviewable unified
Git patch supplied as a `.patch` artifact.

The normal artifact must:

- be suitable for `git apply`;
- include every required content change;
- include required Git file-mode changes;
- represent one logical change;
- include synchronized documentation;
- be prepared against the exact supplied working-tree baseline.

A prose plan, promise to prepare a patch later, replacement script, or manual
editing instructions are not substitutes for the `.patch` artifact.

Application sequence:

cd /root/os-zapret2-restyle && \
git status --short && \
git apply --check /path/to/change.patch && \
git apply /path/to/change.patch && \
git status --short && \
git diff --check

==================================================
NORMAL VERIFICATION
==================================================

Normal verification after patch application is:

git status --short
git diff --check

Review the complete `git diff` only when:

- performing a manual audit;
- investigating unexpected behaviour;
- reviewing a complex refactor;
- explicitly requested by the project owner.

Run additional syntax, package, runtime, or live tests required by the specific
change before commit.

==================================================
COMMIT PROCEDURE
==================================================

Each commit must contain one logical change.

Before commit:

1. Confirm that the patch applied successfully.
2. Confirm `git status --short`.
3. Confirm `git diff --check`.
4. Run focused validation required by the change.
5. Confirm that all affected documentation is synchronized.
6. Stage explicit paths.

Commit messages must be concise, imperative, and describe the logical result.
Avoid vague messages such as `update`, `fix stuff`, or `changes`.

Example:

Docs: enforce context recovery workflow

==================================================
PUSH PROCEDURE
==================================================

After a successful commit:

cd /root/os-zapret2-restyle && \
git status --short && \
git log -1 --oneline && \
git push origin main

The working tree must be clean unless a deliberately separate uncommitted change
has been explicitly identified.

Record completed meaningful publication work in `DEVLOG.md`. Do not create a
separate push log or publication history file.

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
8. Commit and push every release-preparation change.
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
- source baseline pushed to `main`;
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
AUTHORITATIVE PATCH BASELINE
==================================================

After a logical change is fully agreed, the project owner supplies an archive of
the actual working tree named:

`os-zapret2-restyle-<short_commit_sha>.tar.gz`

That archive, including its tracked modifications and Git file modes, is the only
authoritative base for preparing the next multi-file patch. Do not reconstruct
the baseline from GitHub, model memory, chat fragments, or a standalone diff.

Before delivery, test the generated patch with `git apply --check` against an
unchanged extraction of the supplied archive. After the resulting change is
committed, the archive is obsolete; a new archive from the new commit becomes the
baseline for the next patch.

# AGENTS.md

This repository uses a mandatory risk-based documentation and GitHub preflight.

Before project work:

1. Read this file, `docs/INDEX.md`, and `docs/PROJECT_STATE.md`.
2. Read the specialist documents relevant to the requested scope.
3. Read `docs/GITHUB_PUBLICATION.md` immediately before any GitHub mutation.
4. For GitHub work, also read
   `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`.
5. Treat the project owner's current instruction as the highest scope boundary.
6. Use current repository and GitHub state; chat history is supporting context only.

A complete read of every audit, decision, devlog, architecture, roadmap, and requirement
file is required only for a repository-wide audit or genuine full-context recovery. It is
not a blocking prerequisite for every diagnosis, command, or small change.

==================================================
GITHUB DELIVERY AUTHORITY
==================================================

Authority order for GitHub work:

1. current owner instruction;
2. this file;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
5. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
6. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
7. `docs/GITHUB_WORKFLOW.md`.

The evidence-first decision supersedes conflicting historical or active wording that
requires mandatory Draft PRs, exactly one branch commit, full-document rereading for
every operation, unversioned release-preparation titles, replacement publication
branches, or source changes in response to an external GitHub failure.

==================================================
PRE-MUTATION INVENTORY
==================================================

Before creating or changing a branch, PR, workflow, tag, release, or asset, inspect:

- exact `main` SHA and current `VERSION` / `PLUGIN_REVISION`;
- relevant PRs and branches;
- existing workflows capable of the operation;
- active, queued, failed, and successful runs;
- reusable artifacts, tags, releases, and assets;
- actual connector/API/Git/`gh` capabilities and permissions.

Do not invent a new mechanism until this inventory proves that the existing mechanisms
cannot safely complete the operation.

==================================================
ORDINARY DELIVERY RULES
==================================================

Default ordinary delivery:

one logical change
        ↓
one task branch and one Ready pull request
        ↓
focused validation
        ↓
required checks for the latest PR state
        ↓
one squash merge into `main` using the expected head SHA
        ↓
verify `main` and clean the temporary branch

Rules:

- Keep one logical scope per pull request.
- A PR branch may contain multiple same-scope work or repair commits.
- Same-scope failures are corrected in the same branch and PR.
- Draft is optional and reserved for intentional work in progress.
- Every PR title, every PR-branch commit subject, and the final squash subject must
  begin with the exact current package-candidate prefix `v<VERSION>_<REVISION>:`.
- Governance/documentation/CI-only changes do not change package metadata.
- Required CI gates the latest mergeable head, not every historical run.
- Independent analysis may continue while CI runs; unrelated work is not added to the
  checked branch.
- Never force-update `main`, move a published tag, or rewrite published history.

==================================================
PRERELEASE PUBLICATION RULES
==================================================

Publishing an already verified candidate is a release operation, not a code PR.

- Exact owner authorization is required for the candidate tag and asset.
- Prefer direct Release API/UI/`gh` upload when verified package bytes already exist.
- Reuse an Actions artifact only by exact run ID, artifact ID/name, and digest, and
  recheck its `+MANIFEST` before publication.
- Use `.github/workflows/publish-prerelease.yml` only when repository-owned build and
  publication automation is needed.
- Permit only one active publication run per candidate.
- A temporary `publish/v<VERSION>_<REVISION>` branch does not receive a PR.
- A testing prerelease publishes neither GitHub Pages nor the pkg repository.
- Verify target SHA, tag, draft/prerelease flags, asset name, and direct URL.
- Delete the temporary publication branch after success.

==================================================
FAILURE HANDLING
==================================================

Read the exact failed job log before changing source, workflow, runner, or branch.

- A confirmed same-scope source defect is repaired in the same PR.
- An external GitHub, runner, network, or action-distribution failure causes zero source
  changes and permits at most one unchanged rerun after recovery.
- Do not switch runner operating systems, create `-final`/`-retry` sibling branches, or
  add replacement workflows without evidence that the current workflow is defective.
- A second unchanged infrastructure failure stops the operation for diagnosis.
- Scheduled monitoring must be unique and bounded. Duplicate trackers and unbounded
  automatic retries are forbidden.

==================================================
REQUEST SCOPE AND AUTHORIZATION
==================================================

- analyse, diagnose, explain, review, audit: inspect and report; do not mutate;
- patch only, branch only, PR only: stop at the named boundary;
- fix, add, change, implement, complete: perform the ordinary branch → Ready PR →
  checks → squash merge → verification cycle;
- publish candidate `vX.Y.Z_N`: publish only that authorized testing prerelease and
  asset, without Pages/pkg-repository promotion;
- release version `X.Y.Z`: perform the authorized full stable release pipeline for that
  exact version and its existing product gates.

Do not ask for routine branch names, commit wording, PR text, CI inspection, same-scope
repair, squash merge, or cleanup after the owner has authorized the ordinary cycle.
Stop for owner input only on material product ambiguity, relevant unpublished owner
state, unavailable credentials/protected authority, destructive changes to user data or
pre-existing remote objects, history rewriting/direct-main publication, an unresolvable
required-check failure, or mandatory live OPNsense evidence available only from the
owner.

==================================================
PATCH AND RELEASE BOUNDARY
==================================================

- Ordinary packaged change: keep `VERSION`, increment `PLUGIN_REVISION` once, no tag or
  publication unless separately authorized.
- Governance/documentation/CI-only change: change neither value.
- Testing prerelease: explicit authorization for exact `v<VERSION>_<REVISION>`; no
  GitHub Pages or pkg repository.
- Full project release: change `VERSION`, reset revision to `1`, and use the versioned
  release-preparation subject `vX.Y.Z_1: Prepare release vX.Y.Z`.
- Published tags, releases, assets, and versions are immutable and forward-only.

==================================================
OPNSENSE COMMAND RULE
==================================================

OPNsense console commands target the default root `csh` shell. POSIX-only syntax must be
placed between an explicit standalone `sh` command and a matching standalone `exit`.

MANDATORY: Use the connected GitHub plugin first for every repository operation; use another transport only when the plugin lacks the required function or confirmed permission.

Known connector state and stop rule (re-verify before relying on time-sensitive details):

- At the 2026-08-07 verification, the repository returned no configured rulesets.
- The connected GitHub plugin can read and change repository objects, but its current
  installation receives `403 Resource not accessible by integration` when reading the
  repository Actions-permission settings and branch-protection settings. This is a
  connector permission boundary; it is not evidence that Actions or branch protection
  are disabled.
- When the plugin responds and only one exact function or permission is missing, a
  fallback is allowed only for that operation under the rules below.
- If the GitHub plugin stops responding, is unavailable, or cannot provide the
  authoritative repository state required to proceed, stop all GitHub work. Do not
  silently continue through local Git, `gh`, raw API calls, the web UI, an automation,
  or a scheduled tracker. Inform the project owner and wait for explicit direction.

# GitHub publication and delivery discipline

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How are code changes, testing prereleases, and full releases delivered through GitHub?

Purpose:
Define the authoritative preflight, branch, PR, CI, failure, merge, candidate-publication,
release, verification, and cleanup procedure.

Read immediately before any GitHub mutation.

Active decisions:

- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

==================================================
GITHUB PLUGIN FIRST
==================================================

For every repository operation, invoke and use the connected GitHub plugin before any
other repository transport. This includes repository discovery, current-state reads,
branches, commits, pull requests, reviews, checks, workflow metadata, artifacts, merges,
and cleanup when the plugin exposes the operation.

A fallback to local `git`, `gh`, raw API calls, web UI, or another transport is permitted
only when the plugin is available and the exact required plugin function or permission
has been checked and found unavailable or insufficient. The fallback covers only that
missing operation; it does not replace the plugin for the rest of the task.

Plugin unavailability is different from a missing function. If the plugin does not
respond, is unavailable, or cannot read the authoritative state needed for safe work,
stop all GitHub operations, inform the project owner, and wait for explicit direction.
Do not use a fallback transport merely to continue progress while the plugin is down.

Never diagnose current GitHub state from chat history, cached assumptions, local files,
or general web search when the connected plugin can read the authoritative repository
object directly.

==================================================
PRE-MUTATION INVENTORY
==================================================

Before creating or changing any branch, PR, workflow, tag, release, or asset, record:

- exact current `main` SHA;
- current `VERSION`, `PLUGIN_REVISION`, and required title prefix;
- relevant open and closed PRs;
- task, publication, recovery, and owner branches;
- existing workflows capable of the requested operation;
- active, queued, failed, canceled, and successful workflow runs;
- reusable artifacts with run ID, artifact ID/name, expiry, and digest;
- existing tags, releases, and assets;
- actual GitHub-plugin functions and permissions, followed only when needed by fallback
  connector/API/Git/`gh` capabilities.

Do not introduce a new workflow, runner, branch, PR, or transport until this inventory
proves that the existing safe mechanism is insufficient.

==================================================
PACKAGE-CANDIDATE IDENTITY
==================================================

Derive identity from the proposed head:

- `VERSION` supplies the semantic version;
- `Makefile` supplies `PLUGIN_REVISION`;
- non-zero revision prefix: `v<VERSION>_<PLUGIN_REVISION>:`;
- zero revision prefix: `v<VERSION>:`.

The exact prefix applies to every PR title, every PR-branch commit subject, and every
final squash subject, including governance, documentation, CI, maintenance, package,
and release-preparation changes.

Governance/documentation/CI-only work changes neither version value.

==================================================
ORDINARY DEVELOPMENT FLOW
==================================================

1. Resolve the exact owner instruction and stopping boundary.
2. Complete the risk-based context preflight from `AGENTS.md` and `docs/INDEX.md`.
3. Perform the GitHub-plugin-first capability check and pre-mutation inventory above.
4. Record exact base SHA, logical scope, affected documents, and verification plan.
5. Prepare one reviewable logical change.
6. Run focused validation and review the complete diff.
7. Publish one task branch and one Ready PR. Use Draft only for intentional work in
   progress or early design discussion.
8. Keep same-scope repairs in the same branch and PR.
9. Require successful checks for the latest mergeable PR head.
10. Before merge, verify scope, title prefix, mergeability, checks, and expected head SHA.
11. Squash merge once using the exact versioned subject.
12. Verify the resulting `main` commit and clean the task branch.

A PR branch may contain multiple same-scope commits. Permanent `main` history receives
one logical squash commit. Historical workflow-run count is not a correctness metric.

==================================================
CI AND FAILURE CLASSIFICATION
==================================================

Read the exact job log before changing source, workflow, runner, or branch.

Classify the failure:

1. Same-scope source, documentation, title, or test defect:
   repair in the same PR and validate the new head.
2. External GitHub, hosted-runner, network, action-distribution, or dependency outage:
   make zero source changes; after recovery, allow at most one unchanged failed-job or
   workflow rerun.
3. Incorrect PR metadata:
   correct metadata without creating a replacement branch.
4. Wrong base, mixed scope, damaged history, or abandoned approach:
   replace the PR only after recording the evidence.
5. Missing protected authority or credentials:
   stop at the exact boundary and report it once.
6. GitHub plugin unavailable or non-responsive:
   stop all GitHub work, inform the project owner, and wait for explicit direction.

Forbidden reactions to an unproven or external failure:

- speculative runner operating-system changes;
- `-clean`, `-final`, `-fixed`, `-retry`, or sibling publication branches;
- new version-specific workflows;
- repeated push-trigger experiments;
- duplicate scheduled trackers;
- unbounded automatic retries;
- automatic transport switching while the GitHub plugin is unavailable.

A second unchanged infrastructure failure stops the operation for diagnosis. It does
not authorize another retry or redesign.

==================================================
TESTING PRERELEASE PUBLICATION
==================================================

A testing prerelease exposes one already approved package candidate for live validation.
It is not a stable project release and is not an ordinary code PR.

Required authority:

- explicit owner authorization for the exact tag `v<VERSION>_<REVISION>` and asset;
- no implied permission to publish GitHub Pages or the pkg repository.

Preferred path when verified package bytes already exist:

1. identify the source commit and successful package build through the GitHub plugin;
2. bind the artifact by exact workflow run ID, artifact ID/name, and digest;
3. download the artifact once;
4. verify the package `+MANIFEST`:
   - exact package version;
   - `abi: FreeBSD:15:amd64`;
   - `arch: freebsd:15:x86:64`;
5. create the prerelease directly through the plugin when supported, otherwise use the
   narrow Release API/UI/`gh` fallback for the missing release-asset write;
6. attach only the verified `.pkg` asset;
7. verify target SHA, tag, `draft=false`, `prerelease=true`, asset name, state, digest or
   size, and direct download URL through the GitHub plugin.

Do not create a PR merely to attach an existing package asset.

When a repository-owned build-and-publish operation is actually required, create only
the exact temporary branch `publish/v<VERSION>_<REVISION>`. The single generic
`.github/workflows/publish-prerelease.yml` validates branch identity, builds on FreeBSD
15, checks `+MANIFEST`, creates only a prerelease, verifies it, and deletes the temporary
branch. Only one active run is permitted for the candidate.

A testing prerelease never deploys GitHub Pages or pkg-repository metadata.

==================================================
FULL PROJECT RELEASE
==================================================

A full release is separate from an ordinary patch and a testing prerelease.

Required conditions:

- explicit authority for exact new `VERSION=X.Y.Z`;
- product and live-verification gates satisfied;
- `PLUGIN_REVISION=1`;
- release-preparation PR and squash subject:
  `vX.Y.Z_1: Prepare release vX.Y.Z`;
- immutable semantic tag `vX.Y.Z` created at the verified merge commit;
- full Release workflow builds package and pkg repository from that tag;
- GitHub Release, GitHub Pages, pkg metadata, assets, and direct URLs are verified.

Published tags, releases, assets, and versions are immutable and forward-only.

==================================================
TRANSPORT SELECTION
==================================================

Transport order is mandatory while the GitHub plugin is available:

1. connected GitHub plugin for every supported read and write;
2. authenticated ordinary Git for local editing or ref operations that the plugin does
   not support;
3. `gh` for Actions or release operations not covered by the plugin;
4. Git data API for an atomic multi-file commit only when no checkout-based transport is
   available;
5. GitHub web UI only for a narrow operation that the authenticated tools cannot perform,
   such as owner asset upload.

Missing one fallback client is not a blocker while the GitHub plugin or another verified
mechanism covers the operation. Never claim a plugin capability or gap without checking
the actual function and permission first. If the plugin itself is unavailable, this
transport order is suspended and the work stops pending owner direction.

==================================================
MERGE AND CLEANUP
==================================================

Before merge compare:

- derived package-candidate prefix;
- PR title prefix;
- intended squash subject;
- exact expected head SHA;
- required-check state.

Use squash merge once. Never force-update `main`.

Temporary task and publication branches are deleted after successful verification.
`recovery/base` and pre-existing owner branches are not removed without separate
evidence and authority. Cleanup failure is a repository-hygiene defect, not evidence
that a verified merge or release failed.

==================================================
PATCH VERSUS PUBLICATION
==================================================

Ordinary packaged patch:

- keep `VERSION`;
- increment `PLUGIN_REVISION` once;
- merge through the normal PR path;
- create no tag, Release, asset, Pages deployment, or pkg-repository publication without
  separate authority.

Governance/documentation/CI-only patch:

- change neither version value;
- use the unchanged candidate prefix;
- run path-applicable CI;
- do not imply package publication.

Testing prerelease:

- explicit authority for exact `v<VERSION>_<REVISION>`;
- publish one verified package asset only;
- no Pages/pkg repository.

Full release:

- exact new `VERSION` authority;
- revision reset to `1`;
- versioned release-preparation title;
- full immutable tag/Release/Pages/pkg-repository pipeline.

==================================================
SUPERSESSION
==================================================

This document and the active decisions listed at the top supersede conflicting wording
that requires:

- using chat history, generic web search, local state, or another transport before the
  connected GitHub plugin for an operation the plugin supports;
- continuing GitHub work through another transport when the plugin itself is unavailable;
- mandatory Draft PRs;
- exactly one commit in a PR branch;
- exactly one historical workflow run;
- closing a valid PR after an ordinary same-scope failure;
- stopping independent analysis while CI runs;
- full-document rereading for every small operation;
- unversioned governance or release-preparation subjects;
- version-specific prerelease workflows in `main`;
- source/workflow/runner changes in response to an external infrastructure failure;
- publication PRs for already verified assets.

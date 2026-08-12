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
How are code changes, owner testing packages, testing-package publications, and full
project releases delivered through GitHub?

Purpose:
Define the authoritative preflight, branch, PR, CI, failure, merge, package-delivery,
release, verification, and cleanup procedure.

Read this document **completely through EOF** immediately before any GitHub mutation.
If a tool response is truncated, paginated, clamped, or range-limited, continue reading
remaining ranges until EOF before acting.

Active decisions:

- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- `docs/decisions/DEC-2026-08-07-installable-patch-shorthand.md`;
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
REQUIRED-DOCUMENT COMPLETION
==================================================

Opening a required file is not enough. Before action, every file required by `AGENTS.md`,
`docs/INDEX.md`, or the specialist scope must be consumed from first line through EOF.

- If the connector/tool returns only a prefix, continue with explicit line ranges.
- If the response is paginated or clamped, continue until no unread content remains.
- Do not infer unread rules from chat memory or previous summaries.
- If a required authority cannot be read completely, stop before mutation or package
  delivery and report the boundary.

This requirement is about completing the selected required reading set. It does not
restore the obsolete rule that every historical project document must be reread for each
small task.

==================================================
PRE-MUTATION INVENTORY
==================================================

Before creating or changing any branch, PR, workflow, tag, testing-package publication,
release, or asset, record:

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
2. Complete the risk-based context preflight from `AGENTS.md` and `docs/INDEX.md`, reading
   every required document through EOF.
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
GITHUB-ONLY OWNER PACKAGE DELIVERY
==================================================

For this project, **every owner-facing package is delivered persistently from GitHub**.
This rule is broader than the older installable-patch phrase list.

Any owner instruction that asks to build, make, give, publish, install, or test a package
or patch — including obvious Russian wording such as:

- `пакет`;
- `пакет для тестирования`;
- `тестовый пакет`;
- `дай пакет`;
- `собери пакет`;
- `патч`;
- `патч для установки`;
- `дай ссылку/команду для установки`;

means: complete the deterministic testing-package publication and provide a persistent
direct GitHub `.pkg` URL or OPNsense installation command.

The package request itself is publication authority for that deterministic testing
candidate. Do **not** ask for an additional confirmation solely because GitHub's storage
mechanism uses a prerelease/tag object.

### What does not count as package delivery

The following are build evidence or temporary transport, not completion:

- a GitHub Actions artifact ZIP;
- an Actions artifact download procedure or token workflow;
- a local/container/sandbox `.pkg` link;
- any temporary file that is not persistently hosted by this GitHub repository.

Actions artifacts may be used as verified inputs to publication. Bind them by exact run
ID, artifact ID/name, digest and manifest. They are never the final package handed to the
owner unless the owner explicitly asks for **build/CI evidence only and no package
delivery**.

If CI has built a package but it has not yet been persistently published, document the
state as:

`BUILD ARTIFACT READY / GITHUB PACKAGE PUBLICATION PENDING`

Do not call that state `PACKAGE READY FOR OWNER TESTING`.

### “Not a release, a package”

Owner wording such as `не релиз, а пакет` means no stable/full project release:

- keep semantic `VERSION` unless the package change itself requires otherwise;
- do not run the stable release pipeline;
- do not publish GitHub Pages;
- do not promote the pkg repository.

It **does not** mean stop at an Actions artifact. Persist the requested testing `.pkg` on
GitHub. The technical GitHub prerelease/tag used as the package container is a testing
package publication mechanism, not a semantic/full project release.

==================================================
INSTALLABLE PATCH SHORTHAND
==================================================

`DEC-2026-08-07-installable-patch-shorthand.md` remains the mechanical one-command
installation rule, but `DEC-2026-08-13-github-only-package-delivery.md` broadens its
trigger. It is no longer necessary for the owner to use one of a small exact phrase set.
Any package-delivery request covered above triggers the same publication behavior.

Candidate selection is deterministic:

1. Read current `main`, `VERSION`, and `PLUGIN_REVISION` through the GitHub plugin.
2. If the current package candidate has not yet been published and already contains all
   requested packaged changes, publish that exact candidate.
3. If additional packaged changes are required, increment `PLUGIN_REVISION` once through
   the normal PR/CI/squash path and publish the resulting candidate.
4. A documentation/governance-only clarification does not itself force another package
   revision; publication must still target the latest complete package tree.

The package request authorizes exactly:

- the testing-package tag `v<VERSION>_<REVISION>` derived by the rule above;
- one verified asset `os-zapret2-restyle-<VERSION>_<REVISION>.pkg`;
- the repository-owned FreeBSD 15 build-and-publish mechanism as needed;
- verification of the resulting GitHub package asset and direct URL.

It does not authorize a stable release, a semantic `VERSION` change, GitHub Pages,
pkg-repository promotion, unrelated source changes, or rewriting an existing published
candidate.

Normal user-facing result:

`pkg add -f https://github.com/Tolian82/os-zapret2-restyle/releases/download/v<VERSION>_<REVISION>/os-zapret2-restyle-<VERSION>_<REVISION>.pkg`

Only add extra installation detail when it is materially required by an observed error
or the owner explicitly requests it.

==================================================
TESTING PACKAGE PUBLICATION
==================================================

A testing package publication exposes one already approved package candidate for owner
live validation. It is not a stable/full project release and is not an ordinary code PR.

Required authority:

- any owner package-delivery request covered by the GitHub-only package rule above; or
- an explicit instruction for the exact testing candidate/tag and asset;
- no implied permission to publish GitHub Pages or the pkg repository.

Preferred path when verified package bytes already exist:

1. identify the source commit and successful package build through the GitHub plugin;
2. bind the artifact by exact workflow run ID, artifact ID/name, and digest;
3. download the artifact once;
4. verify the package `+MANIFEST`:
   - exact package version;
   - `abi: FreeBSD:15:amd64`;
   - `arch: freebsd:15:x86:64`;
5. create the GitHub testing-package prerelease directly through the plugin when
   supported, otherwise use the narrow Release API/UI/`gh` fallback for the missing
   release-asset write;
6. attach only the verified `.pkg` asset;
7. verify target SHA, tag, `draft=false`, `prerelease=true`, asset name, state, digest or
   size, and direct download URL through the GitHub plugin;
8. record the source/build/publication identity in project documentation.

Do not create a PR merely to attach an existing package asset.

When a repository-owned build-and-publish operation is actually required, create only
the exact temporary branch `publish/v<VERSION>_<REVISION>`. The single generic
`.github/workflows/publish-prerelease.yml` validates branch identity, builds on FreeBSD
15, checks `+MANIFEST`, creates only the testing package prerelease, verifies it, and
deletes the temporary branch. Only one active run is permitted for the candidate.

A testing package publication never deploys GitHub Pages or pkg-repository metadata.

==================================================
FULL PROJECT RELEASE
==================================================

A full project release is separate from an ordinary patch and a testing package
publication.

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
3. `gh` for Actions or package/release operations not covered by the plugin;
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
that a verified merge or package publication failed.

==================================================
PATCH VERSUS PACKAGE PUBLICATION VERSUS RELEASE
==================================================

Ordinary packaged source patch:

- keep `VERSION`;
- increment `PLUGIN_REVISION` once;
- merge through the normal PR path;
- if the owner requested the package itself for testing/installation/delivery, continue
  through GitHub testing-package publication; do not stop at the Actions artifact.

Package requested by owner:

- means a persistent GitHub `.pkg`, not an Actions artifact or sandbox file;
- uses the current unpublished complete package candidate when one already exists;
- otherwise creates the next package revision through the normal PR/CI/squash path;
- publishes one direct `.pkg` GitHub asset;
- returns the direct GitHub URL or csh-safe `pkg add -f` command.

Governance/documentation/CI-only patch:

- change neither version value;
- use the unchanged candidate prefix;
- run path-applicable CI;
- does not itself publish package bytes unless the owner also asks for a package.

Testing package publication:

- authorized by the owner package request or exact candidate-publication instruction;
- publishes one verified package asset only;
- no Pages/pkg repository;
- is not a semantic/full project release.

Full project release:

- exact new `VERSION` authority;
- revision reset to `1`;
- versioned release-preparation title;
- full immutable tag/Release/Pages/pkg-repository pipeline.

==================================================
SUPERSESSION
==================================================

This document and the active decisions listed at the top supersede conflicting wording
that requires or permits:

- using chat history, generic web search, local state, or another transport before the
  connected GitHub plugin for an operation the plugin supports;
- continuing GitHub work through another transport when the plugin itself is unavailable;
- treating a required-document open/fetch as a completed read when content was truncated;
- mandatory Draft PRs;
- exactly one commit in a PR branch;
- exactly one historical workflow run;
- closing a valid PR after an ordinary same-scope failure;
- stopping independent analysis while CI runs;
- full-repository rereading for every small operation;
- unversioned governance or release-preparation subjects;
- version-specific prerelease workflows in `main`;
- source/workflow/runner changes in response to an external infrastructure failure;
- publication PRs for already verified assets;
- treating only a narrow phrase list as authorization for owner package delivery;
- presenting an Actions artifact, ZIP, or sandbox/local file as completion of an owner
  package request;
- asking for an additional testing-package confirmation after the owner has requested
  the package.

# DEC-2026-08-05 — Efficient GitHub delivery

Status: Active, amended 2026-08-06
Date: 2026-08-05

## Context

The repository accumulated GitHub process rules intended to prevent branch clutter and
preserve atomic delivery. Several rules became counterproductive:

- the next patch could not even be analyzed or prepared until all checks finished;
- a valid PR had to be closed and replaced after an ordinary same-scope failure;
- one PR branch was required to contain exactly one commit and one check set;
- low-level blob/tree preparation was treated as mandatory architecture;
- Draft → Ready and branch-cleanup completion were treated as delivery gates;
- full package CI ran again after merge even when the PR merge result had already been
  built;
- a branch-hygiene test asserted literal documentation phrases and a fixed project
  version instead of durable behavior.

Actual repository practice already contradicted those rules: corrective PRs contained
multiple commits, Draft PRs accumulated a series of patches, and repeated full CI runs
were used while documentation still claimed exactly one commit and one check set.

## Decision

Adopt an outcome-based GitHub workflow.

### Logical scope and permanent history

- One logical change uses one task branch and one pull request.
- The PR branch may contain multiple same-scope work and repair commits.
- Squash merge creates one logical permanent commit in `main`.
- Commit count in the PR and historical workflow-run count are not correctness metrics.

### Pull-request state

- Open a Ready PR when content is ready for review and merge.
- Use Draft only for intentional work in progress or early design discussion.
- Correct ordinary same-scope failures in the same branch and PR.
- Replace a PR only when its base, scope, or history is materially wrong, safe repair in
  place is impossible, or the approach is abandoned.

### CI

- Required checks gate merge of the latest mergeable PR state.
- A newer PR head may cancel obsolete in-progress runs through workflow concurrency.
- Transient failures may rerun only failed jobs.
- CI does not forbid independent analysis or separate preparation while it runs.
- Dependent successors must merge in prerequisite order; independent work may proceed
  concurrently.
- Product/package PRs receive the meaningful pre-merge package build.
- Documentation/governance-only PRs skip the FreeBSD package build unless package inputs
  are affected.
- `main` push CI is a lightweight integrity check rather than a duplicate complete
  package build.

### Transport selection

- Use the connected GitHub plugin first for repository, PR, checks, reviews, merge, and
  every other operation it supports.
- When the plugin is responding but one exact function or permission is confirmed
  missing, use local `git`, `gh`, the web UI, or another authenticated API only for that
  narrow operation.
- Return to the plugin for subsequent supported reads and writes.
- If the plugin is unavailable, non-responsive, or cannot provide the authoritative
  repository state required for safe work, stop all GitHub work, inform the project
  owner, and wait for explicit direction. Do not switch transports automatically.
- Git data blobs/trees are optional for API-only atomic construction, not mandatory.
- Missing one fallback client is not a blocker while the plugin is available and another
  verified authenticated mechanism safely covers the exact confirmed gap.

### Merge and cleanup

- Verify scope, required checks, mergeability, expected head SHA, and the intended
  versioned squash subject.
- Squash merge once.
- Prefer repository-native auto-merge and automatic merged-branch deletion when enabled.
- Until repository settings provide native deletion, retain the same-repository cleanup
  workflow as a fallback.
- Branch cleanup failure is a repository-hygiene problem, not evidence that a verified
  code merge failed.

### Titles and package metadata

The title subsection is amended and controlled by
`DEC-2026-08-05-universal-versioned-github-titles.md`.

- Every PR title, every work or repair commit subject in the PR branch, and the final
  squash commit subject in `main` must begin with the exact current package-candidate
  prefix `v<VERSION>_<PLUGIN_REVISION>:` derived from the PR head.
- The same rule applies to code, documentation, governance, CI, maintenance, and
  release-preparation work.
- Governance/documentation/CI-only changes outside packaged plugin contents change
  neither `VERSION` nor `PLUGIN_REVISION`; they use the unchanged current package-
  candidate prefix.
- Unversioned conventional subjects such as `governance:`, `docs:`, `ci:`, or `chore:`
  are not valid project delivery titles.

## 2026-08-06 amendment — Evidence-first operations

`DEC-2026-08-06-evidence-first-github-operations.md` controls pre-mutation inventory,
GitHub transport selection and outage handling, testing-prerelease publication,
publication-run limits, artifact identity, and release-preparation title mechanics.

Compatible rules above remain active. The amendment additionally requires:

- the connected GitHub plugin as the first repository interface;
- a narrow fallback only when the responding plugin lacks one exact function or
  permission;
- immediate stop, owner notification, and no automatic fallback when the plugin itself
  is unavailable or cannot provide the authoritative state required for safe work;
- inventory of workflows, branches, PRs, runs, artifacts, tags, releases, assets, and
  permissions before mutation;
- job-log evidence before changing source, workflow, runner, or branch;
- zero source changes and at most one unchanged rerun for an external infrastructure
  failure;
- no speculative runner switching, replacement publication branches, duplicate
  trackers, or unbounded retries;
- direct release upload for an already verified package when available;
- one generic prerelease publisher instead of version-specific workflows;
- release-preparation title `vX.Y.Z_1: Prepare release vX.Y.Z`;
- no shell-test or CI contract for the exact wording or line placement of the
  plugin-first prose.

## Consequences

- GitHub Actions waiting no longer idles all project work.
- Same-scope repair history stays in one PR.
- `main` remains clean through squash merge without imposing artificial restrictions on
  the working branch.
- Obsolete runs are canceled, expensive package builds are not duplicated, and docs-only
  changes avoid irrelevant FreeBSD builds.
- Every visible GitHub delivery title remains tied to the exact current working package
  candidate.
- PR CI validates PR and branch-commit subjects; post-merge integrity validates the final
  squash subject.
- Candidate publication no longer creates a code PR merely to attach an existing asset.
- External GitHub failures no longer trigger speculative repository changes.
- GitHub-plugin outages stop repository work visibly instead of causing silent transport
  substitution.

## Supersession

This decision supersedes conflicting delivery wording in:

- `docs/decisions/DEC-2026-08-02-atomic-github-publication.md` except where a later active
  title rule explicitly preserves package-candidate identity;
- `docs/architecture/STRATEGY_LAB.md` serial patch gate;
- older Git sections of `WORKING_CONVENTIONS.md` and `DEVELOPMENT_GUIDE.md`;
- historical patch, audit, devlog, and PR text;
- any unmerged decision that requires one published commit at a time and prohibits even
  separate preparation while checks run.

The 2026-08-06 amendment additionally supersedes conflicting publication, transport, and
failure wording as specified in
`docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`.

Product architecture, runtime safety, package/release separation, no-force-push rules,
universal package-candidate title identity, and owner authorization boundaries are
unchanged.

## Affected controls

- `AGENTS.md`;
- `docs/INDEX.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/PROJECT_STATE.md`;
- `docs/WORKING_CONVENTIONS.md`;
- `docs/DEVELOPMENT_GUIDE.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `.github/workflows/ci.yml`;
- `.github/workflows/pr-title.yml`;
- `.github/workflows/cleanup-merged-branch.yml`;
- `.github/workflows/publish-prerelease.yml`;
- `.github/workflows/release-trigger.yml`;
- `scripts/test-github-branch-hygiene.sh`.

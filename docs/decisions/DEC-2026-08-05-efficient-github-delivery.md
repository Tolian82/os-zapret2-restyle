# DEC-2026-08-05 — Efficient GitHub delivery

Status: Active
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

- Use the connected GitHub app/API for repository, PR, checks, reviews, and merge when it
  covers the operation.
- Use local `git` for editing and commits when an authenticated checkout is available.
- Use `gh` for Actions logs or uncovered operations when available.
- Git data blobs/trees are optional for API-only atomic construction, not mandatory.
- Missing one client is not a blocker when another verified authenticated mechanism can
  safely complete the action.

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
- Process documents describe stable outcomes rather than one connector or API sequence.
- Current repository settings may temporarily require explicit squash merge and the
  cleanup workflow until native auto-merge and head-branch deletion are enabled.

## Supersession

This decision supersedes conflicting delivery wording in:

- `docs/decisions/DEC-2026-08-02-atomic-github-publication.md` except where a later active
  title rule explicitly preserves package-candidate identity;
- `docs/architecture/STRATEGY_LAB.md` serial patch gate;
- older Git sections of `WORKING_CONVENTIONS.md` and `DEVELOPMENT_GUIDE.md`;
- historical patch, audit, devlog, and PR text;
- any unmerged decision that requires one published commit at a time and prohibits even
  separate preparation while checks run.

Product architecture, runtime safety, package/release separation, no-force-push rules,
universal package-candidate title identity, and owner authorization boundaries are
unchanged.

## Affected controls

- `AGENTS.md`;
- `docs/INDEX.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/PROJECT_STATE.md`;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `.github/workflows/ci.yml`;
- `.github/workflows/pr-title.yml`;
- `.github/workflows/cleanup-merged-branch.yml`;
- `scripts/test-github-branch-hygiene.sh`.

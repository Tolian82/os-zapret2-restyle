# GitHub publication and delivery discipline

Status: **AUTHORITATIVE PROCEDURE**

This file answers: **How are project changes/packages/releases delivered through GitHub?**

Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`; this file contains procedure only.
Read it completely immediately before GitHub mutation.

## Active authorities

- `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

## GitHub plugin boundary

Use the connected GitHub plugin first for repository reads/writes it supports.

A fallback transport is allowed only when:

- the plugin is responding;
- the exact required function/permission is confirmed missing/insufficient;
- fallback is limited to that exact operation.

Plugin unavailability/non-response or inability to read authoritative state is a stop condition.
Do not silently continue through Git/`gh`/raw API/web UI/automation.

## Required-document completion

Before mutation, complete the mandatory startup reading from `AGENTS.md` and all specialist GitHub
procedure/decision documents selected for the operation through EOF.

A successful fetch/open is not a complete read if output was truncated/clamped/paginated.

## Scope-first pre-mutation inventory

Always verify:

1. exact current `main` SHA;
2. current `VERSION` and `PLUGIN_REVISION`;
3. current documented task/plan (`START_HERE`, `PROJECT_STATE`, `ROADMAP` as applicable);
4. same-scope/relevant open PR state;
5. plugin availability for required operation.

Then expand according to operation:

- **ordinary known-scope source/docs patch:** no unrelated global branch/workflow/tag/release scan;
- **CI debugging/current PR:** relevant workflow/run/jobs/checks/logs;
- **testing package:** exact build run/artifact, candidate tag/release/assets, active publication run;
- **stable release:** release workflow, tag/release/Pages/pkg-repo state and release gates;
- **branch cleanup/recovery/hygiene:** complete relevant branch inventory;
- **broad/cross-cutting investigation:** pinned recursive tree when paths/call chain are unknown;
- **permissions/protection:** inspect only when operation depends on them.

Do not create a new workflow/runner/branch mechanism until relevant inventory proves the current
mechanism cannot safely perform the operation.

## Mandatory documentation gate before publication

Immediately before publishing a task branch/PR or equivalent GitHub delivery:

1. verify the documentation states **what changes and why**;
2. verify it states **the expected result and acceptance criteria**;
3. verify it states **the complete next plan**, including near-term and long-term/deferred work;
4. reconcile that plan against implementation/testing discoveries;
5. if scope/result/plan changed, update documentation **before publication**.

This is the publication implementation of `docs/PROJECT_PRINCIPLES.md`.

## Package-candidate identity

Derive from proposed head:

- semantic version from `VERSION`;
- packaged revision from `PLUGIN_REVISION`;
- non-zero title prefix: `v<VERSION>_<PLUGIN_REVISION>:`;
- zero revision prefix: `v<VERSION>:`.

Every PR title, PR-branch commit subject and final squash subject uses the exact prefix.

Docs/governance/CI-only changes do not alter package metadata.

## Ordinary development flow

1. resolve owner scope/stopping boundary;
2. complete startup/specialist reading;
3. perform scope-first GitHub preflight;
4. record exact base, logical scope, documentation/verification plan;
5. create one task branch;
6. implement one logical change including synchronized documentation;
7. run focused validation and review complete diff;
8. perform plan reconciliation;
9. open one Ready PR (Draft only for intentional WIP);
10. keep same-scope repairs in that PR;
11. require successful checks for latest mergeable head;
12. before merge verify scope/title/mergeability/checks/expected head;
13. squash merge once with exact versioned subject;
14. verify resulting `main` and temporary branch cleanup.

A PR may contain multiple same-scope commits. `main` receives one logical squash commit.

## CI failure handling

Read exact failed-job evidence before changing source/workflow/runner/branch.

Classify:

1. same-scope source/docs/test/title defect -> repair same PR;
2. external GitHub/runner/network/action/dependency outage -> zero source change, at most one
   unchanged rerun after recovery;
3. PR metadata defect -> correct metadata;
4. materially wrong base/scope/history -> replace only with recorded evidence;
5. missing protected authority/credentials -> stop at boundary;
6. plugin unavailable -> stop GitHub work.

Do not react to an unproven/external failure by changing runner OS, creating retry/final sibling
branches, adding replacement workflows, repeated push experiments, duplicate trackers or unbounded
retries.

A second unchanged infrastructure failure stops for diagnosis.

## Owner testing-package delivery

Any owner request for package/patch bytes for testing/installation/delivery means persistent GitHub
`.pkg`, unless explicitly requesting build/CI evidence only.

Actions artifacts/local/sandbox files are build evidence only.

`не релиз, а пакет` means:

- no semantic VERSION promotion;
- no stable/full release;
- no Pages/pkg-repository promotion;
- **yes** persistent testing `.pkg` publication on GitHub.

The package request itself authorizes deterministic testing-package publication; do not ask for a
second confirmation merely because GitHub uses a prerelease/tag container.

### Candidate selection

1. read current `main`, `VERSION`, `PLUGIN_REVISION`;
2. if current complete candidate already contains requested changes and is unpublished, publish it;
3. if packaged source changes are required, increment revision once through normal PR cycle;
4. docs-only clarification does not force a new package revision.

### Preferred publication path

When verified bytes already exist:

1. identify exact source commit/build;
2. bind artifact by exact run ID, artifact ID/name and digest;
3. verify package `+MANIFEST` version/ABI/arch;
4. publish exact testing tag/asset through plugin if supported, otherwise narrow fallback for missing
   release-asset write;
5. verify target SHA, tag, `draft=false`, `prerelease=true`, asset name, size/digest and direct URL;
6. record publication identity in project documentation.

Do not create a PR merely to attach an already verified package.

When repository-owned build-and-publish automation is required, use only temporary branch
`publish/v<VERSION>_<REVISION>` and the generic `.github/workflows/publish-prerelease.yml`.
One candidate may have only one active publication run. Delete temporary publication branch after
success.

Testing-package publication never deploys Pages or pkg repository metadata.

Normal owner installation form:

`pkg add -f https://github.com/Tolian82/os-zapret2-restyle/releases/download/v<VERSION>_<REVISION>/os-zapret2-restyle-<VERSION>_<REVISION>.pkg`

## Full semantic project release

Separate from testing package publication.

Requires:

- explicit exact new `VERSION=X.Y.Z` authority;
- product/live release gates satisfied;
- `PLUGIN_REVISION=1`;
- preparation title `vX.Y.Z_1: Prepare release vX.Y.Z`;
- verified merge;
- immutable semantic tag `vX.Y.Z`;
- full Release workflow/package/pkg repository/Pages verification as defined by current release
  procedure.

Published tags/releases/assets/versions are forward-only and never rewritten.

## Transport order

While plugin is available:

1. GitHub plugin for supported operations;
2. authenticated ordinary Git for local editing/ref gaps;
3. `gh` for Actions/release gaps;
4. Git data API for atomic multi-file construction when needed;
5. web UI only for a narrow operation tools cannot perform.

Fallback never replaces plugin for subsequent supported operations.

## Merge / cleanup

Before merge compare:

- candidate prefix;
- PR title;
- intended squash subject;
- exact expected head SHA;
- required checks;
- final documented plan reconciliation state.

Squash once. Never force-update `main`.

Temporary task/publication branches are removed after verified completion. Preserve `recovery/base`
and pre-existing owner branches unless separately authorized.

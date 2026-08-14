# GitHub publication and delivery discipline

Status: **AUTHORITATIVE PROCEDURE**

This file answers: **How are project changes/packages/releases delivered through GitHub?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current task: `docs/START_HERE.md`.
Operational handoff/preflight authority: `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`.

Read this file completely immediately before GitHub mutation. The decision above records rationale and
supersession boundaries; it is not an additional mandatory reread for every ordinary mutation unless
the current operation needs that rationale.

## GitHub plugin boundary

Use the connected GitHub plugin first for every supported repository operation.

A fallback transport is allowed only when:

- the plugin is responding;
- one exact required function/permission is confirmed missing/insufficient;
- fallback is limited to that operation;
- subsequent supported operations return to the plugin.

Plugin unavailability/non-response or inability to read authoritative required state is a stop
condition, not permission to switch transports silently.

## Scope-first preflight

Always verify before mutation:

1. exact current `main` SHA;
2. current `VERSION` and `PLUGIN_REVISION`;
3. current documented task/plan;
4. same-scope/relevant open PR state;
5. plugin availability for the operation.

Expand inventory only when the operation needs it:

- CI debugging/current PR -> relevant runs/jobs/checks/logs;
- testing package/release -> exact artifact/tag/release/asset/publication-run state;
- branch cleanup/recovery/hygiene -> relevant complete branch inventory;
- protection/permission work -> relevant protection/permission state;
- broad/cross-cutting investigation with unknown paths -> pinned recursive tree.

A known-file task named by `START_HERE.md` does not require unrelated historical branch/workflow/tag/
release discovery before implementation.

## Documentation gate

The unchanged task branch may be created from the verified base immediately after preflight.

Before the **first substantive changed branch state** is published to GitHub, the logical change must
already contain synchronized documentation stating:

1. what changes and why;
2. expected result and acceptance boundary;
3. complete ordered next plan, including near-term and long-term/deferred work.

Before opening/updating a Ready PR for the final intended head, and again immediately before merge,
reconcile that plan against implementation/testing discoveries. If scope, expected result, test/audit
needs, priority or deferred state changed, update documentation first.

This avoids both extremes: an unchanged branch may be created early, but substantive project changes
must never be published without their Engineering Memory.

## Candidate identity / titles

Derive from proposed head:

- semantic version from `VERSION`;
- package revision from `PLUGIN_REVISION`;
- title prefix `v<VERSION>_<PLUGIN_REVISION>:` for non-zero revision.

Every PR title, PR-branch commit subject and final squash subject uses the exact candidate prefix.
Docs/governance/CI-only changes do not alter package metadata.

## Ordinary development flow

1. resolve owner scope/stopping boundary;
2. complete mandatory startup + task-specialist reading;
3. perform scope-first preflight;
4. create one task branch from exact base;
5. implement one logical scope with synchronized documentation;
6. run focused validation and review complete diff;
7. reconcile documentation/plan;
8. open one Ready PR (Draft only for intentional WIP);
9. keep same-scope corrections in that PR;
10. require successful checks for latest mergeable head;
11. re-reconcile plan and verify title/scope/checks/exact head;
12. squash merge once with exact versioned subject;
13. verify resulting `main` and clean the temporary branch.

A PR branch may contain multiple same-scope commits; `main` receives one logical squash commit.

## CI failure handling

Read exact failed-job evidence before changing source/workflow/runner/branch.

- confirmed same-scope source/docs/test defect -> repair same PR;
- external GitHub/runner/network/action/dependency outage -> zero source change; at most one unchanged
  rerun after recovery;
- PR metadata defect -> correct metadata;
- materially wrong base/scope/history -> replace only with recorded evidence;
- missing protected authority/credentials or unavailable plugin -> stop at boundary.

Do not create retry/final sibling branches, change runner OS, add replacement workflows or perform
unbounded retries without evidence that the current mechanism is defective.

## Owner testing-package delivery

Any owner request for package/patch bytes for testing/installation/delivery means a persistent GitHub
`.pkg`, unless the owner explicitly requests build/CI evidence only.

Actions artifacts/local files are build evidence only.

`не релиз, а пакет` means:

- no semantic VERSION promotion;
- no stable/full project release;
- no Pages/pkg-repository promotion;
- yes: persist the deterministic testing `.pkg` on GitHub.

The package request itself authorizes deterministic testing-package publication; no second
confirmation is required merely because GitHub uses a prerelease/tag container.

When verified bytes already exist:

1. bind exact source commit/build/run/artifact/digest;
2. verify package manifest version/ABI/arch;
3. publish exact testing tag/asset through plugin if supported, otherwise narrow fallback only for the
   missing release-asset operation;
4. verify target SHA, tag, draft/prerelease flags, asset name/size/digest/direct URL;
5. record publication identity in documentation.

When repository-owned build/publish automation is needed, use only the generic
`.github/workflows/publish-prerelease.yml` and temporary `publish/v<VERSION>_<REVISION>` branch.
Remove temporary publication branch after success.

Testing-package publication never deploys Pages/pkg repository metadata.

## Full semantic release

Separate from testing-package publication. Requires explicit exact new `VERSION` authority and the
current product/live release gates.

Normal preparation identity:

- set new VERSION;
- reset `PLUGIN_REVISION=1`;
- title/squash `vX.Y.Z_1: Prepare release vX.Y.Z`;
- verified merge;
- immutable semantic tag and full release/package/pkg-repository/Pages pipeline as defined by the
  current release procedure.

Never rewrite published `main`, tags, releases, assets or package history.

## Transport order when fallback is genuinely needed

1. GitHub plugin for supported operations;
2. authenticated ordinary Git for an exact local editing/ref gap;
3. `gh` for an exact Actions/release gap;
4. Git data API for atomic multi-file construction when needed;
5. web UI only for an exact operation tools cannot perform.

Fallback never becomes the default transport.

## Authority boundaries

Standing owner authorization for an ordinary `fix/add/change/implement/complete` request covers task
branch, Ready PR, CI inspection, same-scope repair, squash merge, main verification and temporary
branch cleanup.

Stop for owner input only on material product/architecture ambiguity, relevant unpublished owner-local
state, owner-only live evidence, protected credentials/authority, destructive work affecting user or
pre-existing remote data, direct-main/history rewrite, unresolvable required-check failure or GitHub
plugin unavailability.

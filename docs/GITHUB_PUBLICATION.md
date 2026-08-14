# GitHub publication and delivery discipline

Status: **AUTHORITATIVE PROCEDURE**

This file answers: **How are project changes/packages/releases delivered through GitHub?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current task: `docs/START_HERE.md`.

Read this file completely immediately before GitHub mutation. Decision records contain rationale and
are loaded only when the current operation needs that rationale.

## GitHub plugin boundary

Use the connected GitHub plugin first for every supported repository operation.

A fallback transport is allowed only when the plugin is responding but one exact required function or
permission is confirmed missing/insufficient. Limit fallback to that operation and return to the
plugin afterwards. Plugin unavailability or inability to read required authoritative state is a stop
condition.

## Scope-first preflight

Always verify before mutation:

1. exact current `main` SHA;
2. current `VERSION` and `PLUGIN_REVISION`;
3. current documented task reconciled against the owner's newest unambiguous instruction/fact;
4. same-scope/relevant open PR state;
5. plugin availability for the operation.

Expand inventory only when scope requires it: CI logs for CI debugging, tag/release/assets for package
publication, branch inventory for cleanup/recovery, protection state when relevant, recursive tree for
a genuine broad investigation, and a broad active-document sweep when owner canon must be recorded.

## Owner canon / stale contracts

The newest unambiguous owner instruction, explicit fact or confirmed decision is current project canon
and supersedes conflicting older active docs/tests/plans. Do not reconfirm settled canon merely because
old material disagrees.

When the owner says `зафиксируй` / equivalent, the first GitHub docs change must:

1. record canon in current/canonical authority;
2. inspect active/current authority files capable of contradicting it;
3. correct every active contradiction in the same logical change;
4. leave old statements only as clearly historical/superseded records.

A stale CI/test assertion is corrected rather than used to bend current canon back to obsolete intent.

## Documentation / zero-memory gate

Before the first substantive changed branch state is considered ready for delivery, synchronize the
three-level documentation model:

- Level 1 exposes current facts, compact handoff, short lifetime path and exact next task;
- the active minor-line Level-2 ledger records richer current chronology when useful;
- Level 3 retains old archive maps and original deep records on demand;
- `ROADMAP` contains current/future ordering, not a growing historical narrative;
- `INDEX` routes directly to the current ledger, each completed version-line archive and deep stores;
- every newly approved permanent rule is in `PROJECT_PRINCIPLES`;
- an owner `зафиксируй` request has received its required active-authority consistency sweep.

Detailed patch/devlog/evidence records are created/updated when they add distinct contract, execution
or proof value; they are not duplicated merely to repeat text already held by the current-line ledger.
Existing historical records are never deleted merely to reduce context.

Before Ready PR and again before merge, reconcile documentation against implementation/testing and the
newest owner canon. Acceptance question: could a future session with complete loss of chat/model
memory resume the exact boundary from Level 1 and discover deeper history through links only when
needed? If not, the delivery is not ready.

## Candidate identity / titles

Derive from proposed head:

- semantic version from `VERSION`;
- package revision from `PLUGIN_REVISION`;
- title prefix `v<VERSION>_<PLUGIN_REVISION>:` for non-zero revision.

Every PR title, PR-branch commit subject and final squash subject uses that candidate prefix.
Docs/governance/CI-only changes do not alter package metadata.

## Ordinary development flow

1. resolve owner scope/stopping boundary and newest canon;
2. complete mandatory Level-1 + task-specialist reading;
3. perform scope-first preflight;
4. create one task branch from exact base;
5. implement one logical scope with synchronized documentation;
6. run focused validation and review complete diff;
7. reconcile current state/roadmap/current-line ledger and any required canon sweep;
8. open one Ready PR (Draft only for intentional WIP);
9. keep same-scope corrections in that PR;
10. require successful checks for latest mergeable head;
11. re-reconcile owner canon/plan and verify title/scope/checks/exact head;
12. squash merge once with exact versioned subject;
13. verify resulting `main`;
14. preserve useful unique branch work if any, otherwise remove temporary branch and verify hygiene.

A PR branch may contain multiple same-scope commits; `main` receives one logical squash commit.

## CI failure handling

Read exact failed-job evidence before changing source/workflow/runner/branch.

- confirmed same-scope source/docs/test defect -> repair same PR;
- stale test/CI assertion -> update stale assertion/contract, not current canon;
- external GitHub/runner/network/action/dependency outage -> zero speculative source change;
- PR metadata defect -> correct metadata;
- materially wrong base/scope/history -> replace only with recorded evidence;
- missing protected authority/credentials or unavailable plugin -> stop at boundary.

Do not create retry/final sibling branches, change runner OS, add replacement workflows or perform
unbounded retries without evidence the current mechanism is defective.

## Repository / branch hygiene

After merge/completion:

1. compare temporary branch/PR work with merged `main`;
2. preserve useful unique work first if any;
3. otherwise remove the temporary branch;
4. verify no obsolete task/publication branch remains.

Routine successful cleanup is not an owner problem and is normally silent.

## Owner-facing status

Owner-facing project status/results are clear Russian by default. If internal English GitHub/CI terms
are useful as evidence, explain their practical meaning in Russian: what passed/failed, whether the
change is already in `main`, and what happens next.

## Owner testing-package delivery

Any owner request for package/patch bytes for testing/installation/delivery means a persistent GitHub
`.pkg`, unless build/CI evidence only was explicitly requested. Actions artifacts/local files are build
evidence only.

`не релиз, а пакет` means:

- no semantic VERSION promotion;
- no stable/full project release;
- no Pages/pkg-repository promotion;
- yes: persist the deterministic testing `.pkg` on GitHub.

No second confirmation is required merely because GitHub uses a prerelease/tag container.

When verified bytes already exist:

1. bind exact source commit/build/run/artifact/digest;
2. verify package manifest version/ABI/arch;
3. publish exact testing tag/asset through plugin if supported, otherwise narrow fallback for only the
   missing release-asset operation;
4. verify target SHA, tag, draft/prerelease flags, asset name/size/digest/direct URL;
5. record publication identity in current documentation/evidence as appropriate.

When repository-owned automation is needed, use only the approved generic testing-package workflow and
remove temporary publication branch after success. Testing-package publication never deploys Pages/pkg
repository metadata.

## Full semantic release

A full semantic release requires explicit exact new `VERSION` authority and the current product/live
release gates.

### Automatic semantic-minor documentation rollover

Before publishing the first release whose `MAJOR.MINOR` differs from the active line, for example the
owner requests `v0.5.0_1` while `v0.4.x` is current, the release change automatically must:

1. update `docs/history/current/v0.4.x.md` through the final `v0.4.x` state;
2. freeze/create `docs/history/archive/v0.4.x.md` as the compact map for that completed line;
3. preserve every original `v0.4.x` devlog/patch/verification/release/decision/audit record;
4. initialize `docs/history/current/v0.5.x.md`;
5. update `docs/INDEX.md` so it directly links the new current ledger and the new archive;
6. update `START_HERE`, `PROJECT_STATE`, `ROADMAP` and the short lifetime path for `v0.5.x`;
7. keep current architecture/contracts and permanent principles current rather than archiving them;
8. then continue the normal VERSION/tag/release pipeline.

The explicit request for the new minor release is authority for this rollover; no extra owner reminder
or confirmation is required.

Normal release identity after any required rollover:

- set new `VERSION`;
- reset `PLUGIN_REVISION=1`;
- title/squash `vX.Y.Z_1: Prepare release vX.Y.Z`;
- verified merge;
- immutable semantic tag and full release/package/pkg-repository/Pages pipeline defined by current
  release procedure.

Never rewrite published `main`, tags, releases, assets or package history.

## Transport order for a genuine plugin gap

1. GitHub plugin for supported operations;
2. authenticated ordinary Git for exact local editing/ref gap;
3. `gh` for exact Actions/release gap;
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

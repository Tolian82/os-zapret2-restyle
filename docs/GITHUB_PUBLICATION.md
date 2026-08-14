# GitHub publication and delivery discipline

Status: **AUTHORITATIVE PROCEDURE**

This file answers: **how are project changes, testing packages and full releases delivered through GitHub?**

Permanent principles: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md).
Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).
Current handoff: [`START_HERE.md`](START_HERE.md).
Current state: [`PROJECT_STATE.md`](PROJECT_STATE.md).
Master plan: [`ROADMAP.md`](ROADMAP.md).

Read this file completely immediately before GitHub mutation.

## GitHub plugin boundary

Use the connected GitHub plugin first for every supported repository operation. A fallback transport is
allowed only when the plugin is responding but one exact required function/permission is confirmed
missing. Plugin unavailability or inability to read required authoritative state stops GitHub work.

## Scope-first preflight

Always verify before mutation:

1. exact current `main` SHA;
2. current `VERSION` and `PLUGIN_REVISION`;
3. current `START_HERE`, `PROJECT_STATE` and master-plan consistency with newest owner canon;
4. same-scope/relevant open PR state;
5. plugin availability.

Expand inventory only when scope needs it: exact CI/log evidence, release assets, branch hygiene,
protection/permissions, recursive tree for broad investigation, or broad active-document sweep for
owner-canon reconciliation.

## Owner canon / “Суслик” rule

The newest unambiguous owner instruction/fact/confirmed decision is current canon. When the owner says
`зафиксируй` / equivalent, the first GitHub documentation change must record it and reconcile every
active/current authority and CI contract capable of contradicting it. Historical material may retain
old statements only as clearly historical/superseded records.

## Documentation gate

Every GitHub delivery obeys the numbered rules in `DOCUMENTATION_RULES.md`.

Before publication confirm:

- Level 1 is internally consistent and sufficient for zero-memory recovery;
- `START_HERE` describes the exact current `_N` revision, recent change/effect, immediate next action
  and relevant future direction;
- durable completed facts have flowed into `PROJECT_STATE` when applicable;
- `PROJECT_STATE` remains scoped to the current second-component line and ends with all archive links;
- `ROADMAP` contains the complete concise completed/current/future plan;
- `INDEX` routes to every memory level/archive/deep-record store;
- the current line ledger records richer chronology when useful;
- every owner `зафиксируй` request received its active-document consistency sweep.

Detailed devlog/patch/verification/decision records are created when they add distinct execution,
proof or rationale value; duplication is not preservation.

## Version and candidate identity

For candidate `v0.4.2_14`:

- second numeric component `4` = state/release line `v0.4.x`;
- third numeric component `2` = current development stage/task;
- package revision `_14` = exact patch/iteration.

Derive PR/branch/final squash prefix from current candidate:

`v<VERSION>_<PLUGIN_REVISION>:`

Every PR title, PR-branch commit subject and final squash subject uses that prefix.

### Ordinary same-stage patch

- keep `VERSION` unchanged;
- increment `PLUGIN_REVISION` once for packaged source/behavior change;
- synchronize documentation for the new `_N` boundary;
- docs/governance/CI-only changes change neither value.

### Third-numeric-component stage transition

A genuine new current development stage may move, for example, `v0.4.1_14 -> v0.4.2_1`:

- second component stays unchanged;
- third component changes because the active task/stage genuinely changed;
- `PLUGIN_REVISION` resets to `1`;
- `START_HERE` is initialized for the new stage/revision;
- `PROJECT_STATE` remains the same `v0.4.x` state file and is updated only for facts that changed;
- this transition **does not publish a full release by itself**.

A third-component stage transition therefore changes development relevance without closing the current
second-component project-state line.

The release trigger must classify this as a development-stage transition and finish successfully
without creating a semantic tag/release unless the exact merge subject explicitly prepares a release.

### Second-numeric-component transition

The `4` in `0.4.x` is owner-controlled. The assistant never initiates `v0.4.x -> v0.5.x` by inference.
It requires explicit owner version/transition instruction or separate approval. Once authorized:

- the transition always includes a full release;
- the new stage begins at package revision `_1`;
- final old `PROJECT_STATE` content is preserved in the old line archive;
- old current ledger is finalized as archive and the new current ledger is initialized;
- Level 1, `ROADMAP`, `INDEX` and README are reconciled;
- no redundant second confirmation is required for the already-authorized rollover/release.

A full release may also occur without changing the second component.

## Ordinary development flow

1. resolve owner scope/stopping boundary and newest canon;
2. complete mandatory Level 1 and task-specialist reading;
3. perform scope-first preflight;
4. create one task branch from exact base;
5. implement one logical scope with synchronized documentation;
6. run focused validation and review the complete diff;
7. reconcile `START_HERE`, `PROJECT_STATE`, master plan, current ledger and any required canon sweep;
8. open one Ready PR (Draft only for intentional WIP);
9. keep same-scope corrections in that PR;
10. require successful checks for the latest mergeable head;
11. re-reconcile owner canon/plan and verify title/scope/checks/exact head;
12. squash merge once with exact versioned subject;
13. verify resulting `main`;
14. preserve useful unique branch work or remove the temporary branch and verify clean state.

## CI failure handling

Read exact failed-job evidence before changing source/workflow/runner/branch.

- confirmed same-scope defect -> repair in same PR;
- stale test/CI assertion -> update stale assertion/contract;
- external runner/network/action/dependency outage -> no speculative source change;
- PR metadata defect -> correct metadata;
- missing protected authority or unavailable plugin -> stop at boundary.

## Repository / branch hygiene

After merge/completion compare temporary branch work with merged `main`; preserve any useful unique work,
otherwise remove the branch and verify no obsolete task/publication branch remains.

## Owner testing-package delivery

An owner request for package bytes for testing/installation means persistent GitHub `.pkg` unless
build/CI evidence only was explicitly requested.

Testing package means:

- no full release;
- no Pages/pkg-repository promotion;
- persistent deterministic GitHub package/prerelease asset;
- exact source/tag/asset/digest identity verified;
- temporary publication branch removed after success.

## Full project release

A full release is not merely a tag or uploaded package. It is a complete OPNsense delivery:

- explicit owner release authority;
- exact current candidate `VERSION` + `PLUGIN_REVISION`;
- complete human-facing `README.md` revision;
- verified merge commit titled `v<VERSION>_<PLUGIN_REVISION>: Prepare release v<VERSION>`;
- immutable semantic tag `v<VERSION>` pointing to that exact merge;
- normal GitHub Release with the exact package and checksum assets;
- matching `FreeBSD:15:amd64` Pages/pkg repository deployment;
- installation/update availability through the OPNsense Web GUI.

**A full release does not reset `PLUGIN_REVISION` merely because it is a release.** The current exact
`_N` candidate may be released. Revision resets to `_1` only when a new third-component stage or new
second-component line is entered.

If semantic tag `v<VERSION>` already exists at another commit, published history is immutable: do not
move it. A later full release requires a new appropriate project version according to owner-approved
version semantics.

## Release-trigger contract

The `main` release-trigger workflow classifies every merge:

1. normal same-`VERSION` commit -> no release;
2. third-component-only `VERSION` change -> require `_1`, no release unless the merge subject is an
   explicit release-preparation subject;
3. second-component change -> require `_1` and explicit release-preparation subject, otherwise fail;
4. explicit release-preparation subject at the current candidate -> create/verify semantic tag and
   dispatch the full release workflow.

The implication is one-way: **second-component change => full release**, while a full release can
happen inside the existing second-component line.

## Published-history safety

Never force-update `main`, move published tags, replace published assets/history or hide a failed
release by rewriting history. Repair forward with a new logical change.

## Owner-facing status

Project status/results are clear Russian by default. Explain any materially useful internal English
GitHub/CI labels in practical Russian: what passed/failed, whether the change is already in `main`, and
what happens next.

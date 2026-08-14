# os-zapret2-restyle — Development guide

This file answers: **How do we develop this project?**
Permanent principles: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md).
Current task: [`START_HERE.md`](START_HERE.md).
GitHub delivery: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md).

Do not store competing current project status or duplicate specialist contracts here.

## 1. Restore context with the smallest sufficient read set

Mandatory Level 1:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> current-task specialist docs`.

Then escalate only when needed:

- Level 2 `history/current/vX.Y.x.md` — richer chronology for the active minor line;
- Level 3 `history/archive/` + devlog/patches/verification/releases/decisions/audits — only for a
  concrete historical dependency, investigation, rationale or proof.

Do not reread full historical devlogs merely because a new chat/session started. Do not perform a
repository-wide audit just to reconstruct context when Level 1 names a focused task.

If the current owner instruction conflicts with active docs, apply owner canon from
`PROJECT_PRINCIPLES.md` and synchronize affected active authority. Old archives/history cannot veto a
newer settled direction.

## 2. Establish exact baseline

Use the connected GitHub plugin first. Before mutation verify:

- exact current `main` SHA;
- `VERSION` and `PLUGIN_REVISION`;
- current documented task reconciled with newest owner instruction;
- same-scope open PR state;
- relevant unpublished owner-local state if reported.

A local checkout, when used, must match the recorded GitHub baseline.

## 3. Define one logical work package

The synchronized documentation must make clear:

1. what changes and why;
2. intended result/acceptance boundary;
3. exact immediate next step;
4. current/future ordered plan affected by the change;
5. any new durable principle in `PROJECT_PRINCIPLES.md`.

Put information in its primary home:

- current fact -> `PROJECT_STATE`;
- exact handoff/current task -> `START_HERE`;
- current/future ordering -> `ROADMAP`;
- richer active-line chronology -> current version-line ledger;
- detailed execution/evidence/rationale -> devlog/patch/verification/decision only when that distinct
  record adds value.

Do **not** copy the same narrative into START_HERE + PROJECT_STATE + ROADMAP + patch + devlog. A
single current-line ledger entry may serve as the chronology for a docs/governance-only change when no
separate patch/devlog record adds information.

## 4. Audit only when scope requires it

Audit when owner requests it, roadmap schedules it, inherited behavior must be classified before
refactor/removal, a reproducible defect has unknown/cross-cutting scope, or source/current architecture
cannot be reconciled narrowly.

Otherwise proceed directly with the known-file task after baseline verification.

## 5. Implement one logical scope

- smallest maintainable change satisfying the task;
- preserve working behavior outside scope;
- affected docs belong to the same logical change;
- keep generated runtime/build output out of source control;
- same-scope repairs remain in the same branch/PR.

Packaged source change with unchanged `VERSION` increments `PLUGIN_REVISION` once. Docs/governance/
CI-only changes change neither value.

## 6. Validate

Run focused syntax/static/unit/contract tests appropriate to changed behavior, then the broader matrix
required by the task. Review complete diff. Never claim a test passed unless it ran.

For CI failure, inspect exact failed-job evidence first. Repair same-scope defects in the same PR;
external infrastructure failure causes no speculative source change. If a test encodes superseded
canon, update the stale test rather than current canon.

## 7. Reconcile documentation before publication

Before Ready PR and again before merge, verify zero-memory recovery:

- Level 1 contains only current facts, compact handoff, short lifetime path and exact next task;
- the active version-line ledger contains richer chronology when needed;
- `ROADMAP` remains current/future rather than accumulating history;
- detailed records are linked instead of copied into Level 1;
- any owner `зафиксируй` request has received a full active-authority consistency sweep;
- new permanent rules are in `PROJECT_PRINCIPLES`;
- `INDEX` routes to current ledger, every completed version-line archive and deep evidence.

Acceptance question: **could a future session with no chat/model memory resume the exact current
boundary from Level 1, then discover deeper history through links only if needed?**

## 8. Semantic-minor documentation rollover

When an explicit release changes `MAJOR.MINOR`, for example `v0.4.x -> v0.5.0_1`, perform this in the
release change without a separate reminder:

1. finish the current-line ledger through the final old-line state;
2. freeze/create `history/archive/v0.4.x.md` as a compact archive map;
3. preserve all original devlog/patch/evidence/release/decision records;
4. initialize `history/current/v0.5.x.md`;
5. update `INDEX`, `START_HERE`, `PROJECT_STATE`, short lifetime path and `ROADMAP`;
6. then proceed with normal semantic release publication.

Archiving chronology must never archive current architecture/contracts or permanent principles merely
because the version line changed.

## 9. Deliver through GitHub

Follow `GITHUB_PUBLICATION.md`:

`task branch -> implementation + docs -> validation -> Ready PR -> required checks -> exact-head squash merge -> verify main -> clean temporary branch`.

Standing owner authorization covers routine branch/PR/check/repair/merge/verification/cleanup unless
the current request explicitly stops earlier.

## 10. Package / live verification

Build/live gates apply when changed scope requires them. Use the smallest live gate that verifies the
changed risk. Owner requests for an installable testing package mean persistent GitHub `.pkg` delivery;
Actions artifacts/local files are build evidence only.

## 11. OPNsense / unpublished state

Owner console target is root `csh`; enter explicit `sh`/`/bin/sh` for POSIX-only syntax and return with
`exit`.

If relevant owner-local changes are uncommitted/unpushed, do not overwrite/reconstruct them from
memory; establish the exact transferred baseline before overlapping edits.

## Specialist workflows

Architecture, audit, lifecycle, release and verification contracts belong to specialist docs. Read
them only when the current task selects that scope.

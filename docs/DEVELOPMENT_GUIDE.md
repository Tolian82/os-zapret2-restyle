# os-zapret2-restyle — Development guide

This file answers: **How do we develop this project?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current task: `docs/START_HERE.md`.
GitHub delivery procedure: `docs/GITHUB_PUBLICATION.md`.

Do not store competing current project status or current implementation priority here.

## 1. Restore context

Read in the mandatory order from repository-root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> current-task specialist docs`.

`START_HERE` must include a short mandatory summary of the most recent completed logical work and
point to the relevant detailed patch/devlog/evidence record. This makes recent activity part of every
cold-start context without requiring a full historical devlog reread.

Do not reconstruct project state from chat history. Do not perform a repository-wide audit merely to
recover context when the handoff already names a focused task.

If the current owner instruction conflicts with `START_HERE`, `PROJECT_STATE`, `ROADMAP` or an older
specialist document, apply the owner-canon rule from `PROJECT_PRINCIPLES`: resolve only a genuine
material ambiguity, then synchronize the affected active docs before following the new direction.
Never let an older documented plan silently override a newer confirmed owner instruction.

## 2. Establish the exact baseline

Use the connected GitHub plugin first.

Before mutation verify:

- exact current `main` SHA;
- `VERSION` and `PLUGIN_REVISION`;
- current documented task/plan reconciled with the newest owner instruction;
- same-scope open PR state;
- relevant unpublished owner-local state, if the owner reports any.

A local checkout, when used, must correspond to the recorded GitHub baseline and preserve any
relevant unpublished owner state explicitly transferred into scope.

## 3. Record the work package before editing

The synchronized documentation for the logical change must state:

1. what changes and why;
2. intended effect and expected result/acceptance boundary;
3. the exact immediate next step after the delivery;
4. complete ordered next plan, including completed/superseded/deferred near-term and long-term work;
5. any new durable principle in `PROJECT_PRINCIPLES` itself.

Record affected source/docs and focused verification. Do not implement a work package that the owner
has just superseded. If `START_HERE.md` already defines one and current repository state plus the
newest owner instruction still match it, do not invent a different one.

## 4. Decide whether an audit is part of this task

An audit is **not** a universal prerequisite for every code change.

Perform or continue an audit when:

- the owner requested an audit/review;
- `START_HERE` / `ROADMAP` schedules one and no newer owner instruction supersedes it;
- refactoring/removing inherited behavior requires classification first;
- a new reproducible defect has unknown/cross-cutting scope;
- source contradicts documented architecture/state and the mismatch cannot be resolved narrowly.

When an audit applies, use existing `docs/AUDIT.md` evidence as the starting point, record findings
before remediation and keep audit/current-state/roadmap documentation synchronized.

When the current documented task is a known-file implementation and no audit condition above applies,
proceed directly to implementation after baseline verification.

## 5. Implement one logical scope

- make the smallest maintainable change that satisfies the documented task;
- preserve working behavior outside scope;
- include affected documentation in the same logical change;
- keep generated runtime/build output out of source control;
- keep same-scope corrections in the same task branch/PR.

For packaged source behavior changes with unchanged `VERSION`, increment `PLUGIN_REVISION` once.
Docs/governance-only changes change neither value.

## 6. Validate

Run the focused syntax/static/unit/contract tests appropriate to the changed behavior, then the
required broader matrix defined by the task.

When using a local checkout, review at least:

- `git status --short`;
- `git diff --check`;
- `git diff --stat`;
- complete relevant diff/staged diff.

Never claim a test passed unless it actually ran. Static/package/live verification are distinct.

For a CI failure, read exact failed-job evidence before changing source/workflow/runner. Repair a
same-scope defect in the same PR; do not change source for an external infrastructure failure.

## 7. Reconcile documentation before publication

Immediately before publishing substantive changed branch state / Ready PR and again before merge,
make the repository a self-contained **zero-memory recovery checkpoint**:

- record the most recent completed logical work in `START_HERE` and link its patch/devlog/evidence;
- confirm what changed and why;
- confirm intended effect and expected result/acceptance;
- record the exact immediate next step;
- reconcile the complete near-term and long-term plan with explicit completed/superseded/deferred
  state;
- add any newly approved durable principle to `PROJECT_PRINCIPLES`;
- reconcile all of the above against the newest owner instruction;
- update `START_HERE`, `PROJECT_STATE`, patch/evidence/devlog record and `ROADMAP` as applicable.

The acceptance question is: **could a future session with no chat/model memory, even years later,
read the mandatory startup docs and continue at the exact boundary without rediscovering settled
project intent?** If not, documentation is incomplete and publication must wait for synchronization.

A task branch may be created from the unchanged baseline before this gate. The first substantive
published changed branch state must already carry the documentation required for that logical scope.

## 8. Deliver through GitHub

Follow `docs/GITHUB_PUBLICATION.md`.

Ordinary flow:

`task branch -> implementation + docs -> focused validation -> Ready PR -> latest-head required CI -> exact-head squash merge -> verify main -> clean temporary branch`.

Standing owner authorization covers routine branch creation, PR creation, same-scope repair, CI
inspection, squash merge, main verification and cleanup unless the current request explicitly stops
at an earlier boundary.

## 9. Package and live verification

A package build/live gate is required only when the changed scope needs it. Use the smallest live gate
that verifies the changed behavior; do not expand a focused regression into a new research program
without new evidence/owner/roadmap direction.

Owner requests for a test/installable package mean persistent GitHub `.pkg` delivery under the
current publication procedure; Actions artifacts/local files are build evidence only.

## 10. OPNsense commands

Owner console target is root `csh`.

- separate read-only checks from state-changing actions;
- do not silently use bash/POSIX syntax;
- when POSIX constructs are required, enter explicit `sh`/`/bin/sh` and return with explicit `exit`;
- commands after `exit` must again be csh-valid.

## 11. Unpublished owner-local state

GitHub is authoritative only for committed/pushed state. If relevant owner-local changes are
uncommitted/unpushed, stop overlapping edits and ask the owner to commit/push or explicitly transfer
them. Establish the exact transferred baseline and never reconstruct/overwrite it from memory.

## Specialist workflows

Detailed lifecycle, audit, architecture, release and verification contracts belong to their specialist
documents. Read them only when the current task selects that scope; do not duplicate their full
matrices here.

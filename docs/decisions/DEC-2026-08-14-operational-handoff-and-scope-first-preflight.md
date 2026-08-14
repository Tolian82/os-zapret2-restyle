# DEC-2026-08-14 — Mandatory principles context, operational handoff and scope-first preflight

Status: **ACTIVE**
Date: 2026-08-14

## Context / root cause

The project already had the correct 2026-07-28 rule that documentation is part of architecture and
critical knowledge must live in the repository rather than chat/model memory.

The failure was structural:

- mandatory startup did not guarantee permanent principles were loaded;
- current-state/roadmap docs became stale while packaged source advanced;
- specialist/process docs still contained historical wording that could override the new handoff in
  practice;
- new sessions could therefore obey visible procedure yet spend hours reconstructing settled state.

Audits remain first-class work when selected by owner/current plan/refactor boundary/new evidence.

## Decision

### 1. One always-read principles layer

`docs/PROJECT_PRINCIPLES.md` is the canonical compilation of permanent principles.

Mandatory startup order:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. `docs/START_HERE.md`;
4. `docs/PROJECT_STATE.md`;
5. specialist documents explicitly named by the current task in `START_HERE.md`.

`INDEX.md` is navigation only.

### 2. Source/documentation authority is split by question

- committed source code is authoritative for actual implemented behavior;
- documentation is authoritative for approved decisions, documented project state and plan;
- a contradiction is a synchronization defect, not permission to silently choose one side;
- resolve the narrow mismatch and synchronize the affected project documents/source before continuing.

### 3. One operational handoff

`docs/START_HERE.md` must contain only what is needed to resume:

- current identity;
- current engineering conclusion;
- exact next task;
- required specialist reading for that task;
- likely source/test surfaces;
- expected result/acceptance;
- complete immediate and long-term continuation plan.

Historical rationale/evidence stays in decisions/patches/devlogs/audits/verification and is read only
when the task needs it.

### 4. Current-state docs have single responsibilities

- `START_HERE` — exact operational handoff;
- `PROJECT_STATE` — current facts/state;
- `ROADMAP` — future ordered work;
- `INDEX` — navigation;
- `PROJECT_PRINCIPLES` — permanent principles;
- `WORKING_CONVENTIONS` — procedural application of principles;
- `DEVELOPMENT_GUIDE` — repeatable development procedure.

This supersedes the **role mapping** in the 2026-07-28 `ONE DOCUMENT, ONE QUESTION` decision where the
new `PROJECT_PRINCIPLES` / `START_HERE` layers did not yet exist. The underlying single-responsibility
principle remains active.

### 5. Audit behavior is conditional, not universal startup work

Perform audits when:

- owner requests one;
- current handoff/roadmap schedules one;
- refactoring/removing inherited behavior requires prior classification;
- new reproducible evidence has unknown/cross-cutting scope;
- source materially contradicts documented architecture/state and the mismatch cannot be resolved
  narrowly.

Do not insert a context-recovery audit solely because a new chat has no memory.

### 6. Scope-first GitHub preflight

Always verify before mutation:

- current `main` SHA;
- `VERSION` / `PLUGIN_REVISION`;
- current documented task/plan;
- same-scope/relevant open PR state;
- plugin availability.

Expand inventory only when the operation requires CI/log, artifact/release, branch-hygiene,
protection/permission or broad recursive-tree evidence.

### 7. GitHub reading path is minimal

After mandatory startup, every GitHub mutation always requires only the authoritative
`docs/GITHUB_PUBLICATION.md` procedure.

Decision files are read when an operation needs their special boundary/rationale. `GITHUB_WORKFLOW.md`
is a cheat sheet, not a second mandatory authority.

### 8. Documentation gate timing

An unchanged task branch may be created after preflight.

Before the first substantive changed branch state is published, the same logical change must already
contain synchronized documentation with:

1. what changes and why;
2. expected result/acceptance boundary;
3. complete near-term and long-term/deferred plan.

Reconcile that plan before Ready-PR finalization and again before merge.

### 9. Current Model-C application

At adoption/current `_12` state:

- Model C is the selected production direction;
- source still carries automatic B/A production fallback as transition debt;
- `_13` is the next packaged source patch and removes that production fallback;
- B/A may remain as benchmark/reference/test tooling;
- do not optimize the legacy `C -> B` admission path before completing `_13`;
- accepted Lua/BLOB/discovery/lifecycle evidence remains closed unless owner/roadmap/new evidence or a
  material architecture change reopens it.

Current Strategy Lab architecture documents must describe this state, not preserve old `_23` / `_31`
selection text as if it were still current.

## Documentation contract for every delivery

Every logical delivery records:

1. what changes and why;
2. expected result and acceptance;
3. complete ordered next plan, including long-term/deferred actions.

At the end of a logical cycle update `START_HERE`, `PROJECT_STATE`, current patch/evidence and
`ROADMAP` when priority/sequencing/future/deferred work changed. Long-term work is never silently
removed; mark it completed, superseded, rejected or deferred.

## What this does not weaken

- GitHub-plugin-first transport;
- complete reading of selected required docs through EOF;
- one logical Ready PR/latest-head CI/exact-head squash merge;
- evidence-based CI failure handling;
- package/release immutability and owner-authority boundaries;
- runtime cleanup/restoration correctness;
- audits when actually required by scope.

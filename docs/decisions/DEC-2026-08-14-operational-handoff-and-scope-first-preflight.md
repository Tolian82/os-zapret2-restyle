# DEC-2026-08-14 — Mandatory principles context, operational handoff and scope-first preflight

Status: **ACTIVE**
Date: 2026-08-14

## Context / root cause

Project documentation is architecture and must allow zero-memory recovery. Earlier startup/state rules
were improved repeatedly, but the documentation/version hierarchy now has a dedicated canonical
numbered authority: `docs/DOCUMENTATION_RULES.md`.

The structural risks this decision prevents are:

- mandatory startup omitting a current authority;
- stale handoff/state/roadmap text surviving packaged-source progress;
- competing documentation-role definitions in specialist/process files;
- a new session spending hours rediscovering settled project state;
- confusing second-component state, third-component stage and `_N` patch/revision roles.

Audits remain first-class work when selected by owner/current plan/refactor boundary/new evidence.

## Decision

### 1. Mandatory Level-1 reading

Read completely:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. `docs/DOCUMENTATION_RULES.md`;
4. `docs/START_HERE.md`;
5. `docs/PROJECT_STATE.md`;
6. specialist documents explicitly named by the current task in `START_HERE.md`.

`INDEX.md` is navigation/integrity only. `ROADMAP.md` is the concise master plan and is linked from the
top of `START_HERE`.

### 2. Source/documentation authority is split by question

- committed source code is authoritative for actual implemented behavior;
- documentation is authoritative for approved decisions, current state, current task and plan;
- a contradiction is a synchronization defect, not permission to silently choose one side;
- owner canon and the “Суслик” rule control active-document reconciliation.

### 3. Version-aware operational handoff

`START_HERE.md` is the live exact `_N` revision handoff. It contains only what is needed to resume:

- first links to `PROJECT_STATE`, documentation rules, project principles, GitHub rules, master plan
  and index;
- current candidate identity;
- what was just established in the current revision and intended effect;
- exact next task and selected specialist reading;
- expected acceptance;
- immediate continuation and relevant master-plan direction.

Detailed execution chronology stays in the current ledger/deep records.

### 4. Version-aware current state

`PROJECT_STATE.md` belongs to the **second numeric component** line, for example `v0.4.x`. It stores
current durable facts for that line, not exact next-patch detail.

The **third numeric component** identifies the current development stage/task inside the line. Its
change updates `PROJECT_STATE` only when facts change and does not archive the file.

The package suffix `_N` is the exact patch/iteration boundary and primarily drives `START_HERE`.

Completed tasks flow from `START_HERE` into `PROJECT_STATE` as durable facts; detail flows into the
current ledger/deep records.

### 5. State/archive rollover

Only a second-component transition closes the current `PROJECT_STATE`. Before the transition:

- reconcile the final old state;
- preserve it in the old line archive;
- preserve every original detailed record;
- initialize current state and current ledger for the new line;
- keep direct archive links at the end of `PROJECT_STATE` and through `INDEX`.

The new final-state-snapshot model starts with the eventual `v0.4.x` archive. `v0.4.0` and older history
is not retroactively rewritten.

### 6. Master plan

`ROADMAP.md` is the complete concise plan. It retains short completed milestones, marks current work and
records every known future intention at least once, with optional sub-items. Detailed implementation
notes do not belong there.

### 7. Audit behavior is conditional

Perform audits when owner requests one, the master plan schedules one, inherited behavior must be
classified before removal/refactor, new reproducible evidence has unknown/cross-cutting scope, or
source/current architecture cannot be reconciled narrowly. Do not run a context-recovery audit merely
because conversational memory is absent.

### 8. Scope-first GitHub preflight

Before mutation verify current `main`, `VERSION`, `PLUGIN_REVISION`, current handoff/state/master plan,
same-scope/relevant PR state and plugin availability. Expand inventory only for actual CI/release/
branch/protection/broad-tree needs.

### 9. Documentation gate timing

Before the first substantive changed branch state is published, the same logical change already records
what changes and why, intended result, exact continuation and complete master-plan effects. Reconcile
again before Ready PR and before merge.

### 10. Current Model-C application

At current `v0.4.1_12`:

- Model C is selected for normal production Stage 60;
- packaged source still has automatic B/A fallback as transition debt;
- `v0.4.1_13` removes that fallback;
- B/A remain benchmark/reference/test tooling;
- accepted Lua/BLOB/discovery/lifecycle evidence remains closed absent owner/plan/new evidence/material
  architecture change.

## What this does not weaken

- GitHub-plugin-first transport;
- complete reading of selected mandatory documents through EOF;
- one logical Ready PR/latest-head CI/exact-head squash merge;
- exact-evidence CI failure handling;
- package/release immutability and owner-authority boundaries;
- runtime cleanup/restoration correctness;
- audits when scope actually requires them.

The complete normative documentation rules are numbered in `docs/DOCUMENTATION_RULES.md`; this decision
must not be used to create a competing formulation.

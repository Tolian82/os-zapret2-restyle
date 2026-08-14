# DEC-2026-08-14 — Mandatory principles context, operational handoff and scope-first preflight

Status: **ACTIVE**
Date: 2026-08-14

## Context / root cause

The project already had the correct documentation principle from 2026-07-28. `DECISIONS.md` says
critical knowledge must live in the repository rather than chat history/memory, and
`WORKING_CONVENTIONS.md` implemented the Engineering Memory workflow.

The failure was structural, not conceptual:

- `AGENTS.md` mandatory startup reading did not guarantee that `DECISIONS.md` or
  `WORKING_CONVENTIONS.md` would be read in every new context;
- `docs/INDEX.md` emphasized current Strategy Lab specialists but did not put the permanent
  principles in a mandatory always-read layer;
- `PROJECT_STATE.md` and `ROADMAP.md` later became stale (`_6/_7`) while packaged source advanced to
  `_12`;
- a new session could therefore obey the visible startup procedure while still missing settled
  permanent principles and current plan, then spend hours reconstructing them from GitHub/history.

The documentation principle itself remains unchanged. This decision changes **where permanent
principles live, what is mandatory startup context, and how current plans are kept synchronized**.

Audits remain valid first-class work whenever selected by owner/current plan/new evidence.

## Decision

### 1. One canonical always-read principles file

`docs/PROJECT_PRINCIPLES.md` is the single canonical compilation of permanent project principles.

Mandatory startup order is:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. `docs/START_HERE.md`;
4. `docs/PROJECT_STATE.md`;
5. specialist documents named by the current task.

`DECISIONS.md` retains rationale/history. `WORKING_CONVENTIONS.md` retains implementation
procedures. They must reference, not create alternative canonical principle formulations.

`docs/INDEX.md` is navigation, not an extra compulsory historical reading list.

### 2. Operational handoff

`docs/START_HERE.md` records only the information needed to resume immediately:

- current package/runtime identity;
- accepted conclusions/unresolved issues;
- current production architecture;
- exact next action;
- likely source surfaces;
- expected result/acceptance;
- immediate and long-term plan;
- owner-only blockers.

Historical evidence remains under decisions/patches/devlogs/audits/verification and is read when the
current task requires it.

### 3. Documentation contract for every GitHub delivery

Every logical delivery must have synchronized documentation that records:

1. what changes and why;
2. expected result and acceptance boundary;
3. complete ordered next plan, including near-term and long-term/deferred actions.

Immediately before publication, reconcile that plan with implementation/testing discoveries. If
scope, expected result, sequencing, audit/test needs, long-term priority or deferred status changed,
update documentation **before** publishing.

At the end of a logical cycle update at minimum:

- `START_HERE`;
- `PROJECT_STATE`;
- current patch/evidence record;
- `ROADMAP` whenever priority/sequencing/future/deferred work changed.

Long-term plans are not silently dropped: mark them completed, superseded, rejected or deferred with
reason.

### 4. Scope-first GitHub preflight

Always verify before mutation:

- current `main` SHA;
- current `VERSION` / `PLUGIN_REVISION`;
- current documented task/plan;
- same-scope/relevant open PR state;
- GitHub-plugin availability for the operation.

Expand inventory only as needed:

- CI/log state for CI debugging/current PR;
- artifacts/tags/releases/assets for package/release work;
- full branch inventory for cleanup/recovery/hygiene;
- protection/permission state when relevant;
- recursive tree for broad/cross-cutting investigation with unknown file/call path.

This amends older broad `PRE-MUTATION INVENTORY` wording. Evidence-first remains mandatory; only the
breadth becomes proportional to scope/risk.

### 5. Audit behavior

Audits are performed when:

- owner requests them;
- current `START_HERE`/`PROJECT_STATE`/`ROADMAP` schedules them;
- new reproducible evidence/architecture change requires them;
- source contradicts documented current state.

Use existing audit/evidence as starting context. Do not insert an unscheduled context-recovery audit
solely because conversational memory is absent.

### 6. Current Model-C application

Current decision/plan at adoption:

- B -> C transition is complete as engineering direction;
- source still has automatic B/A production fallback as a transition tail;
- next packaged source patch is `v0.4.1_13` Model-C-only production finalization;
- do not first implement the previously considered larger timeout-admission envelope for `C -> B`;
- retain B/A code where useful as benchmark/reference/test tooling;
- accepted Lua/BLOB/discovery/lifecycle evidence remains available and may be audited again when
  future plan/new evidence requires it.

Exact current handoff: `docs/START_HERE.md`.

## Priority / supersession

This decision controls documentation startup architecture, operational handoff, pre-publication plan
reconciliation and preflight breadth.

It does not weaken:

- canonical permanent principles in `PROJECT_PRINCIPLES.md`;
- complete reading of selected required documents through EOF;
- GitHub-plugin-first transport;
- exact current base/candidate identity;
- one logical Ready PR/latest-head CI/exact-head squash merge;
- evidence-based CI failure handling;
- package/release immutability and owner-authority boundaries;
- runtime cleanup/restoration correctness.

It supersedes only older interpretations that require broad repository/GitHub re-inventory or
historical rereading for every ordinary mutation.

## Affected controls

- `AGENTS.md`;
- `docs/PROJECT_PRINCIPLES.md`;
- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/INDEX.md`;
- `docs/WORKING_CONVENTIONS.md`;
- `docs/ROADMAP.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md` (inventory breadth amended).

# DEC-2026-08-14 — Operational handoff and scope-first preflight

Status: **ACTIVE**
Date: 2026-08-14

## Context

The repository accumulated strong evidence-first and documentation-completion rules, but their
application drifted into an expensive startup ritual. New sessions could spend hours rereading
historical documentation, enumerating every branch/workflow/run/tag/release, rebuilding a recursive
repository index and re-deriving already accepted architecture before writing code.

That behavior defeats the purpose of project documentation. Current-state documentation should let
a session resume implementation quickly. Historical evidence should remain available without being
reprocessed as a mandatory prerequisite for every ordinary patch.

The issue became visible during the long Model-B -> Model-C transition. Model C had already become
the normal production Stage-60 engine and had repeated owner-live no-fallback passes, while later
sessions continued opening additional audits/measurements and even began designing timeout handling
for the legacy C -> B fallback chain. The owner explicitly rejected that process drift and required
documentation to preserve enough operational memory for a new session to start coding quickly.

## Decision

### 1. `docs/START_HERE.md` is the authoritative operational handoff

For an ordinary continuation, mandatory startup reading is:

1. repository-root `AGENTS.md`;
2. `docs/START_HERE.md`;
3. concise `docs/PROJECT_STATE.md`;
4. only specialist documents named by the exact current task.

`docs/INDEX.md` is navigation, not a mandatory historical reading list.

The handoff must contain the current package/runtime identity, accepted conclusions, closed questions,
exact next action, likely source files, non-goals and verification boundary.

A new session must not independently re-litigate a decision recorded as accepted/closed in the
handoff unless current source contradicts it or new evidence/requirements invalidate it.

### 2. Documentation is operational memory

At the end of every logical cycle that materially changes current state or next action, update:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md` when priority/sequencing changed;
- specialist patch/evidence documents when their exact scope requires it.

Do not let `PROJECT_STATE.md` or `INDEX.md` lag several package revisions behind current `main`.

Historical detail belongs in `docs/patches/`, `docs/devlog/`, `docs/verification/evidence/` and
`docs/audit/`. Current startup documents link to those records rather than duplicating a growing
chronological ledger.

### 3. Scope-first GitHub preflight replaces exhaustive inventory for ordinary work

Always inspect before mutation:

- current authoritative `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- open PRs relevant to the same scope;
- GitHub-plugin availability for the required operation.

Inspect additional object classes **only when the requested operation depends on them**:

- workflows/runs/job logs for CI debugging or when waiting on/checking the current PR;
- tags/releases/assets/artifacts for testing-package publication or release work;
- complete branch inventory for branch cleanup, collision, recovery or hygiene work;
- rulesets/protection/permission settings only when the operation depends on them;
- historical closed PRs only when needed to resolve a specific source/evidence question.

An ordinary source or documentation patch does not require enumeration of every historical branch,
workflow, successful run, artifact, tag and release before branch creation.

This rule amends the broad `PRE-MUTATION INVENTORY` wording in
`DEC-2026-08-06-evidence-first-github-operations.md`, `AGENTS.md`, `docs/GITHUB_PUBLICATION.md` and
`docs/GITHUB_WORKFLOW.md`. Evidence-first remains active; inventory breadth is now proportional to
risk and operation type.

### 4. Recursive-tree indexing is exceptional, not startup ceremony

A pinned recursive Git tree remains useful for:

- repository-wide audits;
- cross-cutting defects where the call path/file set is unknown;
- investigations where repeated blind path discovery would otherwise dominate the work.

It is **not** the default first step for a new chat, a known-file patch, a documented next action, or
a narrow symbol-level diagnosis.

When `docs/START_HERE.md` already identifies the next source surfaces, fetch those files directly and
start implementation.

### 5. Closed experiments stay closed

Do not create a new measurement/audit merely because an older experiment appears in the roadmap or
historical evidence. The current handoff controls whether that question is open.

Reopen a closed experiment only when:

- a new reproducible production defect points to it;
- the owner changes the requirement;
- a material architecture change invalidates the old assumptions;
- current source contradicts the recorded accepted state.

### 6. Exact documented next action is an implementation handoff

When the owner asks to continue and the handoff gives an exact next code change, the session should:

1. verify current `main`, candidate metadata and same-scope PR absence;
2. fetch the named source/test files;
3. implement the documented patch;
4. validate and deliver through the ordinary Ready-PR flow.

Do not insert an unsolicited architecture audit between steps 2 and 3 unless the named source
surfaces prove the handoff impossible or materially stale.

### 7. Owner-live gates are risk-based and finite

After a source patch, use the smallest live gate that verifies the changed behavior. Do not expand a
single selected regression into a new multi-day experimental matrix unless the result exposes a new
uncertainty that materially affects correctness.

## Current application to Strategy Lab Model C

As of this decision:

- the B -> C transition is considered complete as an engineering direction;
- the current source still carries Model B and cold Model A as automatic production fallbacks;
- that fallback chain is now a legacy transition tail;
- the exact next packaged source patch is `v0.4.1_13`, whose purpose is to make Model C the only
  normal production Stage-60 runtime while retaining B/A code only where useful as
  benchmark/reference/test tooling;
- do not continue the aborted plan to improve timeout admission for `C -> B` fallback;
- do not reopen Lua, BLOB, discovery-probe or cross-batch lifecycle experiments without new evidence.

Exact implementation handoff: `docs/START_HERE.md`.

## Priority and supersession

For startup/preflight breadth and current-state recovery, authority order is:

1. current owner instruction;
2. `AGENTS.md`;
3. this decision;
4. `docs/START_HERE.md`;
5. `docs/PROJECT_STATE.md`;
6. current specialist architecture/patch/evidence documents;
7. historical records.

This decision does **not** weaken:

- GitHub-plugin-first transport;
- exact `main`/candidate identity before mutation;
- one logical branch/Ready PR/latest-head CI/exact-head squash merge;
- versioned title prefixes;
- reading the selected required documents completely through EOF;
- job-log evidence before source changes in response to CI failure;
- package/release immutability and owner-authorization boundaries;
- cleanup/restoration correctness requirements.

It supersedes only the interpretation that every ordinary mutation requires a full repository/GitHub
inventory or broad historical reread.

## Affected controls

- `AGENTS.md`;
- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/INDEX.md`;
- `docs/ROADMAP.md`;
- `docs/GITHUB_PUBLICATION.md` (inventory breadth amended by this decision);
- `docs/GITHUB_WORKFLOW.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md` (amended for inventory breadth).

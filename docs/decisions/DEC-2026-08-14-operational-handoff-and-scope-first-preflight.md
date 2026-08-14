# DEC-2026-08-14 — Operational handoff, documentation contract and scope-first preflight

Status: **ACTIVE**
Date: 2026-08-14

## Context

The repository accumulated strong evidence-first and documentation-completion rules, but their
application drifted into an expensive startup ritual. New sessions could spend hours rereading
historical documentation, enumerating every branch/workflow/run/tag/release, rebuilding a recursive
repository index and re-deriving already accepted architecture before writing code.

That behavior defeats the purpose of project documentation. Documentation is part of the project and
must function as its operational memory: what changed, why it changed, what outcome is expected, what
has already been proven, what remains open and what the complete next plan is.

The issue became visible during the long Model-B -> Model-C transition. Model C had already become
the normal production Stage-60 engine and had repeated owner-live no-fallback passes, while later
sessions continued reconstructing context and opening additional lines of investigation before
following the already established plan. The owner requires future sessions to orient by current
project documentation first and to begin the documented work promptly.

This decision does **not** prohibit audits. Audits remain valid whenever the documented plan selects
one, the owner requests one, or new evidence requires one. The problem being corrected is redundant
context reconstruction and unscheduled re-analysis caused by stale or incomplete operational docs.

## Decision

### 1. `docs/START_HERE.md` is the authoritative operational handoff

For an ordinary continuation, startup reading is:

1. repository-root `AGENTS.md`;
2. `docs/START_HERE.md`;
3. concise `docs/PROJECT_STATE.md`;
4. specialist documents named by the exact current task.

`docs/INDEX.md` is navigation, not a mandatory historical reading list.

The handoff must contain:

- current package/runtime identity;
- accepted conclusions and unresolved issues;
- current production architecture;
- exact next action;
- likely source files;
- expected result/acceptance boundary;
- immediate follow-up actions;
- longer-term plan and deferred items;
- blockers requiring owner input.

Historical patches, audits, devlogs and evidence remain authoritative project records and must be
read when the current task/plan points to them. They are not automatically reprocessed only because
a new chat started.

### 2. Documentation is part of every project delivery

Every logical GitHub delivery must be accompanied by documentation that answers three questions:

1. **What are we changing and why?**
   Concrete scope, trigger/root reason and important non-goals.
2. **What result do we expect after the patch?**
   Intended runtime/user result plus automated/live acceptance criteria.
3. **What do we do after that?**
   The complete ordered plan: immediate follow-up, next work, longer-term actions and explicitly
   deferred ideas.

This is not optional release-note prose. It is the continuity contract for the next session.

At the end of a logical cycle, update at minimum:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- the current patch/evidence record;
- `docs/ROADMAP.md` whenever priority, sequencing, future actions or deferred plans changed.

Do not let `PROJECT_STATE.md`, `INDEX.md`, or the handoff lag several package revisions behind
current `main`.

Historical detail belongs under `docs/patches/`, `docs/devlog/`, `docs/verification/evidence/` and
`docs/audit/`; startup documents summarize/link it instead of becoming an ever-growing chronological
ledger.

### 3. Mandatory plan reconciliation before GitHub publication

Immediately before publishing a branch/PR or equivalent GitHub delivery, reread the current plan and
compare it with what was actually learned while implementing the change.

Check explicitly:

- is the documented patch scope still correct?;
- is the expected result still correct?;
- did implementation/testing change the next immediate action?;
- did any long-term priority or dependency change?;
- did a new audit/test become necessary?;
- did an earlier planned audit/test become unnecessary or move later?;
- did any deferred idea become active or vice versa?

If the plan changed, update the documentation **before** the GitHub publication. Only then publish,
merge or package the change.

Long-term plans are never silently dropped. When they are superseded, postponed or rejected, record
that explicitly with the reason.

### 4. Scope-first GitHub preflight replaces exhaustive inventory for ordinary work

Always inspect before mutation:

- current authoritative `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- open PRs relevant to the same scope;
- GitHub-plugin availability for the required operation;
- the current operational handoff/plan.

Inspect additional object classes only when the requested operation depends on them:

- workflows/runs/job logs for CI debugging or current-PR check handling;
- tags/releases/assets/artifacts for testing-package publication or release work;
- complete branch inventory for branch cleanup, collision, recovery or hygiene work;
- rulesets/protection/permission settings when the operation depends on them;
- historical closed PRs when needed to resolve a specific source/evidence question.

An ordinary source or documentation patch does not require enumeration of every historical branch,
workflow, successful run, artifact, tag and release before branch creation.

This amends the broad `PRE-MUTATION INVENTORY` wording in
`DEC-2026-08-06-evidence-first-github-operations.md`, `AGENTS.md`, `docs/GITHUB_PUBLICATION.md` and
`docs/GITHUB_WORKFLOW.md`. Evidence-first remains active; inventory breadth is proportional to the
operation and risk.

### 5. Recursive-tree indexing is a tool, not mandatory startup ceremony

A pinned recursive Git tree remains useful for:

- repository-wide audits;
- cross-cutting defects where the call path/file set is unknown;
- investigations where repeated blind path discovery would otherwise dominate the work.

It is not automatically required for a known-file patch or documented next action. When the handoff
already identifies the relevant source surfaces, fetch them directly.

If the documented next action itself is a broad audit, use the recursive-tree method when it makes
that audit faster and more reliable.

### 6. Audits follow the project plan

Audits are first-class project work, not prohibited work.

Perform an audit when:

- the owner requests it;
- `START_HERE`/`PROJECT_STATE`/`ROADMAP` schedules it;
- a new reproducible defect or architecture change makes it necessary;
- current source contradicts recorded project state.

When prior audit/evidence already exists, start from that documentation rather than assuming no work
has been done. If an audit is not in the current plan and no new evidence calls for it, do not insert
one solely because a new chat lacks conversational memory.

### 7. Exact documented next action is an implementation handoff

When the owner asks to continue and documentation gives an exact next task, the session should:

1. verify current `main`, candidate metadata and same-scope PR state;
2. read the named specialist documents/source surfaces;
3. perform the documented task — audit, implementation, test or publication as applicable;
4. update the three-part documentation contract;
5. reconcile the full plan;
6. deliver through the ordinary Ready-PR flow.

Do not substitute a different task without new evidence or an explicit plan update.

### 8. Owner-live gates remain risk-based and finite

After a source patch, use the selected live gate documented for that change. Expand it when results
show a material new uncertainty; do not automatically create a new experimental series merely
because live testing exists.

## Current application to Strategy Lab Model C

As of this decision:

- the B -> C transition is complete as an engineering direction;
- current source still carries Model B and cold Model A as automatic production fallbacks;
- the fallback chain is a legacy transition tail to be finalized;
- exact next packaged source patch is `v0.4.1_13`: make Model C the only normal production Stage-60
  runtime while retaining B/A code where useful as benchmark/reference/test tooling;
- the previously considered timeout-admission fix for `C -> B` fallback is not the current plan;
- accepted Lua/BLOB/discovery/lifecycle conclusions remain current evidence, but audits of them are
  allowed whenever future plans or new evidence require it.

Exact implementation handoff and full near/long-term plan: `docs/START_HERE.md`.

## Priority and supersession

For startup/preflight breadth and current-state recovery:

1. current owner instruction;
2. `AGENTS.md`;
3. this decision;
4. `docs/START_HERE.md`;
5. `docs/PROJECT_STATE.md`;
6. current specialist architecture/patch/evidence documents;
7. historical records.

This decision does not weaken:

- GitHub-plugin-first transport;
- exact `main`/candidate identity before mutation;
- one logical branch/Ready PR/latest-head CI/exact-head squash merge;
- versioned title prefixes;
- complete reading of the selected required documents through EOF;
- job-log evidence before source changes in response to CI failure;
- package/release immutability and owner-authorization boundaries;
- cleanup/restoration correctness requirements.

It supersedes only the interpretation that every ordinary mutation requires a full repository/GitHub
inventory or broad historical reread, and it adds the mandatory three-part documentation and
pre-publication plan-reconciliation contract.

## Affected controls

- `AGENTS.md`;
- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/INDEX.md`;
- `docs/ROADMAP.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md` (inventory breadth amended).

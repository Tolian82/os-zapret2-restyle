# os-zapret2-restyle — START HERE

Status: **AUTHORITATIVE OPERATIONAL HANDOFF**
Updated: 2026-08-14

This file answers one question: **What must the next session know to resume immediately?**

Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`.

## Mandatory startup

Read completely through EOF, in this order:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. this file;
4. `docs/PROJECT_STATE.md`;
5. the specialist documents named under **Required specialist reading for current task** below.

Use `docs/INDEX.md` only when more navigation/history is actually needed.

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- branch authority: current `main` — resolve exact SHA at session start;
- `VERSION=0.4.1`;
- packaged source `PLUGIN_REVISION=12`;
- testing package: `os-zapret2-restyle-0.4.1_12.pkg`;
- testing tag: `v0.4.1_12`;
- packaged runtime/source commit: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- required ABI: `FreeBSD:15:amd64`;
- owner console: root `csh`.

Documentation-only `main` may be newer than the packaged source commit. Source code is authoritative
for actual behavior; documentation is authoritative for approved decisions/state/plan. If they
contradict, treat that as a synchronization defect and resolve the narrow mismatch before proceeding.

## Current engineering conclusion

The B -> C transition is complete as an engineering direction.

Current source still contains the transitional production chain:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`

Model C is the selected production direction. B/A automatic production fallback is a legacy
transition tail, not a long-term requirement. B/A code may remain where useful as benchmark,
reference or test tooling.

Accepted evidence already established:

- Model C normal production integration and source-port dispatch;
- source-port leasing/collision correction;
- finite `eligible-work-v1` adaptive budgets;
- Lua/BLOB/discovery measurements with no further production optimization justified;
- `_11` profile-compatible physical segmentation while preserving logical planner batches;
- `_12` readiness polling corrective;
- latest `_12` lifecycle replay: 5/5 Model-C-only, no fallback, cleanup/restoration PASS;
- cross-batch keep-warm/reuse not justified by current measured cost/jitter.

Durable latest evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Required specialist reading for current task

Before editing `_13`, read these current architecture contracts completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Historical patch/evidence files are supporting references only unless a concrete implementation
question requires them.

# Exact next code change — `v0.4.1_13`

## 1. What changes and why

Make Model C the **only normal production Stage-60 runtime**.

Required implementation:

- normal `strategy_lab_python.py stage60-parallel ...` path uses Model C only;
- remove silent production replay of the same work through Model B/cold Model A;
- Model-C infrastructure/selector/rendering/readiness/attribution failures remain explicit and bounded;
- remove production-only lease/fallback plumbing that exists solely for B/A replay;
- keep B/A implementation only where useful as benchmark/reference/test tooling;
- preserve current Model-C leasing, exact attribution, `_11` segmentation, `_12` readiness,
  candidate identity/search semantics, adaptive budgets, GET-4K discovery, cleanup and Stage-90
  semantic restoration.

Start from these source/test surfaces:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- narrow search hits that directly encode production `C -> B -> A` semantics.

Metadata:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- title/commit prefix `v0.4.1_13:`.

**Do not spend the next patch improving timeout admission for `C -> B`; finish the transition first.**
The previously observed legacy `C -> B` admission gap becomes irrelevant if automatic B fallback is
removed. A Model-C-only timeout/deadline audit remains valid later if the owner/roadmap/new evidence
selects it.

## 2. Expected result

Automated acceptance:

- normal production Stage 60 is Model-C-only;
- no silent Model-B/cold-Model-A replay after Model-C infrastructure failure;
- injected Model-C infrastructure failure is explicit and bounded;
- cleanup works on success/failure/cancel paths;
- source-port leasing/attribution and `_11` segmentation remain correct;
- complete Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

Owner-live acceptance after testing-package publication:

- one selected normal OPNsense Model-C-only regression;
- expected result handling;
- cleanup/restoration PASS;
- no temporary IPFW/process/socket residue.

## 3. Complete further plan

1. implement `_13` directly from the files/contracts above;
2. run focused Model-C-only regression and full corrective matrix;
3. qualify the FreeBSD 15 package;
4. reconcile `START_HERE`, `PROJECT_STATE`, `ROADMAP` and `_13` patch documentation against what the
   implementation/tests actually learned;
5. Ready PR -> latest-head checks -> exact-head squash merge -> verify `main`;
6. publish deterministic `_13` testing `.pkg` when owner testing/package delivery is requested;
7. run one selected owner-live Model-C-only regression;
8. record live evidence and close the B -> C transition on PASS;
9. return to `docs/ROADMAP.md` and select the next product/Strategy-Lab work by owner priority;
10. retain long-term/deferred work explicitly; do not silently drop it.

## New-session execution rule

When the owner says `продолжаем` or equivalent:

1. perform the mandatory startup reading above;
2. verify current `main`, `VERSION`, `PLUGIN_REVISION` and same-scope open PR state;
3. if repository state still matches this handoff, start the documented `_13` code task;
4. if a future handoff names an audit, audit; if it names code, code;
5. expand to broad repository/history inventory only when the documented task actually requires it.

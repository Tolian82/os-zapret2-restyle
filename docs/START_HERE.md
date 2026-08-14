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

Documentation-only `main` may be newer than the packaged source commit.

## Locked owner canon — do not reopen from old docs/tests

These facts/directions are settled and remain current until the owner explicitly changes them or
fresh direct reproducible evidence contradicts a factual claim:

1. **DNS is fixed.** The previous local/container DNS path used to be slow and flaky, but the owner
   fixed it. Treat DNS as working. Do not ask again whether it was fixed and do not reuse historical
   DNS failures as a current diagnosis without new direct evidence.
2. **Model C is selected.** A/B/C production model selection is closed. Model C is the selected normal
   production Stage-60 direction. Model A/B are reference/test implementations; current `_12` B/A
   automatic fallback is transition debt scheduled for removal in `_13`, not an alternative design.
3. **A stale document/test is a defect, not counter-authority.** If old current-active text or a CI
   assertion contradicts owner canon, update the stale text/contract. Never weaken current canon to
   satisfy it.
4. **`Зафиксируй` means full reconciliation.** When the owner says to record a new fact/decision, all
   active authority documents capable of contradicting it are reviewed and corrected in that first
   documentation change.
5. **Owner-facing status is clear Russian.** Internal GitHub/CI terms are translated/explained rather
   than left for the owner to decode.
6. **Routine repository cleanup is part of the task.** Useful unique work is preserved; obsolete
   temporary branches are removed without making ordinary cleanup an owner problem.

Decision authority:
`docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`.

## Most recent completed logical work

The latest logical work before the next packaged source patch is the **canon-lock and active-
documentation reconciliation**. It is docs/governance-only and keeps package identity `0.4.1_12`.

Why it was needed:

- the previous continuity corrective had correctly recorded fixed DNS and selected Model C in the
  current handoff/state/roadmap;
- however, a broad active-document review found three current/current-looking authorities that could
  still revive obsolete Model-B selection;
- leaving them unchanged meant a future cold-start session could still read old A/B/C selection as
  active despite newer owner canon.

Corrected active/current-looking documentation:

- `docs/ARCHITECTURE.md` now describes current Python/Model-C architecture and explicitly says A/B/C
  selection is closed;
- `docs/architecture/STRATEGY_LAB.md` is now a current-state base contract and no longer delegates
  production runtime choice to the historical A/B/C experiment plan;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` is now explicitly
  **HISTORICAL / COMPLETED**, preserves the experiment/evidence chain, and cannot present the former
  Model-B selection as current architecture.

Durable records:

- `docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`;
- `docs/patches/v0.4.1_12-owner-canon-lock-doc-audit.md`;
- `docs/devlog/2026-08-14-owner-canon-lock-doc-audit.md`.

## Current engineering state

Current packaged `_12` source still contains this implementation chain:

`Model C -> Model B -> Model A cold`

This is **implementation transition debt only**.

The approved production architecture is already decided:

**Model C only for normal production Stage 60.**

Accepted Model-C behavior that `_13` must preserve:

- immutable CandidateSpec and job-scoped ResourceInventory;
- bounded native adaptive search graph;
- logical candidate width at most three;
- exact source-port-qualified attribution;
- pinned endpoints sequential inside one candidate;
- `preferred-free-else-alternate` source-port leasing;
- profile-compatible physical segmentation while preserving logical planner batch identity;
- readiness from process identity + socket + clean log + two consecutive qualified snapshots;
- 25 ms readiness polling, bounded by 4 s;
- bounded GET-4K discovery;
- finite `eligible-work-v1` parent budgets;
- cleanup on success/failure/cancel;
- Stage-90 exact semantic restoration.

Accepted measurement conclusions remain closed unless owner/roadmap/material architecture change/new
direct evidence reopens them:

- Lua initialization: no production change justified;
- BLOB startup/RSS/common set: no lazy-BLOB production change justified;
- discovery: keep bounded GET-4K;
- cross-batch keep-warm/reuse: not justified for current architecture.

Latest live evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Required specialist reading for current task

Before editing `_13`, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

The rewritten `docs/ARCHITECTURE.md` and `docs/architecture/STRATEGY_LAB.md` are current active
architecture. `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` is historical evidence.
None may be interpreted to reopen A/B/C selection.

# Exact next code change — `v0.4.1_13`

Unless the owner gives a newer instruction, implement Model-C-only production finalization.

## What changes

- normal `strategy_lab_python.py stage60-parallel ...` path uses Model C only;
- remove silent replay of the same production work through Model B/cold Model A;
- Model-C infrastructure/selector/rendering/readiness/attribution failures remain explicit/bounded;
- remove production-only fallback plumbing that exists solely for B/A replay;
- retain B/A only where useful as benchmark/reference/test tooling;
- preserve planner/search semantics, CandidateSpec/ResourceInventory, leasing/attribution, `_11`
  segmentation, `_12` readiness, adaptive budgets, GET-4K discovery, cleanup and Stage-90 restoration.

Start from:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- narrow current search hits that encode production `C -> B -> A` semantics.

Metadata:

- keep `VERSION=0.4.1`;
- increment packaged source `PLUGIN_REVISION 12 -> 13`;
- title/commit prefix `v0.4.1_13:`.

**do not spend the next patch improving timeout admission for `C -> B`; remove the transition instead.**

## Expected result

Automated acceptance:

- normal production Stage 60 is Model-C-only;
- no silent Model-B/cold-Model-A replay;
- injected Model-C infrastructure failure is explicit and bounded;
- cleanup succeeds on success/failure/cancel;
- leasing/attribution and physical segmentation remain correct;
- complete Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

Owner-live acceptance after testing-package publication:

- one selected normal Model-C-only OPNsense regression;
- correct result handling;
- cleanup/restoration succeeds;
- no temporary IPFW/process/socket residue.

## Complete further plan

1. implement `_13`;
2. run focused Model-C-only regression and complete corrective matrix;
3. qualify FreeBSD 15 package;
4. update zero-memory documentation with what `_13` actually changed/verified;
5. publish Ready PR, complete required checks and squash-merge exact verified head;
6. verify `main` and clean temporary branch automatically;
7. publish deterministic `_13` testing package when owner testing/package delivery is requested;
8. run one owner-live Model-C-only regression;
9. record evidence and close fallback-removal transition on PASS;
10. select next product/Strategy-Lab work from the current roadmap without reopening A/B/C selection.

## New-session execution rule

When the owner says `продолжаем` or equivalent:

1. read mandatory startup docs;
2. accept the locked canon above without reconfirmation unless the current owner message changes it;
3. verify current `main`, `VERSION`, `PLUGIN_REVISION` and same-scope PR state;
4. if repository state still matches this handoff, start `_13` directly;
5. if a current active document/test contradicts the locked canon, correct the stale authority rather
   than asking whether the settled decision still applies.

# Strategy Lab adaptive-search experiment history

Status: **HISTORICAL / COMPLETED — NOT CURRENT ARCHITECTURE AUTHORITY**

==================================================
DOCUMENT ROLE
==================================================

This file preserves the experiment sequence that led from the cold Model-A reference through
Model-B measurements to the selected Model-C production direction.

It is **not** a current model-selection plan. Present-tense statements from the original experiment
plan such as “Model B is selected” or “Model C is future” are superseded historical snapshots.

Current authority:

- `docs/PROJECT_PRINCIPLES.md` — owner canon and permanent rules;
- `docs/START_HERE.md` — exact current handoff;
- `docs/PROJECT_STATE.md` — current factual state;
- `docs/ROADMAP.md` — current plan;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — selected Model-C runtime contract;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — current search semantics;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — current budget contract.

**Current locked conclusion: Model C is selected for normal production Stage 60. A/B/C production
model selection is closed.** Packaged source through `v0.4.1_12` still contains automatic B/A
fallback only as transition debt. `v0.4.1_13` removes that fallback.

The historical local/container DNS slowness/failure is also closed because the owner fixed DNS.
Old DNS timing/failure observations below or in linked evidence are historical and cannot be used as
a current diagnosis without fresh direct reproducible evidence.

The complete pre-archive experiment-plan text remains permanently available in Git history at
commit `938d01bca0617d4dad6e4715e637ebd2a3cb11f4` under this same path. The current tree keeps the
results/evidence index below so future work does not need to treat the superseded experiment plan as
active architecture.

==================================================
HISTORICAL MODEL-SELECTION SEQUENCE
==================================================

## Model A — cold reference

Model A established correctness and cold-runtime timing. It remains useful as a reference/test
implementation, not as a competing normal production path.

Key retained evidence:

- package/job: `v0.4.0_11` / `job.TtZeaH`;
- 25 retained cold candidate samples;
- candidate median/p90/max: 1580 / 3411 / 3463 ms;
- readiness median/p90/max: 1046 / 1052 / 1138 ms;
- RSS minimum/median/p90/max: 4316 / 4332 / 4348 / 4356 KiB;
- restoration verified and temporary runtime clean.

Evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

## Model B — warm coexistence and bounded candidate parallelism

Model B proved that several isolated warm workers could coexist deterministically, then measured the
benefit of sequential and controlled width-three candidate execution.

Historical accepted chain:

- `_16`: first owner-live warm-coexistence ACCEPT;
- `_17`: 5/5 reproducibility;
- `_19`: sequential exhaustive ACCEPT 5/5, mean 74808.2 ms, about 15.96% measured candidate-runtime
  improvement versus the retained cold reference;
- `_21`: controlled parallel candidate execution accepted with exact source-port-qualified ownership;
- `_22`: production integration of the then-selected Model-B architecture.

The `_21` controlled-parallel series measured approximately 33025.6 ms mean Stage-60 candidate
runtime, about 62.90% lower than the cold Model-A reference and about 55.85% lower than sequential
warm Model B, with roughly 13 MiB aggregate RSS.

Historical Model-B production evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

This evidence remains valuable because it established isolation, attribution, cleanup and performance
baselines. It **does not** mean Model B is the current selected production architecture.

## Model C — source-port dispatcher and final selection

Model C replaced multiple candidate workers with source-port-qualified dispatch through compatible
warm physical workers while preserving exact candidate identity.

Selection/acceptance work established:

- source-port-qualified dispatcher behavior;
- exact IPFW/Lua attribution;
- source-port leasing/collision correction;
- bounded logical width at most three;
- pinned endpoints sequential inside one candidate;
- profile-compatible physical segmentation while preserving logical planner batches;
- readiness proof using process identity, socket readiness, clean startup log and two consecutive
  qualified snapshots;
- cleanup/cancellation/restoration safety.

Key evidence:

- source-port acceptance:
  `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- adaptive-budget acceptance:
  `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- latest readiness/lifecycle replay:
  `docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

**Result: Model C is selected.** Any older experiment wording that describes Model B as the current
production selection or Model C as merely future is superseded history.

==================================================
POST-SELECTION MEASUREMENT HISTORY
==================================================

After Model C became the production direction, focused experiments answered narrower performance
questions without reopening model selection.

## Lua initialization

Conclusion: no production reduction/change justified for the current architecture.

Evidence:
`docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

## BLOB startup / RSS / common-set scaling

Conclusion: no material current-width startup/RSS penalty was measured that justified lazy-BLOB
production loading or a smaller common set.

Evidence:

- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`.

## Discovery probe depth

Conclusion: retain bounded GET-4K production discovery. HEAD/GET-1 alternatives did not justify a
production change.

Evidence:
`docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`.

## Lifecycle / readiness / cross-batch reuse

The `_7` through `_12` series isolated lifecycle/startup/readiness behavior. `_11` corrected
profile-compatible physical segmentation; `_12` corrected readiness polling. After those corrections,
cross-batch keep-warm/reuse was not justified by the measured current cost/jitter.

Latest evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

These conclusions remain closed until the owner/current roadmap, a material architecture change, or
fresh direct reproducible evidence explicitly reopens them.

==================================================
EXPERIMENT SAFETY PRINCIPLES RETAINED
==================================================

The completed experiment program established reusable verification principles that remain valid:

- compare like-for-like candidate corpus, endpoint identity and probe semantics;
- record CPU/model/load as context, never as a silent semantic gate;
- prove exact candidate traffic ownership before accepting a faster runtime;
- a performance gain cannot compensate for false PASS/FAIL, cross-candidate leakage or cleanup
  failure;
- source-port plans must be unique/free/bounded where used for attribution;
- pinned endpoints remain sequential within one candidate unless a later approved architecture
  explicitly changes that contract;
- cleanup/restoration evidence is mandatory for runtime experiments;
- historical results are evidence, not current product authority.

==================================================
CURRENT CONTINUATION
==================================================

The experiment-selection phase is complete.

Current packaged source: `v0.4.1_12`.

Exact next source change: `v0.4.1_13` — remove the legacy automatic Model-B/cold-Model-A production
replay so Model C is the only normal production Stage-60 runtime while preserving the already accepted
search semantics, attribution, leasing, segmentation, readiness, budgets, cleanup and restoration.

Do not use this historical experiment file to reopen A/B/C selection or to restore an older
experiment sequence as the current roadmap.

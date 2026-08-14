# os-zapret2-restyle — Current state

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **Where is the project now?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Exact continuation handoff: `docs/START_HERE.md`.
Future work: `docs/ROADMAP.md`.

## Repository / package identity

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- semantic version: `0.4.1`;
- current packaged source revision: `12`;
- package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing tag: `v0.4.1_12`;
- package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`.

Documentation-only `main` may be newer than the packaged source merge. Always resolve the actual
`main` SHA before mutation.

## Current governance / continuity facts

- the owner's newest unambiguous/confirmed instruction is current intended project canon and
  supersedes conflicting older active documentation;
- all newly approved durable development principles must be added to
  `docs/PROJECT_PRINCIPLES.md` in the first synchronized documentation change;
- every substantive GitHub delivery is a zero-memory recovery checkpoint; current continuation is
  summarized in `docs/START_HERE.md`, with detailed chronology in patch/devlog/evidence records;
- the historical local/container DNS problem is **closed**. DNS previously worked slowly and with
  failures; the owner fixed it. Treat DNS as currently working and do not diagnose a new failure as
  the old DNS problem without fresh reproducible evidence.

Detailed continuity decision:
`docs/decisions/DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`.

## Current production behavior and approved direction

Actual current source enters Model C first but still retains automatic legacy fallback:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

Approved owner direction:

- **Model C is the final normal production Stage-60 runtime**;
- automatic Model-B / cold-Model-A replay is a legacy transition tail, not a requirement capable of
  blocking or reversing the Model-C decision;
- B/A may remain as benchmark/reference/test tooling;
- the next packaged source patch removes B/A from the production fallback chain instead of improving
  that chain further.

This is not a contradiction: the source describes current implementation; the documentation records
that the remaining fallback is scheduled transition debt. If source and this approved state diverge
in another way, treat it as a synchronization defect and resolve it narrowly.

## Model-C behavior that is already accepted and must be preserved

- native adaptive graph/planner and immutable CandidateSpec identity;
- job-scoped ResourceInventory semantics;
- candidate width at most three;
- exact source-port-qualified attribution;
- pinned endpoints sequential inside one candidate;
- `preferred-free-else-alternate` source-port leasing;
- `_11` logical-batch preservation with profile-compatible physical segmentation;
- `_12` readiness: process identity + socket readiness + clean log + two consecutive qualified
  snapshots, 25 ms polling, bounded by 4 s;
- production discovery GET-4K;
- finite `eligible-work-v1` adaptive budgets;
- bounded cancellation/cleanup and Stage-90 semantic restoration;
- downstream Stage 70/80/85/result ownership.

## Accepted live evidence

Production baseline `v0.4.0_26`, Extended `telegram.org`, `job.xhdgCU`:

- Model C 16/16, graph exhausted, zero winners;
- no fallback;
- Stage 60 `34209 ms`;
- Stage-90 restoration PASS;
- normal Zapret2 remained running;
- no temporary rule residue.

Latest readiness/lifecycle evidence `v0.4.1_12`, retained job replay:

- 5/5 completed;
- 5/5 `model_c_only=true`;
- no fallback;
- lifecycle/RSS evidence complete;
- cleanup/restoration PASS;
- physical-segment startup median `82.5 ms`;
- median aggregate RSS `4366 KiB`.

Strict lifecycle `measurement_rejected` reflected live candidate-result variation between repeats,
not Model-C infrastructure failure.

Evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Closed measurement questions

These conclusions remain accepted until the owner/current roadmap/new reproducible evidence or a
material architecture change reopens them:

- Lua initialization (`_2`): no production change justified;
- BLOB startup/RSS and common-set scaling (`_3/_4`): no material current-width penalty; no lazy-BLOB
  production change;
- discovery (`_5/_6`): retain bounded GET-4K;
- cross-batch lifecycle (`_7` through `_12`): `_11/_12` fixed real defects; further keep-warm/reuse
  architecture not justified by current measurements.

Do not reopen these merely because a new chat lacks conversational memory.

## Most recent docs/governance corrective

The current docs-only continuity corrective does not change package/runtime code or metadata. It
closes the owner-canon/DNS/zero-memory documentation gaps and records the latest work in:

- `docs/patches/v0.4.1_12-owner-canon-zero-memory-checkpoint.md`;
- `docs/devlog/2026-08-14-owner-canon-zero-memory-checkpoint.md`.

## Current next packaged source change — `v0.4.1_13`

**Make Model C the only normal production Stage-60 runtime.**

Scope summary:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure failures explicit/bounded;
- preserve leasing, attribution, segmentation, readiness, budgets, cleanup and restoration;
- retain B/A code only where still useful outside the normal production path.

Exact implementation files, required specialist reading, acceptance and complete further plan are in
`docs/START_HERE.md`. A newer explicit owner instruction supersedes this priority and must be
synchronized here/there before implementation.

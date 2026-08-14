# Strategy Lab adaptive native-Zapret2 search architecture

Status: **CURRENT**

This file answers: **What search semantics must Stage 50/60 preserve while runtime execution evolves?**

Historical `_28..._33` planning text is superseded by the implemented/current contract below.
Implementation chronology remains in `docs/patches/`, `docs/devlog/` and verification evidence.

Read after:

- `docs/PROJECT_STATE.md`;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` when migration history is relevant.

Read with:

- `docs/architecture/STRATEGY_LAB_MODEL_C.md` for current Stage-60 runtime execution;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` for parent-budget ownership.

## Technical boundary

Strategy Lab searches native `bol-van/zapret2` mechanisms only.

The stable boundary is:

`Python planner / CandidateSpec / ResourceInventory / evidence -> narrow system adapter -> FreeBSD IPFW/divert + dvtws2 -> bounded probe -> Python classification/next decision`.

Shell/runtime adapters do not choose the next candidate, expand the search graph or silently invent
strategy semantics.

## CandidateSpec

Each candidate is one immutable normalized identity containing enough information to reproduce the
exact tested strategy, including as applicable:

- stable candidate ID and provenance;
- L3/transport/destination-port/L7 requirements;
- ordered Lua action list and arguments;
- split/marker/position/seqovl/fake parameters;
- optional input/output ranges;
- BLOB/Lua/resource dependencies;
- target/endpoint-binding requirement;
- cost/complexity metadata.

`family` is diagnostic/ordering metadata, not authorization. Stage-50 family evidence may influence
priority but must not turn the Stage-60 graph into an allowlist.

There is no implicit `--out-range=-d10` rule. A candidate carries its own exact range or none.

## ResourceInventory

At job initialization Python records one immutable job-scoped view of installed/available resources:

- `/usr/local/etc/zapret2/lua/*.lua`;
- `/usr/local/etc/zapret2/files/fake/*.bin`;
- supported built-in BLOB names;
- inline patterns requiring no external file.

Presence of a resource means available, not required by every candidate. Search eligibility remains
semantic and does not create Cartesian combinations from unrelated installed files.

Resource classes remain:

1. BLOB-free;
2. built-in BLOB;
3. inline `0x...` value/pattern;
4. external installed `.bin`.

Candidate functional dependencies are part of reproducibility; runtime preload policy is an execution
optimization and must not alter CandidateSpec identity.

## Search graph

Stage 50 is low-cost reconnaissance/evidence, not a hard family gate.

Stage 60 performs bounded adaptive graph exploration:

- current-job PASS/FAIL evidence changes priority/reachability of compatible neighbors;
- stronger variants remain reachable after simple failure;
- inexpensive success does not prohibit alternatives;
- protocol/resource incompatibility prunes meaningless work;
- the planner records why a node was scheduled/skipped/pruned/deferred;
- graph work remains bounded by absolute stage/job budgets and cancellation;
- normal output targets up to three stable winners while truthful smaller output remains valid.

The search intentionally avoids a full Cartesian product.

## Endpoint epoch / baseline

A clean baseline precedes search.

If the target already works directly under the required baseline contract, return
`TARGET_ACCESSIBLE`; do not search for an unnecessary bypass.

For one search epoch:

- resolve/select endpoint identity once and persist it;
- preserve original hostname/SNI identity;
- candidate probes use the pinned endpoint set;
- a deliberate re-resolution creates a new recorded epoch rather than silently changing targets.

Candidate execution performs no hidden DNS selection that would invalidate comparison.

## Discovery / stability / result boundary

Current production discovery remains the bounded 4 KiB GET selected after the `_5/_6` measurement
cycle. HEAD/GET-1 did not justify a production change.

Stability/final result logic remains owned by Python/downstream stages and must preserve exact
CandidateSpec, endpoint/resource identity and execution evidence. Runtime acceleration must not turn
an infrastructure failure into a candidate PASS/FAIL result.

Historical finalist/deep-validation proposals are not automatic current requirements merely because
they appeared in an old target-design sequence; current implemented behavior and current task docs
control.

## Current runtime selection

The old A/B/C comparison is **closed as a selection question**.

- Model A: retained correctness/reference implementation;
- Model B: retained warm/reference implementation and, through `_12`, legacy automatic fallback;
- Model C: selected normal production Stage-60 runtime.

Actual `_12` source still has `C -> B -> A` fallback. `v0.4.1_13` removes B/A from the normal
production fallback chain while preserving this search architecture.

Do not treat A/B/C as three still-competing production options in a new session.

## Model-C execution constraints inherited from search semantics

Model C may accelerate one planner-selected logical batch, but must preserve:

- candidate order and identity;
- maximum logical width three;
- exact source-port-qualified attribution;
- pinned endpoints sequential inside one candidate;
- logical-batch evidence boundary even when `_11` requires multiple physical compatible segments;
- `_12` readiness proof;
- cleanup/cancellation/restoration ownership.

See `docs/architecture/STRATEGY_LAB_MODEL_C.md` for the current physical runtime contract.

## Timeout / admission architecture

Containment invariant remains:

`bounded child operation <= stage parent <= finite job parent`.

Candidate/operation admission uses remaining absolute budget; cleanup/restoration is never made
unbounded to gain more search time.

The current parent-budget policy is `eligible-work-v1`; see
`docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

A previously observed containment question concerned the transitional `C -> B` replay path. Do not
optimize that legacy transition before `_13`. After Model-C-only finalization, a timeout/deadline audit
may be selected independently if owner/roadmap/new evidence requires it.

## Result / reproducibility contract

Every reported candidate remains explainable from persisted evidence including:

- normalized CandidateSpec;
- ResourceInventory identity;
- target/search epoch and pinned endpoints;
- exact rendered strategy/profile;
- discovery/stability/final result evidence as applicable;
- runtime model used;
- timing/cleanup/interception evidence required by the current implementation.

Runtime preload/dispatcher details do not silently become user strategy semantics.

## Current implementation handoff

The immediate runtime change is `v0.4.1_13` Model-C-only production finalization. It must not rewrite
this search graph, CandidateSpec, resource, endpoint, discovery or result contract.

After `_13` owner-live PASS, return to the current `docs/ROADMAP.md` rather than reopening historical
A/B/C selection or old `_32/_33` sequencing by default.

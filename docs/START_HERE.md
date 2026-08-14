# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-14
**Current handoff identity:** `v0.4.1_13`

This file answers: **what has just been established at the current `_N` boundary, what is its effect, and what happens next?**

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=13`;
- current state line: `v0.4.x`;
- current development stage: `v0.4.1`;
- current source package candidate: `os-zapret2-restyle-0.4.1_13.pkg`;
- latest published testing package/tag remains `os-zapret2-restyle-0.4.1_12.pkg` / `v0.4.1_12` until a separate testing-package publication is requested;
- required ABI: `FreeBSD:15:amd64`.

Resolve the exact current `main` SHA at execution time under `GH-004`. A source candidate and a persistently published testing package are distinct identities (`DEV-033`, `GH-047`–`GH-050`).

## What was just established — Model-C-only production

`v0.4.1_13` closes the transitional Stage-60 runtime chain without changing search semantics:

- the packaged `stage60-parallel` compatibility command routes normal production through `strategy_lab_py/stage60_model_c_production.py`;
- the production owner reuses the proven Model-C `_bucket_batch` engine and the existing authoritative Stage-60 planner;
- normal production Model-C infrastructure/selector/rendering/readiness/attribution/cleanup failure becomes an explicit bounded structural Stage-60 failure;
- that failure is deliberately not a `WarmInfrastructureError`, so the legacy Model-B/cold-Model-A fallback handler cannot consume it;
- persisted Stage-60 evidence marks `model_c_only=true` and `cold_fallback_available=false` when a result file exists;
- automatic production replay through Model B and cold Model A is removed;
- Model B and Model A remain available only through explicit reference/benchmark/test overrides;
- source-port leasing/attribution, profile-compatible segmentation, `_12` readiness, adaptive budgets, GET-4K discovery, cleanup/cancellation and Stage-90 restoration ownership are unchanged.

Detailed runtime contract: [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md).

## Current product facts

- DNS is fixed/currently working; historical DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- accepted measurement decisions remain closed: no Lua-init production change, no lazy-BLOB/common-set production change, retain bounded GET-4K discovery, no cross-batch keep-warm/reuse for the current architecture.
- Model B/A fallback code may remain inside explicit reference/measurement tooling, but it is not reachable from the normal packaged production entry point.

Detailed measurements and proof links are in [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

## `_13` automated acceptance

Before `_13` is considered source-complete and mergeable:

- normal production Stage 60 must reach Model C only;
- an injected Model-C infrastructure failure must produce explicit bounded failure with no B/A replay;
- cleanup must remain bounded on success/failure/cancel;
- source-port leasing/attribution and segmentation must remain correct;
- the complete Strategy Lab corrective matrix must pass;
- FreeBSD 15 package qualification must pass on the exact PR head;
- merge must use that exact verified head under `GH-024`–`GH-026`.

## Immediate post-merge/live gate

`_13` owner-live acceptance still requires one selected normal Model-C-only run on OPNsense with:

- correct result handling;
- no automatic Model B/A replay;
- Stage-90 semantic restoration PASS;
- no temporary IPFW/process/socket residue.

A persistent `v0.4.1_13` testing package/tag is published only when testing-package delivery is requested; do not infer publication merely from source merge.

After the selected `_13` owner-live PASS, return to [`ROADMAP.md`](ROADMAP.md) and take the next accepted risk-selected product task. Do not reopen A/B/C selection or closed measurement experiments by inertia.

## Current task reading

For Model-C-only production/live work, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read the current `v0.4.x` ledger when richer chronology/proof is needed. Use `INDEX.md` for older records on demand.

When the owner says `продолжаем`, apply `CHAT-012`: verify repository/handoff identity and continue from this exact `_13` boundary rather than reconstructing or reopening closed choices.

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
- current testing package/tag: `os-zapret2-restyle-0.4.1_13.pkg` / `v0.4.1_13`;
- testing-package SHA-256: `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`;
- `_13` source merge and testing-tag target: `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- required ABI: `FreeBSD:15:amd64`.

Resolve the exact current `main` SHA at execution time under `GH-004`. The testing prerelease is persistent GitHub delivery only; it does not publish the stable Pages/pkg repository (`GH-034`–`GH-038`).

## What was established — Model-C-only production

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

## `_13` automated acceptance and testing-package publication — PASS

The `_13` source and persistent testing-delivery boundaries are complete:

- PR `#230` exact verified head: `8e1af17ce4ccfaad4851329167b386741d0c9ee8`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD 15 package build/inspection qualification: PASS;
- exact verified head squash-merged as `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- source CI run: `31819116248`;
- testing publication workflow run: `31838633599`;
- persistent prerelease `v0.4.1_13`: published;
- package asset `os-zapret2-restyle-0.4.1_13.pkg`: uploaded and verified;
- tag `v0.4.1_13` points exactly to `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- publication branch `publish/v0.4.1_13`: deleted after successful publication.

## Immediate remaining `_13` live gate

Run one selected normal Model-C-only Strategy Lab regression on OPNsense with the published `_13` package and verify:

- correct result handling;
- no automatic Model B/A replay;
- Stage-90 semantic restoration PASS;
- no temporary IPFW/process/socket residue.

After the selected `_13` owner-live PASS, return to [`ROADMAP.md`](ROADMAP.md) and take the next accepted risk-selected product task. Do not reopen A/B/C selection or closed measurement experiments by inertia.

## Current task reading

For Model-C-only production/live work, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read the current `v0.4.x` ledger when richer chronology/proof is needed. Use `INDEX.md` for older records on demand.

When the owner says `продолжаем`, apply `CHAT-012`: verify repository/handoff identity and continue from this exact `_13` boundary rather than reconstructing or reopening closed choices.

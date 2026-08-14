# os-zapret2-restyle — START HERE

Status: **AUTHORITATIVE OPERATIONAL HANDOFF / LEVEL 1**
Updated: 2026-08-14

This file answers only: **where are we, what is next, and what must be read to do it?**
Detailed current-line chronology lives in [`history/current/v0.4.x.md`](history/current/v0.4.x.md).
Older history is routed by [`INDEX.md`](INDEX.md) and is not part of normal startup context.

## Mandatory startup

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. this file;
4. `docs/PROJECT_STATE.md`;
5. only the specialist documents listed under **Current task reading** below.

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- resolve exact `main` SHA at session start;
- `VERSION=0.4.1`;
- packaged source `PLUGIN_REVISION=12`;
- testing package/tag: `os-zapret2-restyle-0.4.1_12.pkg` / `v0.4.1_12`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- required ABI: `FreeBSD:15:amd64`;
- owner console: root `csh`.

Documentation-only `main` can be newer than the packaged source merge.

## Locked current facts

- **DNS is fixed/currently working.** Historical DNS failures are closed unless fresh direct evidence
  shows a new problem.
- **Model C is selected for normal production Stage 60.** A/B/C selection is closed.
- packaged `_12` still implements `Model C -> Model B -> Model A cold`; this is transition debt only.
- exact next packaged source patch is **`v0.4.1_13`**: remove silent B/A production fallback; do not
  improve the transition.
- accepted measurement decisions remain closed: no Lua-init production change, no lazy-BLOB change,
  retain bounded GET-4K discovery, no cross-batch keep-warm/reuse for current architecture.

Evidence and the richer reasoning are in the current `v0.4.x` ledger, not duplicated here.

## Short lifetime path

- Initial plugin
- Lifecycle hardening
- Zapret2 GUI
- Diagnostics fixes
- Strategy Lab
- Python migration
- Model A baseline
- Model B testing
- Model C testing
- Model C selected
- Production finalization ← **current**

Completed-line archives: [`v0.1.x`](history/archive/v0.1.x.md),
[`v0.2.x`](history/archive/v0.2.x.md), [`v0.3.x`](history/archive/v0.3.x.md).
Current-line detail: [`v0.4.x`](history/current/v0.4.x.md).

# Exact next code change — `v0.4.1_13`

Make normal production Stage 60 Model-C-only:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure/selector/rendering/readiness/attribution failures explicit and bounded;
- remove fallback plumbing used only for production B/A replay;
- retain B/A where useful as reference/benchmark/test tooling;
- preserve planner/search semantics, CandidateSpec/ResourceInventory, leasing/attribution,
  profile-compatible segmentation, readiness, adaptive budgets, GET-4K discovery, cleanup and
  Stage-90 semantic restoration.

Metadata for the packaged change:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- title/commit prefix `v0.4.1_13:`.

## Current task reading

Before editing `_13`, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read [`history/current/v0.4.x.md`](history/current/v0.4.x.md) only if the implementation needs the
richer current-line chronology/evidence. Read old archives/deep records only when a concrete
historical dependency arises.

## Acceptance / continuation

Automated `_13` acceptance:

- normal production Stage 60 reaches Model C only;
- no silent B/A replay;
- Model-C infrastructure failure is explicit/bounded;
- cleanup succeeds on success/failure/cancel;
- leasing/attribution and segmentation remain correct;
- Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

Then publish the deterministic `_13` testing package when requested and run one owner-live normal
Model-C-only regression. A PASS closes fallback-removal transition; it does not reopen model
selection.

When the owner says `продолжаем`, verify current repository identity and, if it still matches this
handoff, start `_13` directly without rediscovering completed Model A/B/C or measurement history.

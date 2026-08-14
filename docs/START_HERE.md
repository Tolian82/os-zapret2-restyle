# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Permanent project principles:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **GitHub delivery/release rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

Status: **AUTHORITATIVE REVISION HANDOFF / LEVEL 1**
Updated: 2026-08-14
Current handoff identity: **`v0.4.1_12`**

This file answers only: **what has just been established at the current revision boundary, what is the
intended effect, and what exactly happens next?** It is the live handoff for the current `_N` revision,
not a patch-by-patch project history.

## Fast-start rule

Mandatory repository startup order is defined by `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> DOCUMENTATION_RULES -> START_HERE -> PROJECT_STATE -> current-task specialists`.

The richer current-line chronology is [`history/current/v0.4.x.md`](history/current/v0.4.x.md).
Older detail is reached through [`INDEX.md`](INDEX.md) only when the task actually needs it.

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- resolve exact `main` SHA at session start;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=12`;
- current second-component state line: `v0.4.x`;
- current third-component development stage: `v0.4.1`;
- current testing package/tag: `os-zapret2-restyle-0.4.1_12.pkg` / `v0.4.1_12`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- required ABI: `FreeBSD:15:amd64`;
- owner console: root `csh`.

Documentation/CI-only `main` may be newer than the packaged source merge without changing the package
candidate identity.

## What was just established under `v0.4.1_12`

The current revision line now has a durable documentation/version-memory contract:

- documentation uses a dedicated numbered canonical rule file;
- `PROJECT_STATE.md` belongs to the whole second-component line (`v0.4.x`), not to one third component;
- `START_HERE.md` belongs to the exact current `_N` handoff boundary;
- the third numeric component (`1` in `0.4.1`) identifies the current development stage/task;
- a third-component transition resets `_N` to `_1` but does not itself publish a full release;
- the second numeric component (`4` in `0.4.x`) remains owner-controlled and its change always means a
  full release plus state/history rollover;
- full release publication is independent of `_N`: the current candidate revision may be released when
  explicitly requested and when its semantic tag is still available;
- the master plan remains compact but contains all known completed/current/future development items;
- release automation distinguishes ordinary third-component stage changes from actual full-release
  preparation;
- owner-facing project communication remains normal understandable Russian.

### Intended effect

A future zero-memory session should immediately understand the hierarchy
`v0.4.x -> v0.4.1 -> v0.4.1_12`, know which document owns each level, read the recent action log only
when necessary, and continue without reconstructing settled history or confusing a development-stage
change with a release.

## Current product facts that matter for the next code patch

- **DNS is fixed/currently working.** Historical DNS failures remain closed absent fresh direct evidence.
- **Model C is selected for normal production Stage 60.** A/B/C selection is closed.
- packaged `_12` still implements `Model C -> Model B -> Model A cold`; this is transition debt only.
- accepted measurement decisions remain closed: no Lua-init production change, no lazy-BLOB change,
  retain bounded GET-4K discovery, no cross-batch keep-warm/reuse for the current architecture.

Durable current facts live in `PROJECT_STATE.md`; measurements and their proof links live in the
current `v0.4.x` ledger.

# Exact next code change — `v0.4.1_13`

Make normal production Stage 60 Model-C-only:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure/selector/rendering/readiness/attribution failures explicit and bounded;
- remove fallback plumbing used only for production B/A replay;
- retain B/A where useful as reference/benchmark/test tooling;
- preserve planner/search semantics, CandidateSpec/ResourceInventory, leasing/attribution,
  profile-compatible segmentation, readiness, adaptive budgets, GET-4K discovery, cleanup and
  Stage-90 semantic restoration.

Package metadata for this ordinary same-stage source patch:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- title/commit prefix `v0.4.1_13:`.

## Current task reading

Before editing `_13`, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read [`history/current/v0.4.x.md`](history/current/v0.4.x.md) only if implementation needs richer
current-line chronology or proof. Use `INDEX.md` for older records only when a concrete dependency
requires them.

## `_13` acceptance and immediate continuation

Automated acceptance:

- normal production Stage 60 reaches Model C only;
- no silent B/A replay;
- Model-C infrastructure failure is explicit/bounded;
- cleanup succeeds on success/failure/cancel;
- leasing/attribution and segmentation remain correct;
- Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

Then publish the deterministic `_13` testing package when requested and run one owner-live normal
Model-C-only regression. A PASS closes fallback-removal transition; it does not reopen model selection.

## Overall direction

The complete concise completed/current/future checklist is always kept in [`ROADMAP.md`](ROADMAP.md).
The immediate sequence is:

1. documentation/version-memory rules — **done in current `_12` GitHub state**;
2. Model-C-only production patch `_13`;
3. owner-live `_13` regression;
4. continue the risk-selected regression/product backlog from the master plan;
5. change the third numeric component only when moving to the next genuine development stage;
6. change the second numeric component only after explicit owner authorization and as a full release.

When the owner says `продолжаем`, verify repository identity and, if it still matches this handoff,
start `_13` directly without rediscovering completed Model A/B/C or measurement history.

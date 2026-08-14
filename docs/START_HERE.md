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
**Current handoff identity:** `v0.4.1_12`

This file answers: **what has just been established at the current `_N` boundary, what is its effect, and what happens next?**

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=12`;
- current state line: `v0.4.x`;
- current development stage: `v0.4.1`;
- current testing package/tag: `os-zapret2-restyle-0.4.1_12.pkg` / `v0.4.1_12`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- required ABI: `FreeBSD:15:amd64`.

Documentation/CI-only `main` may be newer than the packaged source while package identity remains `_12` (`DEV-033`).

## What was just established

The documentation-governance audit tightened the four-book model without changing product/package code:

- all current general rules remain in exactly four canonical books;
- the GitHub task route is now inside the single `GH-*` book; `GITHUB_WORKFLOW.md` is only a compatibility pointer;
- `DEVELOPMENT_GUIDE.md` and `WORKING_CONVENTIONS.md` are compatibility pointers rather than extra mutable process/state stores;
- existing rule IDs are persistent identities and are not renumbered merely for sorting;
- every canonical book contains explicit outbound and inbound cross-reference registries;
- CI validates rule-ID existence plus registry/body symmetry;
- owner instructions are explicitly binding and must result in execution, persisted canon, or a concrete blocker;
- a read-only boundary must be explicit rather than inferred from words such as `проверь` when the same instruction also says to act;
- every GitHub change performs a documentation-impact check and updates affected documentation in the same logical scope;
- cold start is context-first: handoff/state before the complete four-book canon, then plan/index/specialists;
- already-read Level-1 material may be reused while the exact repository state is unchanged, reducing repeated context load;
- current and newly written documentation uses normal Markdown rather than decorative `=====` walls.

The detailed rules are canonical in `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*`; this handoff does not duplicate them.

## Current product facts needed for the next code patch

- DNS is fixed/currently working; historical DNS failures are closed absent fresh direct evidence.
- Model C is the selected normal production Stage-60 direction; A/B/C selection is closed.
- packaged `_12` still implements transitional `Model C -> Model B -> Model A cold` production fallback.
- accepted measurement decisions remain closed: no Lua-init production change, no lazy-BLOB/common-set production change, retain bounded GET-4K discovery, no cross-batch keep-warm/reuse for the current architecture.

Detailed measurements and proof links are in [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

## Exact next code change — `v0.4.1_13`

Make normal production Stage 60 Model-C-only:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure, selector, rendering, readiness, and attribution failures explicit and bounded;
- remove production fallback plumbing used only for B/A replay;
- retain B/A where useful as reference/benchmark/test tooling;
- preserve planner/search semantics, CandidateSpec/ResourceInventory, source-port leasing/attribution, profile-compatible segmentation, readiness, adaptive budgets, GET-4K discovery, cleanup, cancellation containment, and Stage-90 semantic restoration.

Package metadata follows `DEV-032`:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- use candidate prefix `v0.4.1_13:` for GitHub delivery (`GH-014`).

## Current task reading for `_13`

Before editing `_13`, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read the current `v0.4.x` ledger when richer chronology/proof is needed. Use `INDEX.md` for older records on demand.

## `_13` acceptance

- normal production Stage 60 reaches Model C only;
- no silent B/A replay;
- Model-C infrastructure failure is explicit and bounded;
- cleanup succeeds on success/failure/cancel;
- source-port leasing/attribution and segmentation remain correct;
- Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes;
- selected owner-live normal Model-C-only regression verifies result handling and restoration.

When the owner says `продолжаем`, apply `CHAT-012`: verify repository/handoff identity and start `_13` directly if it still matches.

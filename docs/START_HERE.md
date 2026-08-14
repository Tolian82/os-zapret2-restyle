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

The documentation-governance audit now has a stable rule-lifecycle and link-integrity model without changing product/package code:

- all current general rules remain in exactly four canonical books;
- `GITHUB_PUBLICATION.md` remains the fourth canonical book and is explicitly the complete **Правила работы с GitHub**;
- obsolete duplicate files `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` are physically removed after their useful current meaning and repository references are migrated;
- rule IDs are permanent identities and are never cascade-renumbered merely because a rule is inserted, moved, or reorganized;
- cancelling a rule does not delete its ID/text: the rule remains in its canonical book marked `[ОТМЕНЕНО]`; replacement uses `[ЗАМЕНЕНО НА <ID>]`;
- cancelled/replaced IDs have no current normative force and are never recycled;
- the former blanket `DOC-014` formulation about all useful normative information being in the four books is cancelled in place as unnecessary;
- the former automatic read-only interpretation of words such as `проверь`/`аудит` is explicitly cancelled; active `CHAT-011` requires a real read-only prohibition;
- every canonical book retains explicit outbound/inbound cross-reference registries;
- CI validates active rule references, lifecycle state, replacement chains, and cross-reference symmetry;
- CI also validates tracked local Markdown file/directory links and Markdown heading fragments;
- cold start is context-first: `AGENTS -> START_HERE -> PROJECT_STATE -> four rule books -> ROADMAP -> INDEX -> selected specialists`;
- already-read Level-1 material may be reused while the exact repository state is unchanged; after `main` advances, affected current/mandatory documents are reread;
- every GitHub scope continues to perform a documentation-impact decision and keeps the active tree self-consistent.

The detailed rules are canonical in `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*`; this handoff does not redefine them.

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

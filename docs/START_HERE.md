# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

Status: **AUTHORITATIVE REVISION HANDOFF / LEVEL 1**
Updated: 2026-08-14
Current handoff identity: **`v0.4.1_12`**

This file answers only: **what has just been established at the current `_N` boundary, what is its intended effect, and what exactly happens next?**

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=12`;
- current project-state line: `v0.4.x`;
- current development stage: `v0.4.1`;
- current testing package/tag: `os-zapret2-restyle-0.4.1_12.pkg` / `v0.4.1_12`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- required ABI: `FreeBSD:15:amd64`.

Documentation/CI-only `main` may be newer than the packaged runtime/source merge while package identity remains `_12` (`DEV-033`).

## What was just established under `v0.4.1_12`

The project's general normative material has been normalized into exactly four canonical rule books:

- documentation governance: `DOCUMENTATION_RULES.md` / `DOC-*`;
- project-development canon: `PROJECT_PRINCIPLES.md` / `DEV-*`;
- owner/assistant communication semantics: `CHAT_RULES.md` / `CHAT-*`;
- GitHub operation/publication discipline: `GITHUB_PUBLICATION.md` / `GH-*`.

Current rules previously spread across active documents were moved into their correct single normative homes, reviewed for supersession, ambiguity, contradiction, duplication, and scope, then assigned stable domain-prefixed rule IDs. Active supporting documents now reference rule IDs instead of competing with the four rule books. Historical decisions/records remain historical rather than being rewritten as if they had always used the new structure (`DOC-002`–`DOC-007`).

### Intended effect

A zero-memory session can now distinguish immediately between:

1. how documentation is maintained;
2. how the product is developed and versioned;
3. how the owner's words are interpreted in chat;
4. how GitHub work is performed.

This removes rule duplication while keeping `INDEX.md` as the integrity/navigation map and preserving all historical/deep records.

## Current product facts needed for the next code patch

- DNS is fixed/currently working; historical DNS failures are closed absent new direct evidence.
- Model C is the selected normal production Stage-60 direction; A/B/C model selection is closed.
- packaged `_12` still implements transitional `Model C -> Model B -> Model A cold` production fallback.
- accepted measurement decisions remain closed: no Lua-init production change, no lazy-BLOB/common-set production change, retain bounded GET-4K discovery, no cross-batch keep-warm/reuse for the current architecture.

Detailed measurements and proof links are in [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

# Exact next code change — `v0.4.1_13`

Make normal production Stage 60 Model-C-only:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure/selector/rendering/readiness/attribution failures explicit and bounded;
- remove production fallback plumbing used only for B/A replay;
- retain B/A where useful as reference/benchmark/test tooling;
- preserve planner/search semantics, CandidateSpec/ResourceInventory, source-port leasing/attribution, profile-compatible segmentation, readiness, adaptive budgets, GET-4K discovery, cleanup, cancellation containment, and Stage-90 semantic restoration.

Package metadata for this ordinary same-stage packaged source patch follows `DEV-032`:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- use candidate prefix `v0.4.1_13:` for GitHub delivery (`GH-014`).

## Current task reading for `_13`

Before editing `_13`, read completely:

1. `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
2. `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
3. `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Read [`history/current/v0.4.x.md`](history/current/v0.4.x.md) only when richer current-line chronology or proof is needed. Use `INDEX.md` for older records on demand.

## `_13` acceptance

Automated acceptance:

- normal production Stage 60 reaches Model C only;
- no silent B/A replay;
- Model-C infrastructure failure is explicit and bounded;
- cleanup succeeds on success/failure/cancel;
- source-port leasing/attribution and segmentation remain correct;
- Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

Then publish the deterministic `_13` testing package when instructed and run the selected owner-live normal Model-C-only regression required by the current risk gate.

## Overall direction

The complete concise completed/current/future checklist remains in [`ROADMAP.md`](ROADMAP.md). The immediate sequence is:

1. four canonical rule books — **established in current `_12` documentation state**;
2. Model-C-only production patch `_13`;
3. owner-live `_13` regression;
4. continue the risk-selected product/regression backlog from the master plan.

When the owner says `продолжаем`, apply `CHAT-012`: verify repository/handoff identity and, if it still matches, start `_13` directly without rediscovering settled Model A/B/C or measurement history.

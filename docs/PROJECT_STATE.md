# os-zapret2-restyle — Current state for `v0.4.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-14
State-line scope: **`v0.4.x`**

This file contains current facts only (`DOC-026`–`DOC-030`).

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md);
- project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
- chat rules: [`CHAT_RULES.md`](CHAT_RULES.md);
- GitHub rules: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology/proof: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

## Repository and package facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.4.1`;
- packaged source revision: `_12`;
- current testing package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- testing tag: `v0.4.1_12`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing-package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`;
- required ABI: `FreeBSD:15:amd64`;
- internal service key: `zapret`.

The exact `main` SHA is resolved at execution time under `GH-004`; documentation/CI-only commits after the packaged source merge do not change `_12` package identity (`DEV-033`).

## Current product facts

- DNS is fixed/currently working. Historical DNS failures are not a current blocker without fresh direct reproducible evidence.
- Model C is the selected normal production Stage-60 direction. A/B/C model selection is closed.
- Model B remains reference/warm tooling plus `_12` transition fallback; Model A remains cold reference tooling.
- packaged `_12` still contains `Model C -> Model B -> Model A cold`; this is implementation debt, not approved long-term architecture.
- exact next packaged source change is `v0.4.1_13`, which removes automatic production B/A replay and leaves normal Stage 60 Model-C-only.
- Lua initialization, BLOB lazy-loading/common-set, bounded GET-4K discovery, and cross-batch keep-warm questions are closed for the current architecture by accepted measured evidence.

Detailed measurements and proof links remain in the current `v0.4.x` ledger.

## Current architecture and safety facts

Model C currently preserves:

- adaptive-search planner semantics;
- immutable CandidateSpec and job-scoped ResourceInventory identity;
- exact source-port-qualified attribution/leasing;
- profile-compatible physical segmentation inside logical planner batches;
- bounded readiness;
- finite adaptive budgets;
- bounded GET-4K discovery;
- cleanup/cancellation containment;
- Stage-90 semantic restoration.

Current architecture entry points:

- [`ARCHITECTURE.md`](ARCHITECTURE.md);
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md);
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md).

Historical A/B/C experiment material is history/proof and does not represent current production choice.

## Current documentation and governance facts

- exactly four canonical general rule books exist: `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`;
- rules use persistent `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*` identities rather than renumbering for presentation order;
- each canonical book contains explicit inbound/outbound cross-reference registries and CI validates them against actual rule bodies;
- `START_HERE.md` is the exact `_N` handoff;
- this file is current state for `v0.4.x`;
- `ROADMAP.md` is the complete concise master plan;
- `INDEX.md` is the global navigation/integrity map;
- [`history/current/v0.4.x.md`](history/current/v0.4.x.md) is the current Level-2 chronology;
- `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` are legacy compatibility pointers only and contain no independent mutable canon;
- active/new documentation uses clean standard Markdown; old Level-3 historical formatting is preserved unless deliberately migrated separately.

The normative mechanics behind these facts live only in the corresponding rule books and are not duplicated here.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).

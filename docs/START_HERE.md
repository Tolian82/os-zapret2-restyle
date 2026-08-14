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

The documentation/governance rules were audited again without changing product/package code:

- owner-facing project explanations must be written as normal Russian sentences; literal English technical names may remain only as object names, while service-status/process jargon is translated unless quoted literally;
- current work has one documentation flow: `START_HERE -> PROJECT_STATE -> version-line archive`;
- `START_HERE.md` owns active work and the immediate next boundary; durable completed facts flow into `PROJECT_STATE.md`; line closure moves final state into the archive;
- current ledgers, decisions, devlogs, and evidence preserve chronology/rationale/proof but are not parallel owners of current state;
- rule maintenance now has an explicit decision boundary: create a new rule only for a new durable normative principle; refine an existing rule when its identity remains the same; cancel it when it no longer applies; replace it when a materially different durable rule supersedes it;
- one-off tasks, test results, temporary plans, and ordinary current work do not become canonical rules merely because they are currently important;
- `GH-009` is cancelled and retained only as a permanent historical rule ID; targeted dependency/reference reconciliation plus scope/risk inspection replaces its former mandatory broad audit;
- documentation reconciliation remains mandatory for every logical scope, but editing documentation files is not required when the evidence-based result is that documented state did not change;
- roadmap commitments are limited to owner-approved or otherwise accepted future development directions, not every idea mentioned during discussion;
- release tag/asset identity remains immutable, while human-facing release notes may be transparently corrected when binary identity and publication truth do not change;
- CI is being aligned with scope/risk: pure documentation changes use focused documentation/governance integrity checks, while product/package changes retain the full product matrix and package qualification as applicable.

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

# os-zapret2-restyle — Current state

Status: **CURRENT / LEVEL 1**
Updated: 2026-08-14

This file answers only: **what is true now?**
Exact continuation: [`START_HERE.md`](START_HERE.md).
Current-line chronology/evidence: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).
Future ordering: [`ROADMAP.md`](ROADMAP.md).

## Repository / package

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- semantic version: `0.4.1`;
- packaged source revision: `12`;
- current testing package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- testing tag: `v0.4.1_12`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing-package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`;
- required ABI: `FreeBSD:15:amd64`.

Resolve the actual `main` SHA before every mutation; docs/CI-only `main` may be newer than packaged
source without changing package identity.

## Current product facts

- DNS is fixed/currently working. Historical DNS failures are not a current blocker without fresh
  direct reproducible evidence.
- Model C is the selected normal production Stage-60 direction. A/B/C model selection is closed.
- Model B is reference/warm tooling plus `_12` transition fallback; Model A is cold reference tooling.
- packaged `_12` still contains `Model C -> Model B -> Model A cold`; this is implementation debt,
  not approved long-term architecture.
- `_13` removes automatic B/A production replay and leaves normal production Stage 60 Model-C-only.
- Lua-init, BLOB lazy-loading/common-set, bounded GET-4K discovery and cross-batch keep-warm questions
  are closed for the current architecture by accepted measured evidence.

Detailed measurements and evidence links intentionally live only in the current `v0.4.x` ledger.

## Current architecture / safety

Model C retains the accepted adaptive-search planner, CandidateSpec/ResourceInventory ownership,
source-port-qualified attribution/leasing, profile-compatible physical segmentation, bounded
readiness, finite adaptive budgets, GET-4K discovery, cleanup/cancellation containment and Stage-90
semantic restoration.

Current architecture authorities:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)

Historical A/B/C experiment material is evidence only and cannot reopen current production choice.

## Current release/version authority

The second numeric component is the `4` in `0.4.x`. It changes only after explicit owner
version/transition instruction or separate owner approval. A transition such as `v0.4.x -> v0.5.x`
necessarily includes a full project release and version-line archive rollover. A full release can also
be requested while keeping the second numeric component unchanged.

A full release means a verified OPNsense package published into the project Pages/pkg repository for
installation/update through the OPNsense Web GUI, together with the semantic tag, release assets and
checksums. Every full release includes a complete human-facing `README.md` review.

## Documentation memory state

Documentation uses three levels:

- Level 1: mandatory bounded recovery set (`AGENTS`, principles, `START_HERE`, this file);
- Level 2: current `v0.4.x` ledger plus task-selected specialist docs;
- Level 3: completed version archives and deep chronology/evidence, loaded on demand.

Completed archives: [`v0.1.x`](history/archive/v0.1.x.md),
[`v0.2.x`](history/archive/v0.2.x.md), [`v0.3.x`](history/archive/v0.3.x.md).
Current ledger: [`v0.4.x`](history/current/v0.4.x.md).

## Exact next packaged source change

**`v0.4.1_13` — Model-C-only production finalization.**

Scope and acceptance are intentionally kept in [`START_HERE.md`](START_HERE.md), not duplicated here.

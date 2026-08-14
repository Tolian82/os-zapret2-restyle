# os-zapret2-restyle — Current state for `v0.4.x`

Status: **CURRENT SECOND-COMPONENT STATE / LEVEL 1**
Updated: 2026-08-14
State-line scope: **`v0.4.x`** — the second numeric component is `4`.

This file answers only: **what is true now for the current `v0.4.x` project-state line?**
Exact revision continuation: [`START_HERE.md`](START_HERE.md).
Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).
Master development plan: [`ROADMAP.md`](ROADMAP.md).
Current-line chronology and proof links: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

`PROJECT_STATE.md` remains the current factual state file for the whole `v0.4.x` line while the second
numeric component stays `4`. Changes to the third numeric component update this file when current facts
change but do **not** archive it. The final state is archived only when the second component changes.

## Repository / package

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- current project version: `0.4.1`;
- current third-component development stage: `1` in `0.4.1`;
- packaged source revision: `_12`;
- current testing package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- testing tag: `v0.4.1_12`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing-package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`;
- required ABI: `FreeBSD:15:amd64`.

Resolve the actual `main` SHA before every mutation; documentation/CI-only `main` can be newer than the
packaged source without changing package identity.

## Current product facts

- DNS is fixed/currently working. Historical DNS failures are not a current blocker without fresh
  direct reproducible evidence.
- Model C is the selected normal production Stage-60 direction. A/B/C model selection is closed.
- Model B is reference/warm tooling plus `_12` transition fallback; Model A is cold reference tooling.
- packaged `_12` still contains `Model C -> Model B -> Model A cold`; this is implementation debt,
  not approved long-term architecture.
- the next ordinary packaged patch removes automatic B/A production replay and leaves normal
  production Stage 60 Model-C-only.
- Lua-init, BLOB lazy-loading/common-set, bounded GET-4K discovery and cross-batch keep-warm questions
  are closed for the current architecture by accepted measured evidence.

Detailed measurements and proof links live in the current `v0.4.x` ledger rather than being copied
into this Level-1 state file.

## Current architecture / safety

Model C retains the accepted adaptive-search planner, CandidateSpec/ResourceInventory ownership,
source-port-qualified attribution/leasing, profile-compatible physical segmentation, bounded
readiness, finite adaptive budgets, GET-4K discovery, cleanup/cancellation containment and Stage-90
semantic restoration.

Current architecture authorities:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)

Historical A/B/C experiment material is proof/history only and cannot reopen current production choice.

## Current version/documentation facts

- second numeric component `4` defines this state line `v0.4.x`;
- third numeric component `1` identifies the current development stage inside this line;
- `_12` identifies the current concrete package revision/handoff boundary;
- a same-stage ordinary source patch increments only `_N`;
- a genuine new development stage changes the third component and resets `_N` to `_1`;
- a third-component-only stage change does not itself mean a full release;
- a second-component change is owner-controlled and always means full release + final state/archive
  rollover;
- a full release can occur inside the same second-component line and may use the current `_N` candidate;
- every full release includes a complete human-facing `README.md` review.

The complete numbered documentation contract is in [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).

## Documentation memory state

Documentation uses three levels:

- Level 1: `AGENTS`, `PROJECT_PRINCIPLES`, `DOCUMENTATION_RULES`, `START_HERE`, this file, then only
  current-task specialist documents;
- Level 2: current `v0.4.x` ledger plus task-selected current detail;
- Level 3: completed version-line archives and deep history/proof, loaded on demand.

`START_HERE` owns the exact current `_N` task. `ROADMAP` owns the complete concise master plan.
`INDEX` owns navigation. This file owns current facts for `v0.4.x`.

## Future state rollover

Only an explicitly owner-authorized change of the second numeric component closes this state line.
For example, on `v0.4.x -> v0.5.x`:

1. reconcile this file through the final true `v0.4.x` state;
2. preserve that final state inside `history/archive/v0.4.x.md` together with the compact archive map;
3. preserve all detailed `v0.4.x` records unchanged;
4. initialize this file as the current `v0.5.x` state;
5. initialize the new `history/current/v0.5.x.md` ledger;
6. update `INDEX`, `START_HERE`, `ROADMAP` and README as required by the full-release procedure.

The new final-state-snapshot rule is not retroactively imposed on `v0.4.0` or older history.

## Completed version-line archives

All currently completed archive files are linked here as required:

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).
When `v0.4.x` eventually closes, its new archive link is appended to this list before the new current
state is published.

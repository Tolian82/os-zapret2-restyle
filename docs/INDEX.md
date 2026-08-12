# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

A full repository-wide reading is required only for a repository-wide audit or genuine
full-context recovery. Focused work uses the risk-based specialist reading defined in
`AGENTS.md`. For current diagnosis, later patch/live/release evidence outranks historical
records.

## Current release / Strategy Lab authorities

Read these first for current Strategy Lab or release work:

- `docs/PROJECT_STATE.md` — current source/published candidates, accepted runtime basis and next boundary;
- `docs/patches/v0.4.1_3.md` — current measurement-only BLOB startup/readiness/RSS patch;
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md` — BLOB measurement/isolation/decision contract;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md` — exact `_3` testing publication evidence;
- `docs/patches/v0.4.1_2.md` — accepted measurement-only Lua initialization patch;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md` — accepted Lua measurement/decision contract;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md` — accepted owner-installed Lua equivalence evidence;
- `docs/releases/v0.4.1.md` — stable v0.4.1 release record;
- `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md` — stable publication evidence;
- `docs/patches/v0.4.0_26.md` — accepted workload-derived adaptive-budget patch;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — adaptive-budget contract;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md` — detailed production owner-live runtime basis;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — search/validation architecture;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — preferred one-worker source-port dispatcher architecture;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical live regression inventory;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership.

### Current v0.4.1 boundary

`VERSION=0.4.1`, `PLUGIN_REVISION=3`; current source candidate and latest published testing
prerelease are `os-zapret2-restyle-0.4.1_3.pkg` / `v0.4.1_3`.

Stable published package remains `os-zapret2-restyle-0.4.1_1.pkg`; stable upgrade smoke is
PASS. Latest owner-tested testing candidate remains `_2` until `_3` owner measurement passes.
`_2` Lua initialization measurement is accepted and closed as a valid negative optimization
result. Detailed production Strategy Lab evidence remains `_26` because `_2` and `_3` are
measurement-only.

`_3` centralizes canonical resource roots and measures BLOB-free vs built-in fake vs external
fake-file startup/readiness/RSS using an isolated lifecycle-locked harness. It installs no
experiment traffic routes and does not mutate normal Zapret2 state. One `_3` run cannot
authorize a production BLOB-loading change.

Owner-live Extended `telegram.org`, `job.xhdgCU`, remains the detailed production baseline:
Model C 16/16, no fallback, adaptive budget `150/120/270/120`, clean restoration and no
`19128-19130` residue.

Stage 60 remains
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`;
`preferred-free-else-alternate` source-port leasing remains active.

## Current implementation authorities

### Strategy Lab core

- `docs/architecture/STRATEGY_LAB.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md`
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md`
- `docs/architecture/STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`
- `docs/architecture/STRATEGY_LAB_STRUCTURED_RESULTS.md`
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md`
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md`
- `docs/architecture/STRATEGY_LAB_RETENTION.md`
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_MATRIX.md`

### Historical corrective/evidence chain

Historical records stay under `docs/patches/`, `docs/devlog/`, `docs/verification/evidence/`,
and `docs/audit/`. Key retained comparison points:

- Model A cold reference: `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model B production: `docs/patches/v0.4.0_22.md`, `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C source-port correction: `docs/patches/v0.4.0_25.md`, `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- adaptive budget: `docs/patches/v0.4.0_26.md`, `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- v0.4.1 stable release: `docs/releases/v0.4.1.md`, `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`;
- Lua measurement: `docs/patches/v0.4.1_2.md`, `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- current BLOB measurement: `docs/patches/v0.4.1_3.md`, `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`, `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`.

Historical evidence explains progression; it never overrides a later current record.

## Audit authorities

- `docs/AUDIT.md`
- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`

## Product/project authorities

- `docs/REQUIREMENTS.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/decisions/`
- `docs/WORKING_CONVENTIONS.md`
- `docs/DEVELOPMENT_GUIDE.md`
- `docs/DEVLOG.md`
- `docs/devlog/`
- `docs/patches/`
- `docs/releases/`

## GitHub delivery authority

For GitHub work, read in this order:

1. current owner instruction;
2. repository-root `AGENTS.md`;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
5. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
6. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
7. `docs/GITHUB_WORKFLOW.md`.

Key rules: GitHub plugin first, exact main SHA before mutation, one logical Ready PR,
same-scope repairs in that PR, latest head green, exact-head squash merge, verify main and
cleanup, candidate publication separate, never rewrite main or published tags.

## OPNsense command authority

The default user console is root `csh`. Commands supplied for OPNsense must be csh-valid.
When POSIX syntax is required, explicitly invoke `/bin/sh` or enter `sh` and return with
`exit`.

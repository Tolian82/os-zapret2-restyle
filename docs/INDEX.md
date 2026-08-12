# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

A full repository-wide reading is required only for a repository-wide audit or genuine
full-context recovery. Focused work uses the risk-based specialist reading defined in
`AGENTS.md`.

For a current diagnosis, **do not start from an old evidence file**. Read the current state,
current release/patch, current PR/live comments and latest dated evidence first. Historical
evidence remains preserved for comparison but does not override later source/live/release
state.

## Current release / Strategy Lab authorities

Read these first for current Strategy Lab or release work:

- `docs/PROJECT_STATE.md` — current package/source candidate, accepted runtime basis and next boundary;
- `docs/patches/v0.4.1_2.md` — accepted measurement-only Lua initialization patch;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md` — Lua initialization measurement/decision contract;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md` — accepted owner-installed Lua equivalence evidence;
- `docs/releases/v0.4.1.md` — stable v0.4.1 release content/protocol record;
- `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md` — exact v0.4.1 merge/tag/workflow/package/Pages publication evidence;
- `docs/devlog/2026-08-12-release-v0.4.1.md` — v0.4.1 release-preparation basis;
- `docs/patches/v0.4.0_26.md` — accepted workload-derived finite adaptive-budget patch;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — parent-budget calculation/deadline/evidence contract;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md` — detailed owner-live runtime basis;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — adaptive candidate/search and validation architecture;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — preferred one-worker bucket/source-port dispatcher architecture;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live regression inventory;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — accepted Model-B fallback/reference authority;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live selection policy.

### Current v0.4.1 boundary

`VERSION=0.4.1`, `PLUGIN_REVISION=2`; current source candidate:
`os-zapret2-restyle-0.4.1_2.pkg`.

Stable published package remains `os-zapret2-restyle-0.4.1_1.pkg`; stable upgrade smoke is
PASS. Testing prerelease `v0.4.1_2` is now owner-tested for its measurement-only scope.
Detailed production Strategy Lab behavioral evidence remains the unchanged `_26` owner-live
basis because `_2` did not change production Model C.

Published stable release identity:

- merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- semantic tag `v0.4.1`;
- Release workflow `31596979559` — SUCCESS;
- package size `180305` bytes;
- package digest `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- Pages deployment `5869308071` — SUCCESS.

`v0.4.1_2` measurement conclusion is accepted: all 16 native Stage-60 expansion candidates
use the same candidate-declared Lua dependency pair; with mandatory `zapret-auto.lua` and
`strategy_lab_model_c.lua`, every Model-C batch current init set equals the candidate-minimal
union. Corrected installed-path evidence reports all required files present,
`runtime_comparison_required=false`, and `conclusion=equivalent_init_set`. No production Lua
loading change is justified.

The `_2` measurement-only default path `/usr/local/share/zapret2/lua` differed from canonical
ResourceInventory `/usr/local/etc/zapret2/lua`; this is queued for correction in the next
packaged measurement patch. The next independent optimization is BLOB loading / startup / RSS
measurement.

Owner-live Extended `telegram.org`, `job.xhdgCU`, remains the detailed production runtime
baseline: Model C 16/16, no fallback, adaptive budget `150/120/270/120`, clean restoration
and no `19128-19130` residue.

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

Historical records stay under `docs/patches/`, `docs/devlog/`, `docs/verification/evidence/`, and `docs/audit/`.

Key retained comparison points:

- `_28` family reachability: `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`;
- `_32` Stage-60 timeout correction and late-stage containment: `docs/patches/v0.4.0_7.md`, `docs/patches/v0.4.0_8.md`;
- `_33` adaptive validation: `docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`;
- Model A cold reference: `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model B production integration: `docs/patches/v0.4.0_22.md` and `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C source-port corrective acceptance: `docs/patches/v0.4.0_25.md`, `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- Adaptive workload budget acceptance: `docs/patches/v0.4.0_26.md`, `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`, `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- v0.4.1 release: `docs/releases/v0.4.1.md`, `docs/devlog/2026-08-12-release-v0.4.1.md`, `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`;
- Lua initialization measurement: `docs/patches/v0.4.1_2.md`, `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`, `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

Historical evidence explains progression; it never overrides a later patch/PR/live/release record.

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
5. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
6. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
7. current focused delivery decisions when applicable;
8. `docs/GITHUB_WORKFLOW.md`.

Key rules: connected GitHub plugin first; exact `main` SHA before mutation; one logical task
branch and Ready PR; same-scope repairs in that PR; latest head must pass required checks;
universal versioned titles for every task commit/PR/squash; squash with expected head SHA;
verify `main` and cleanup; candidate publication is separate; never rewrite `main` or a
published tag.

## OPNsense command authority

The default user console is root `csh`. Commands supplied for OPNsense must be csh-valid.
When POSIX syntax is required, explicitly enter `sh`, run the POSIX block, then `exit` back
to csh.

See `docs/WORKING_CONVENTIONS.md` and `AGENTS.md` for the full command-dialect rule.

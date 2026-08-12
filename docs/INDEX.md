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
installed/current patch, current PR/live comments and latest dated evidence first.
Historical evidence remains preserved for comparison but does not override later source/live
state.

## Current release / Strategy Lab authorities

Read these first for current Strategy Lab or release work:

- `docs/PROJECT_STATE.md` — current release-preparation source, accepted runtime basis and next boundary;
- `docs/releases/v0.4.1.md` — current full-release record;
- `docs/devlog/2026-08-12-release-v0.4.1.md` — exact v0.4.1 release-preparation basis/protocol;
- `docs/patches/v0.4.0_26.md` — accepted workload-derived finite adaptive-budget patch;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — current parent-budget calculation, deadline and evidence contract;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md` — current owner-live PASS and measured production budget evidence;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md` — exact `_26` source/CI/prerelease identity;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — adaptive candidate/search and validation architecture;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — preferred one-worker bucket/source-port dispatcher architecture;
- `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md` — source-port lease corrective live baseline;
- `docs/patches/v0.4.0_25.md` — accepted controlled-source-port lease corrective;
- `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md` — prior Model-C proof and shared-port defect input;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live regression inventory;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — accepted width-three Model B fallback/reference authority;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md` — accepted Model-B owner-live comparison baseline;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live selection policy.

### Current v0.4.1 release boundary

Release-preparation source is `VERSION=0.4.1`, `PLUGIN_REVISION=1`; current source
candidate is `os-zapret2-restyle-0.4.1_1.pkg`.

The current published and owner-tested runtime basis remains testing prerelease
`v0.4.0_26`, exact runtime commit
`8ada9cba28916fff506f19b34f5ef3de16e2008e`, until the v0.4.1 full Release workflow has
built and published the new package from the verified release-preparation merge.

Owner-live Extended `telegram.org`, `job.xhdgCU`, closed the selected runtime gate:

- `policy=eligible-work-v1` persisted after Stage 30;
- measured matrix was two endpoints, IPv4 only, QUIC closed, Generic UDP inactive;
- effective budget was exactly Standard `150 s`, Extended `120 s`, search `270 s`, Stage 80 `120 s`;
- Stage 60 Model C completed 16/16, `graph_exhausted`, `.parallel.fallbacks=[]`;
- Stage 60 `34209 ms`, total `114644 ms`;
- final `NO_CANDIDATE` and clean Stage-90 restoration;
- post-job Zapret2 RUNNING and no `19128-19130` residue.

Durable owner-live record:
`docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Stage 60 remains
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`;
`preferred-free-else-alternate` source-port leasing remains active.

The release-preparation PR introduces no new Strategy Lab runtime behavior. Its required
squash subject is `v0.4.1_1: Prepare release v0.4.1`; after merge the repository must create
semantic tag `v0.4.1` and publish package `os-zapret2-restyle-0.4.1_1.pkg`, checksum and the
matching `FreeBSD:15:amd64` Pages/pkg repository.

## Current implementation authorities

### Strategy Lab core

- `docs/architecture/STRATEGY_LAB.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`
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
- Model B coexistence/reproducibility: `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md` and `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- Model B sequential exhaustive: `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`;
- Model B controlled parallel: `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md`, `docs/patches/v0.4.0_21.md`, and `docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`;
- Model B production integration: `docs/patches/v0.4.0_22.md` and `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C production-candidate publication/live evidence: `docs/patches/v0.4.0_23.md`, `docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md`, `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`;
- Model C source-port corrective acceptance: `docs/patches/v0.4.0_25.md`, `docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`, `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- Adaptive workload budget acceptance: `docs/patches/v0.4.0_26.md`, `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`, `docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md`, `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- v0.4.1 release preparation: `docs/releases/v0.4.1.md` and `docs/devlog/2026-08-12-release-v0.4.1.md`.

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

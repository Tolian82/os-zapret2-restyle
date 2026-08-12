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

## Current Strategy Lab authorities

Read these first for current Strategy Lab work:

- `docs/PROJECT_STATE.md` — current package candidate, verified live boundary and next action;
- `docs/patches/v0.4.0_25.md` — `_25` controlled-source-port lease corrective and adaptive-budget follow-up;
- `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md` — current owner-live PASS for `_25` Extended `telegram.org` Model-C no-fallback path;
- `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md` — prior `_23` live evidence that proved Model C and exposed the shared `42004` source-port collision;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — Model-C one-worker bucket/source-port dispatcher architecture;
- `docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md` — owner-authorized Model-C production direction;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live regression inventory;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — stable native Zapret2 graph, `CandidateSpec`, `ResourceInventory`, search epoch and validation architecture;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — accepted width-three Model B fallback/reference authority;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md` — accepted Model-B owner-live comparison baseline;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live selection policy.

### Current `_25` boundary

`VERSION=0.4.0`, `PLUGIN_REVISION=25`; published testing prerelease:
`os-zapret2-restyle-0.4.0_25.pkg` from runtime commit
`a5ecfbfd57820e30e5f2be450e510b96c00267e3`.

Normal Stage 60 prefers `C-warm-bucket-source-port-dispatch`, then accepted
`B-warm-worker-parallel-batched`, then cold Model A. `_25` keeps deterministic `42000+`
values as preferred identity ports but leases exact free concrete ports per admitted warm
batch. A foreign occupied port is skipped non-destructively; Model B fallback takes a fresh
lease rather than inheriting Model C's failed concrete port.

Owner-live `_25` Extended `telegram.org`, `job.5yGde5`:

- Model C production path;
- 16/16 candidates, zero winners, `graph_exhausted`;
- `.parallel.fallbacks=[]`;
- Stage 60 `34198 ms`;
- total job `114759 ms`;
- all six batches persisted lease evidence with `preferred-free-else-alternate` / `skip-only`;
- no real collision occurred in this run, so replacements remained zero;
- final `NO_CANDIDATE`, Stage-90 restoration PASS, service RUNNING, no `19128-19130` residue.

This closes the selected `_25` owner-live gate. The live run proves the lease wrapper is
active and the prior `_23` Telegram timeout/fallback path no longer occurs; automated focused
coverage remains the proof for alternate-port selection under an intentionally occupied port.

### Next Strategy Lab timing work

Adaptive budget must be derived from the actual eligible matrix:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

Available IPv6, QUIC and Generic UDP work should add finite proportional budget
automatically. Do not replace this with one guessed oversized static timeout. Use the clean
`_25` no-fallback timing baseline above for the next design.

## Current implementation authorities

### Strategy Lab core

- `docs/architecture/STRATEGY_LAB.md`
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
- Model C source-port corrective acceptance: `docs/patches/v0.4.0_25.md`, `docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`, `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

Historical evidence explains progression; it never overrides a later patch/PR/live record.

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

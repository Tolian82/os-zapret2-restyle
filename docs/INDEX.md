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

- `docs/PROJECT_STATE.md` — current package candidate, verified live boundary, blockers and
  next action;
- `docs/patches/v0.4.0_25.md` — current `_25` controlled-source-port lease corrective and
  explicit adaptive-budget follow-up;
- `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md` — owner-live evidence
  that Model C works on `job.FaLtIk` and that `job.G0wC5l` reproduced the shared `42004`
  source-port collision through Model C -> Model B -> cold Model A;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — Model-C one-worker bucket/source-port
  dispatcher architecture;
- `docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md` — owner-authorized
  Model-C production direction;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live
  regression inventory;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — stable native Zapret2 graph,
  `CandidateSpec`, `ResourceInventory`, search epoch and validation architecture;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — accepted
  width-three Model B fallback/reference authority;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md` — accepted
  Model-B owner-live comparison baseline;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live
  selection policy.

### Current `_25` boundary

`VERSION=0.4.0`, `PLUGIN_REVISION=25`; source candidate is
`os-zapret2-restyle-0.4.0_25.pkg` pending CI/publication in the `_25` delivery cycle.

Normal Stage 60 still prefers `C-warm-bucket-source-port-dispatch`, then accepted
`B-warm-worker-parallel-batched`, then cold Model A. `_25` does not change search semantics.
It changes the concrete warm source-port plan from a blindly reused static port into a
per-batch exact lease: retain a preferred `420xx` port when free, otherwise skip the foreign
owner and allocate a unique free alternate. Model B fallback takes a fresh lease rather than
inheriting Model C's failed concrete port. Existing exact IPFW/curl/endpoint attribution is
unchanged.

The `_23` Extended `rutracker.org` owner-live run `job.FaLtIk` proved real one-worker Model C
16/16 without fallback. Extended `telegram.org` `job.G0wC5l` proved the defect: both Model C
and Model B failed on the same occupied `42004`, cold Model A completed 13 candidates, and
Stage 60 stopped for insufficient budget. Semantic restoration remained exact.

### Required adaptive-budget follow-up

After source-port collision amplification is removed and measured, Strategy Lab timing must
be redesigned around the actual eligible matrix:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

Available IPv6, QUIC and Generic UDP work should add a finite proportional budget
automatically. Do not replace this with one guessed oversized static timeout. `_25` records
this requirement but intentionally does not implement it.

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

Historical records stay under `docs/patches/`, `docs/devlog/`,
`docs/verification/evidence/`, and `docs/audit/`.

Key retained comparison points:

- `_28` family reachability:
  `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`;
- `_32` Stage-60 timeout correction and late-stage containment:
  `docs/patches/v0.4.0_7.md`, `docs/patches/v0.4.0_8.md`;
- `_33` adaptive validation:
  `docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`;
- Model A cold reference:
  `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model B coexistence/reproducibility:
  `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md` and
  `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- Model B sequential exhaustive:
  `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`;
- Model B controlled parallel:
  `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md`,
  `docs/patches/v0.4.0_21.md`, and
  `docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`;
- Model B production integration:
  `docs/patches/v0.4.0_22.md` and
  `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C production-candidate publication/live evidence:
  `docs/patches/v0.4.0_23.md`,
  `docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md`, and
  `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`.

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

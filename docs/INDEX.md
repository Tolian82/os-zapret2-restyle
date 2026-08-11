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
installed/current patch, current PR/live comments and latest dated evidence first. Historical
evidence remains preserved for comparison but does not override later source/live state.

## Current Strategy Lab authorities

Read these first for current Strategy Lab work:

- `docs/PROJECT_STATE.md` — current package candidate, publication state, runtime ownership,
  verified live baseline, watch items and next action;
- `docs/patches/v0.4.0_23.md` — current published `_23` Model-C production-candidate contract;
- `docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md` — owner's direct
  Model-C switch decision and Model C -> Model B -> Model A fail-closed boundary;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — current Model-C dispatcher/bucket runtime
  architecture;
- `docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md` — exact `_23` main/tag,
  package, workflow and digest publication evidence; owner-live acceptance remains pending;
- PR #177 conversation — implementation and publication closeout for `_23`;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md` — latest
  completed owner-live baseline until `_23` appliance testing is supplied;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live
  regression inventory and `_23` change-specific pending gate;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — stable native Zapret2 graph,
  `CandidateSpec`, `ResourceInventory`, search epoch and validation architecture;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — historical A/B experiment
  methodology/evidence and future optimization questions; it does not override the current
  Model-C patch/decision/architecture above;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — accepted
  width-three Model B decision retained as `_23` fallback/reference authority;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live
  selection policy.

### Current `_23` boundary

`v0.4.0_23` is **published** from exact main commit
`77b1beec471d161fb80584bf884e98970d4c75b3`. The verified asset is
`os-zapret2-restyle-0.4.0_23.pkg`, size `177429` bytes, digest
`sha256:f735f88e62fc82e5e856123f0d7c3dc26bd550b3ec0d5ab0e72bb2277dabe364`.
Publication workflow run `31520848437` passed and deleted the temporary publication branch.

Normal Stage 60 now prefers `C-warm-bucket-source-port-dispatch`: up to three currently-ready
candidates share one warm physical `dvtws2` bucket and are selected by exact controlled
client source ports through packaged Lua orchestration. Candidate-specific
payload/range/Lua/BLOB semantics remain exact. Accepted `_22` Model B is the immediate
runtime fallback/reference and cold Model A remains the final fail-closed fallback.

Publication does not constitute owner-live acceptance. The latest completed appliance
baseline remains `_22` until the owner tests the published `_23` package.

### Latest accepted `_22` live baseline

- Standard `telegram.org` `job.KpLHgb`: Model B 16/16 graph exhaustion, zero winners,
  width-three overlap, no fallback, `NO_CANDIDATE`, clean restoration;
- Standard `rutracker.org` `job.GK0X66`: Model B 16/16, two Stage-60 winners, successful
  Stage 70/85, clean restoration;
- Extended `rutracker.org` `job.d5XV82`: one controlled-source-port conflict activated the
  designed cold Model-A fallback; the job still completed `SUCCESS` with clean restoration.

The current 16/16 behavior is not the historical Stage-60 fixed-parent-timeout defect;
that boundary was closed by `_7`/`_8`.

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

Historical records are retained under `docs/patches/`, `docs/devlog/`,
`docs/verification/evidence/`, and `docs/audit/`.

Key comparison points:

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
- Model B controlled parallel reject/corrective/accept:
  `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md`,
  `docs/patches/v0.4.0_21.md`, and
  `docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`;
- Model B production integration and owner-live closeout:
  `docs/patches/v0.4.0_22.md` and
  `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C production-candidate publication:
  `docs/patches/v0.4.0_23.md` and
  `docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md`.

Historical evidence explains progression; it must not be treated as current package
behavior without checking the later patch/PR/live records above.

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

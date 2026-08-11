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

- `docs/PROJECT_STATE.md` — current candidate, production architecture, current live boundary,
  watch items and next action;
- `docs/patches/v0.4.0_22.md` — current production Stage-60 controlled-parallel Model B contract
  and owner-live closeout;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md` — current `_22`
  owner-live production evidence;
- PR #175 conversation — current `_22` owner-live summary attached to the implementing PR;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live
  regression inventory and current `_22` change-specific boundary;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — accepted A/B evidence chain
  and boundary for any future runtime experiment;
- `docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md` — decision selecting
  the width-three controlled-parallel Model B architecture for production integration;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — native Zapret2 search graph,
  `CandidateSpec`, `ResourceInventory`, search-epoch and validation architecture;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed automated Python ownership;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md` — Python/shell ownership
  rationale and compatibility invariants;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — release-specific live
  selection policy.

### Current `_22` live summary

- Standard `telegram.org` `job.KpLHgb`: production Model B, 16/16 graph exhaustion, zero
  winners, width-three overlap, no fallback, `NO_CANDIDATE`, clean restoration;
- Standard `rutracker.org` `job.GK0X66`: production Model B, 16/16, two Stage-60 winners,
  successful Stage 70/85, `SUCCESS`, clean restoration;
- Extended `rutracker.org` `job.d5XV82`: one controlled-source-port conflict triggered the
  designed fail-closed cold Model A fallback; the job still completed `SUCCESS` with clean
  restoration.

The current 16/16 Standard `rutracker.org` result is not the historical fixed Stage-60
parent-timeout defect. `_7` already closed that defect. The supplied `_22` run found two
Stage-60 winners, below the target of three, so graph exhaustion is truthful current
behavior.

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

### Strategy Lab historical corrective/evidence chain

Historical records are retained under:

- `docs/patches/`
- `docs/devlog/`
- `docs/verification/evidence/`
- `docs/audit/`

Key active historical comparison points:

- `_28` family-reachability evidence:
  `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`;
- `_32` Stage-60 timeout correction:
  `docs/patches/v0.4.0_7.md` and
  `docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`;
- `_32` late-stage containment closeout:
  `docs/patches/v0.4.0_8.md` and
  `docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md`;
- `_33` adaptive-validation historical live evidence:
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
  `docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`.

Historical evidence should be used to understand progression and retained correctness
boundaries. It must not be treated as the current package behavior without checking later
patch/PR/live records.

## Audit authorities

- `docs/AUDIT.md` — consolidated audit register;
- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md` — third Strategy Lab audit;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md` — earlier hardening audit;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md` — shell-era source/CI closure.

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

Stable-release preparation records remain under `docs/releases/` and the corresponding dated
`docs/devlog/` entries.

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

Key rules:

- use the connected GitHub plugin first;
- fix the exact current `main` SHA before mutation;
- one logical task branch and Ready PR;
- same-scope repair stays in that PR;
- required checks must pass on the latest head;
- every PR title, every PR-branch commit subject, and final squash subject use the universal versioned title contract;
- squash merge with expected head SHA;
- verify `main` and cleanup;
- candidate publication is separate from the code PR;
- do not mutate source in response to external infrastructure failure;
- read exact failed-job evidence before repairing CI;
- `main` and published tags are never force-updated.

## OPNsense command authority

The default user console is root `csh`. Commands supplied for OPNsense must be csh-valid.
When POSIX syntax is required, explicitly enter `sh`, run the POSIX block, then `exit` back
to csh.

See `docs/WORKING_CONVENTIONS.md` and `AGENTS.md` for the full command-dialect rule.
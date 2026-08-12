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
- `docs/patches/v0.4.1_5.md` — current measurement-only discovery-probe agreement/cost package candidate;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — experiment selection and acceptance authority, including discovery-vs-deep question 10;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — production discovery/stability/deep validation architecture;
- `docs/patches/v0.4.1_4.md` — accepted measurement-only BLOB common-set scaling candidate;
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md` — accepted `_3` and `_4` BLOB measurements and closed negative optimization result;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md` — accepted `_4` owner-live common-set startup/readiness/RSS evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md` — exact `_4` testing publication evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md` — accepted owner-installed single-BLOB startup/readiness/RSS evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md` — exact `_3` testing publication evidence;
- `docs/patches/v0.4.1_3.md` — accepted `_3` measurement patch history;
- `docs/patches/v0.4.1_2.md` — accepted measurement-only Lua initialization patch;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md` — accepted Lua measurement/decision contract;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md` — accepted Lua equivalence evidence;
- `docs/releases/v0.4.1.md` — stable v0.4.1 release record;
- `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md` — stable publication evidence;
- `docs/patches/v0.4.0_26.md` — accepted workload-derived adaptive-budget patch;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — adaptive-budget contract;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md` — detailed production owner-live runtime basis;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — preferred one-worker source-port dispatcher architecture;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical live regression inventory;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — completed Python ownership.

### Current v0.4.1 boundary

`VERSION=0.4.1`, `PLUGIN_REVISION=5`; current source candidate is
`os-zapret2-restyle-0.4.1_5.pkg`, a measurement-only discovery-probe package whose CI artifact is
pending. No `_5` tag/Release/prerelease/Pages/pkg-repository publication is authorized by the
current package request.

Stable published package remains `os-zapret2-restyle-0.4.1_1.pkg`; latest published testing
prerelease and latest owner-tested testing candidate remain `_4`. Detailed production Strategy Lab
evidence remains `_26` because `_2`, `_3`, `_4`, and `_5` do not change production behavior.

`_5` measures adaptive-search question 10: agreement and cost for `HEAD`, one-byte GET and the
current 4 KiB discovery GET against the existing cold deep-GET finalist reference. It reuses the
same reference job, pinned endpoint epoch, native TLS 1.3 candidate specifications and candidate
interception attribution. The lifecycle wrapper owns the shared Zapret2 lock, temporarily stops
normal Zapret2 for cold candidate replays, cleans residue and restores semantic lifecycle evidence.
Production discovery remains the bounded 4 KiB GET until owner-live evidence demonstrates zero
false PASS and a material reproducible cost advantage.

The `_3` accepted owner run completed 27 starts, 9 per variant. Median stable readiness was
`63.061 / 62.652 / 62.566 ms` for BLOB-free / built-in / external respectively, while median
ready and settled RSS was exactly `4360 KiB` for all variants. Lifecycle restoration and cleanup
passed. The observed sub-1% readiness differences did not establish a BLOB startup penalty and do
not justify a production Model-C change.

The `_4` accepted owner run completed 48 starts, 12 per variant, using the same `external` worker
and divert port `9992` across BLOB-free, inline `0x1603`, one external `fake_tls_7`, and a
three-external TLS common set with two intentionally eager/unused declarations. All sample,
cleanup, worker-identity and lifecycle-restoration checks passed.

Primary `external-common-3` versus `external-single` median stable-readiness delta was only
`+0.234 ms` / `+0.375%`; median ready/settled RSS delta was `+2 KiB` / `+0.046%`. Readiness
stdev was `2.276 ms` for common-3 and `5.502 ms` for single, so the measured delta is below normal
jitter. The common-set mean/p90 were also not worse. No material BLOB common-set startup/RSS cost
was established at the current production width-three bound.

The Model-C Lua initialization and BLOB startup/RSS optimization questions are therefore closed
without production changes. Production Model C remains unchanged and
`production_change_recommended=false`.

`v0.4.1_4` was published from exact merge `461fe2d045b131f3400f285a9cb59808b5f33ce2` by workflow
`31633335688`. Release asset `os-zapret2-restyle-0.4.1_4.pkg` is `186024` bytes with digest
`sha256:934fdd3a73117b3d914c9823f29eb7f2ca47196d97c30d94e3066a38159edbc9`.

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
- accepted single-BLOB measurement: `docs/patches/v0.4.1_3.md`, `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`, `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`;
- accepted common-set scaling measurement: `docs/patches/v0.4.1_4.md`, `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`, `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md`, `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`;
- current discovery-probe measurement: `docs/patches/v0.4.1_5.md`.

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

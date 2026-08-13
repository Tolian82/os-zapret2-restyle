# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

**Completion is mandatory:** every selected required document must be read from its first line through EOF before project action. If a tool truncates, clamps, paginates, or range-limits the response, continue fetching the remaining ranges until EOF. Opening/fetching a file is not by itself a completed read.

A full repository-wide reading is required only for a repository-wide audit or genuine
full-context recovery. Focused work uses the risk-based specialist reading defined in
`AGENTS.md`. For current diagnosis, later patch/live/release records outrank historical
records.

## Current release / Strategy Lab authorities

Read these first for current Strategy Lab or release/package work:

- `docs/PROJECT_STATE.md` — current source/published candidates, accepted runtime basis and next boundary;
- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md` — every owner-facing package is persistently delivered from GitHub; Actions/sandbox files are not final delivery; required documents must be read through EOF;
- `docs/patches/v0.4.1_6.md` — accepted discovery cleanup-finalizer corrective; production Model C and GET-4K unchanged;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md` — exact `_6` persistent testing-package publication and corrected owner-live `measurement_accepted` evidence;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-input.md` — preserved owner-live Rutracker/YouTube Stage-60 and PASS-path inputs for the corrective;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-source-verification-plan.md` — `_6` source/CI/live verification contract;
- `docs/patches/v0.4.1_5.md` — published measurement-only discovery-probe agreement/cost package and collected multidomain result;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-cleanup-finalizer-root-cause.md` — confirmed `_5` numeric-boolean finalizer defect;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-ci-package-artifact.md` — exact `_5` CI build artifact evidence; historical build evidence only after persistent publication;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md` — exact `_5` persistent GitHub testing-package publication;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — experiment selection and acceptance authority, including discovery-vs-deep question 10;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — production discovery/stability/deep validation architecture;
- `docs/patches/v0.4.1_4.md` — accepted measurement-only BLOB common-set scaling candidate;
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md` — accepted `_3` and `_4` BLOB measurements and closed negative optimization result;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md` — accepted `_4` owner-live common-set startup/readiness/RSS evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md` — exact `_4` testing publication evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md` — accepted owner-installed single-BLOB startup/readiness/RSS evidence;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md` — exact `_3` testing publication evidence;
- `docs/patches/v0.4.1_3.md` — accepted `_3` measurement patch history;
- `docs/patches/v0.4.1_2.md` — accepted `_2` measurement patch history;
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

`VERSION=0.4.1`, `PLUGIN_REVISION=6`; current source candidate is
`os-zapret2-restyle-0.4.1_6.pkg`. `_6` is persistently published and owner-live accepted for the discovery cleanup-finalizer corrective. The latest persistently published testing package and latest owner-tested testing candidate are both `_6`.

Exact `_5` historical build-artifact identity:

- source PR #197 final head `a7504d95b2b5f0fe3c0b0bccea359e8f22148181`;
- merged source commit `3f85d34f415d49c2b9a3ae25bd8bdebdad2f84dd`;
- identical tree on both: `3498b759161b14369921e9a47787e82ddbace6a2`;
- latest-head CI `31645083105` / #785 — SUCCESS;
- artifact ID `9160582106`, name `os-zapret2-restyle-0.4.1_5`;
- package inside the artifact `os-zapret2-restyle-0.4.1_5.pkg`, `410452` bytes;
- SHA-256 `d2a8de95bb128739bcf59325433f97b6c28eb819124131c867f0f3cea9d67b4e`;
- post-merge main CI `31645659351` / #786 — SUCCESS (`Verify main integrity` PASS).

Exact `_5` persistent GitHub testing-package identity:

- publication workflow run `31652568754` / #42 — SUCCESS;
- testing tag `v0.4.1_5` targets exact source commit `3f85d34f415d49c2b9a3ae25bd8bdebdad2f84dd`;
- GitHub Release ID `369590644`, `draft=false`, `prerelease=true`;
- package asset ID `512227845`;
- package `os-zapret2-restyle-0.4.1_5.pkg`, `188854` bytes;
- package SHA-256 `f3c55966658d336a3f51a76d0847f194f79ba13d9e140553e7fa9c308ec5f6ce`;
- direct URL `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_5/os-zapret2-restyle-0.4.1_5.pkg`;
- publication branch `publish/v0.4.1_5` was deleted by the successful workflow;
- no GitHub Pages or pkg-repository promotion occurred.

Exact `_6` persistent GitHub testing-package and live identity:

- exact source/squash merge `9a76551d17289fa6a125c10fabedf87241d1a490`;
- source tree `36019521fb74c1736a9c6da822780133df639820`;
- latest-head packaged CI `31687601966` / #808 — SUCCESS;
- post-merge main CI `31688215371` / #809 — SUCCESS;
- publication workflow run `31689302668` / #43 — SUCCESS;
- testing tag `v0.4.1_6` targets exact source commit `9a76551d17289fa6a125c10fabedf87241d1a490`;
- GitHub Release ID `369818027`, `draft=false`, `prerelease=true`;
- package asset ID `512818044`;
- package `os-zapret2-restyle-0.4.1_6.pkg`, `188907` bytes;
- package SHA-256 `e708d2ac0eb13d41d1d79da96e2b5f1f6e9d4fc9e138366fd4e72e30b96a02b7`;
- direct URL `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_6/os-zapret2-restyle-0.4.1_6.pkg`;
- publication branch `publish/v0.4.1_6` was deleted by the successful workflow;
- no GitHub Pages or pkg-repository promotion occurred;
- corrected owner-live `rutracker.org` measurement on retained `job.lWLjqL` concluded `measurement_accepted`;
- immediate cleanup checks showed no IPFW `19100-19131` residue, no candidate process/socket on `9989`, and normal Zapret2 restored running;
- evidence: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`.

Stable published package remains `os-zapret2-restyle-0.4.1_1.pkg`; latest persistently published and owner-tested testing package is `_6`. Detailed accepted production Strategy Lab evidence remains `_26` because `_2` through `_6` do not change production behavior.

The `_5` multidomain set covered Telegram zero-winner exhaustive, Rutracker two-winner exhaustive and YouTube three-winner early-stop Model-C execution without fallback. Rutracker Stage 60 completed in `24204 ms`; YouTube Stage 60 completed in `9151 ms`. Each cheap probe recorded 29/29 agreement on comparable pairs across the three corpora with zero false PASS and zero false FAIL, plus one expected Rutracker deep-inconclusive short-resource pair.

Pooled equal-sample mean total times were approximately `3452.97 ms` for HEAD, `3442.37 ms` for GET-1 and `3439.70 ms` for current GET-4K. No material latency benefit for HEAD or GET-1 was established, so production discovery remains bounded GET-4K.

`_6` corrected only the `_5` finalizer interface: shell numeric cleanup values `1`/`0` are decoded together with textual `true`/`false`, and unknown values fail closed. Regression coverage proved successful cleanup can produce `measurement_accepted`, and the owner-live corrected Rutracker repeat now produced exactly that accepted conclusion with clean residue/lifecycle checks. The finalizer corrective and discovery-probe optimization question are closed without a production change.

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

The Model-C Lua initialization, BLOB startup/RSS and discovery-probe optimization questions are therefore closed without production changes. Production Model C and GET-4K remain unchanged and `production_change_recommended=false`.

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
- discovery-probe measurement: `docs/patches/v0.4.1_5.md`, historical build evidence `docs/verification/evidence/2026-08-13-v0.4.1_5-ci-package-artifact.md`, persistent package publication `docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md`, root cause `docs/verification/evidence/2026-08-13-v0.4.1_5-cleanup-finalizer-root-cause.md`;
- accepted discovery cleanup finalizer corrective: `docs/patches/v0.4.1_6.md`, preserved live input `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-input.md`, accepted publication/live evidence `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`.

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

For GitHub work, read in this order **through EOF**:

1. current owner instruction;
2. repository-root `AGENTS.md`;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
5. `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
6. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
7. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
8. `docs/GITHUB_WORKFLOW.md`.

Key rules: GitHub plugin first, read required authorities completely through EOF, exact main SHA before mutation, one logical Ready PR, same-scope repairs in that PR, latest head green, exact-head squash merge, verify main and cleanup. Every owner package request means a persistent GitHub `.pkg`; Actions artifacts and sandbox/local files are build evidence only, never final package delivery. Candidate package publication is separate from a full semantic project release; never rewrite main or published tags.

## OPNsense command authority

The default user console is root `csh`. Commands supplied for OPNsense must be csh-valid.
When POSIX syntax is required, explicitly invoke `/bin/sh` or enter `sh` and return with
`exit`.

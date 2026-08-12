# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Later current patch/live/release records override
historical implementation evidence for current state.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=4`
Current source candidate: `os-zapret2-restyle-0.4.1_4.pkg`
Current published release tag: `v0.4.1`
Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`
Latest published testing prerelease: `v0.4.1_4` / `os-zapret2-restyle-0.4.1_4.pkg`
Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS
Latest owner-tested testing candidate: `v0.4.1_4` — BLOB common-set scaling measurement PASS
Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Stable v0.4.1 identity:

- merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- semantic tag `v0.4.1`;
- package `os-zapret2-restyle-0.4.1_1.pkg`;
- digest `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- evidence: `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`.

Accepted `_2` evidence:

- runtime/source merge `462c55b291ac737eb368ee9ec5e4f139bd239665`;
- tag `v0.4.1_2`, workflow `31605249326` — SUCCESS;
- package `os-zapret2-restyle-0.4.1_2.pkg`, `181696` bytes;
- digest `sha256:09d0edacd0527230a2657128c80099e6436f41b14621f5573586b4cc6fed9063`;
- owner-live: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

Published and owner-tested `_3` identity:

- runtime/source merge `da427cd061df1f3cbc01ba11a14a6417f2e406b3`;
- merge tree `fec062533bb971450cf197a3365de3ef2e1f3c60`;
- PR #190 and CI run `31615648930` — SUCCESS;
- post-merge main CI run `31616335987` — SUCCESS;
- publication workflow run `31616501996` — SUCCESS;
- tag `v0.4.1_3` targets exact runtime/source merge;
- GitHub Release ID `369373181`, prerelease=true;
- package `os-zapret2-restyle-0.4.1_3.pkg`, `185310` bytes;
- digest `sha256:6efdb8e844bdec5cbe2fddffd77c1234cc53b939520c4648ed68da3126e7989b`;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`;
- owner-live evidence: `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`.

Published and owner-tested `_4` testing identity:

- runtime/source merge `461fe2d045b131f3400f285a9cb59808b5f33ce2`;
- merge tree `844d9992dcab35f630ee6acd3bf2ab5bbaf4c248`;
- PR #193 final latest-head CI run `31628622306` — SUCCESS;
- post-merge main CI run `31629464779` — SUCCESS;
- publication workflow run `31633335688` — SUCCESS;
- tag `v0.4.1_4` targets exact runtime/source merge;
- GitHub Release ID `369482221`, draft=false, prerelease=true;
- package `os-zapret2-restyle-0.4.1_4.pkg`, `186024` bytes;
- digest `sha256:934fdd3a73117b3d914c9823f29eb7f2ca47196d97c30d94e3066a38159edbc9`;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md`;
- owner-live evidence: `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`.

`_3` is accepted for its BLOB-free / built-in / representative single-external-file scope.
`_4` is accepted for the remaining bounded common-set scaling scope. Because `_2`, `_3`, and `_4`
are measurement-only, detailed production behavior still uses the accepted `_26` runtime evidence.

==================================================
CURRENT AUTHORITIES
==================================================

Current GitHub delivery authority: `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`;
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`;
- `docs/patches/v0.4.1_4.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`;
- `docs/patches/v0.4.1_3.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current Stage-60 chain remains
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.
Candidate width remains at most 3, pinned endpoints inside one candidate remain sequential,
and source-port leasing remains `preferred-free-else-alternate`.

==================================================
ACCEPTED OWNER-LIVE PRODUCTION RUNTIME BASIS
==================================================

Extended `telegram.org`, `job.xhdgCU`:

- `policy=eligible-work-v1`, effective budgets `150/120/270/120`;
- Stage 60 `C-warm-bucket-source-port-dispatch`, 16/16, graph exhausted, zero winners;
- `.parallel.fallbacks=[]`;
- Stage 60 duration `34209 ms`; total job duration `114644 ms`;
- Stage 90 restoration succeeded; Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

==================================================
V0.4.1_2 LUA INITIALIZATION — ACCEPTED
==================================================

Corrected owner-installed `_2` measurement: `candidate_count=16`, all six batches
`equivalent_init_set=true`, `checks.all_required_files_present=true`,
`checks.production_model_unchanged=true`, `runtime_comparison_required=false`,
`conclusion=equivalent_init_set`.

Current Model-C Lua initialization already equals the candidate-minimal union, so this
optimization is closed without a production change. `_3` fixed `_2` resource discovery by
deriving the Lua default from canonical ResourceInventory (`/usr/local/etc/zapret2/lua`; fake
root `/usr/local/etc/zapret2/files/fake`).

==================================================
V0.4.1_3 BLOB STARTUP / RSS MEASUREMENT — ACCEPTED
==================================================

Policy `blob-startup-rss-v1` compared BLOB-free, built-in `fake_default_tls`, and external
`fake_tls_7.bin` variants with the common Model-C Lua/action shape held constant.

The owner-installed run completed all 27 planned startups, 9 per variant, with
`adapter_preflight=true`, `all_samples_ready=true`, `expected_sample_count=true`,
`temporary_workers_clean=true`, `cleanup_ok=true`, `lifecycle_restored=true`, and
`conclusion=measurement_accepted`.

Median stable readiness:

- BLOB-free `63.061 ms`;
- built-in `62.652 ms`;
- external `62.566 ms`.

Median ready and settled RSS was exactly `4360 KiB` for every variant. Built-in vs BLOB-free
median readiness delta was `-0.409 ms` (`-0.649%`); external vs BLOB-free was `-0.495 ms`
(`-0.785%`). These sub-1% differences were below observed within-variant jitter/tails and did
not show a material BLOB startup penalty.

Initial/final normal service, config, runtime-args and firewall evidence matched exactly and
remained RUNNING. The run used `cache_policy=natural-cache-no-drop` and is not a cold-cache
claim. Production Model C remained unchanged and `production_change_recommended=false`.

==================================================
V0.4.1_4 BLOB COMMON-SET SCALING — ACCEPTED / OPTIMIZATION CLOSED
==================================================

Policy: `blob-common-set-scaling-v1`, schema `2`.

The owner-installed run completed all `48` planned starts, `12` per variant, with every acceptance
check true: adapter preflight, all samples ready, balanced trial count, expected sample count,
single worker identity, temporary worker cleanup, cleanup, and lifecycle restoration.
Final conclusion: `measurement_accepted`.

All variants used one physical adapter worker `external` on divert port `9992`. Controlled variants
were BLOB-free, inline `0x1603`, one external `fake_tls_7`, and a three-external TLS common set in
which only `fake_tls_7` was active while the other two declarations were intentionally eager/unused.
The common set scaled from `226` declared bytes to `3825` bytes while retaining the current maximum
production candidate width of three.

Primary `external-common-3` vs `external-single` result:

- median stable readiness `62.566` vs `62.332 ms`: `+0.234 ms` / `+0.375%`;
- readiness stdev `2.276` vs `5.502 ms`;
- readiness mean `63.610` vs `65.055 ms`;
- readiness p90 `66.033` vs `72.535 ms`;
- median ready/settled RSS `4362` vs `4360 KiB`: `+2 KiB` / `+0.046%`.

The median readiness/RSS deltas are substantially below measured run-to-run spread and the
mean/p90 direction does not show a common-set penalty. Supporting BLOB-free and inline comparisons
are likewise sub-percent and below jitter.

Initial and final normal-service evidence matched exactly and remained RUNNING:

- effective-config hash `e63f62a3ec541d4c3c2bd4e4c5d2efdc69c1cda18cd844b2d7069213156ac8d7`;
- runtime-args hash `b4f5d08dd3f6c6e53f3ad970fc3c9cfbfbb004fee54ec1241c668ddd7bcdffc4`;
- normal-firewall hash `8b6952782a6862a5c86fcc688438c746a57948d1b98c927c5ba1fe8bbf3ee0dd`.

Combined with `_3`, the current width-three architecture has no measured material BLOB
startup/readiness or RSS cost. Production Model C remains unchanged, lazy BLOB loading is not
justified, and the BLOB-loading startup/RSS optimization is closed as a negative result for the
present architecture. `production_change_recommended=false` remains correct.

Owner-live evidence:
`docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

The Model-C Lua initialization and BLOB startup/RSS optimization questions are both closed by
owner-live evidence without production changes. Do not create another package revision solely for
Lua/BLOB loading optimization.

The next Strategy Lab optimization must be selected from the remaining adaptive-search experiment
questions and measured separately. Production behavior remains
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback` until a
new experiment independently justifies a change.

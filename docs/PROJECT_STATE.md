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
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=3`
Current source candidate: `os-zapret2-restyle-0.4.1_3.pkg`
Current published release tag: `v0.4.1`
Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`
Latest published testing prerelease: `v0.4.1_3` / `os-zapret2-restyle-0.4.1_3.pkg`
Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS
Latest owner-tested testing candidate: `v0.4.1_2` — Lua initialization measurement PASS
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

Published `_3` testing identity:

- runtime/source merge `da427cd061df1f3cbc01ba11a14a6417f2e406b3`;
- merge tree `fec062533bb971450cf197a3365de3ef2e1f3c60`;
- PR #190 and CI run `31615648930` — SUCCESS;
- post-merge main CI run `31616335987` — SUCCESS;
- publication workflow run `31616501996` — SUCCESS;
- tag `v0.4.1_3` targets exact runtime/source merge;
- GitHub Release ID `369373181`, prerelease=true;
- package `os-zapret2-restyle-0.4.1_3.pkg`, `185310` bytes;
- digest `sha256:6efdb8e844bdec5cbe2fddffd77c1234cc53b939520c4648ed68da3126e7989b`;
- evidence: `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`.

`_3` is published for owner-assisted measurement and remains owner-live pending. Because `_2`
and `_3` are measurement-only, detailed production behavior still uses the accepted `_26`
runtime evidence.

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
- `docs/patches/v0.4.1_3.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-measurement-publication.md`;
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
optimization is closed without a production change. `_3` also fixes `_2` resource discovery by
deriving the Lua default from canonical ResourceInventory (`/usr/local/etc/zapret2/lua`; fake
root `/usr/local/etc/zapret2/files/fake`).

==================================================
V0.4.1_3 BLOB STARTUP / RSS MEASUREMENT
==================================================

Policy `blob-startup-rss-v1` compares BLOB-free, built-in `fake_default_tls`, and external
`fake_tls_7.bin` variants with the common Model-C Lua/action shape held constant.

The lifecycle-locked harness launches one temporary `dvtws2` at a time on `9990..9992`, never
calls `route-add`, never stops/reconfigures normal Zapret2, and uses
`cache_policy=natural-cache-no-drop`. Default is 9 balanced/interleaved trials per variant.
It persists raw readiness/RSS samples, summaries and pairwise median deltas.

Acceptance requires matching initial/final semantic service/config/runtime/firewall evidence
plus clean temporary workers/rules. `_3` keeps `production_change_recommended=false`; one run
cannot authorize a production BLOB-loading change.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

`v0.4.1_3` source, CI, FreeBSD 15 build and testing-prerelease publication are PASS.
Remaining gate: owner installs `_3` and runs the isolated BLOB startup/readiness/RSS
measurement.

Owner-live acceptance requires `conclusion=measurement_accepted`, complete samples,
lifecycle restoration and cleanup PASS. Only reproducible evidence may justify a separate
future production BLOB-loading patch.

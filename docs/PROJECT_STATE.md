# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Historical implementation detail belongs in
`docs/patches/`, `docs/devlog/` and `docs/verification/evidence/` and must not override a
later current patch/live/release record.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=3`
Current source candidate: `os-zapret2-restyle-0.4.1_3.pkg`
Current published release tag: `v0.4.1`
Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`
Latest published testing prerelease: `v0.4.1_2` / `os-zapret2-restyle-0.4.1_2.pkg`
Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS
Latest owner-tested testing candidate: `v0.4.1_2` — Lua initialization measurement PASS
Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Stable v0.4.1 identity:

- merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- semantic tag `v0.4.1`;
- package `os-zapret2-restyle-0.4.1_1.pkg`;
- digest `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- stable publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`.

Accepted `_2` identity/evidence:

- runtime/source merge `462c55b291ac737eb368ee9ec5e4f139bd239665`;
- publication workflow run `31605249326` — SUCCESS;
- tag `v0.4.1_2` targeting exact runtime/source merge;
- package `os-zapret2-restyle-0.4.1_2.pkg`, size `181696` bytes;
- digest `sha256:09d0edacd0527230a2657128c80099e6436f41b14621f5573586b4cc6fed9063`;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-publication.md`;
- owner-live evidence: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

The owner-installed `_2` Lua measurement is PASS. Detailed production Strategy Lab behavioral
evidence remains the unchanged `_26` runtime basis because `_2` and `_3` are measurement-only
and do not change production Model C.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`;
- `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`;
- `docs/patches/v0.4.1_3.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
ACCEPTED OWNER-LIVE PRODUCTION RUNTIME BASIS
==================================================

Detailed production Strategy Lab live basis remains Extended `telegram.org`, `job.xhdgCU`:

- `policy=eligible-work-v1`, effective budgets `150/120/270/120`;
- Stage 60 `C-warm-bucket-source-port-dispatch`, 16/16, graph exhausted, zero winners;
- `.parallel.fallbacks=[]`;
- Stage 60 duration `34209 ms`; total job duration `114644 ms`;
- Stage 90 restoration succeeded; Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

==================================================
V0.4.1_2 LUA INITIALIZATION MEASUREMENT — ACCEPTED
==================================================

The corrected owner-installed `_2` measurement reported:

- `candidate_count=16`;
- all six current batches `equivalent_init_set=true`;
- `checks.all_required_files_present=true`;
- `checks.production_model_unchanged=true`;
- `runtime_comparison_required=false`;
- `conclusion=equivalent_init_set`.

Therefore current Model-C initialization already equals the candidate-minimal four-file union.
Lua initialization optimization is closed with no production runtime change.

`_3` removes the `_2` measurement-only duplicate path by deriving the default Lua root from
canonical `ResourceInventory`, whose installed roots are `/usr/local/etc/zapret2/lua` and
`/usr/local/etc/zapret2/files/fake` unless explicitly overridden by Strategy Lab environment.

==================================================
V0.4.1_3 BLOB STARTUP / RSS MEASUREMENT
==================================================

`v0.4.1_3` is measurement-only. Production Model C/B/A remains unchanged.

Policy `blob-startup-rss-v1` compares three isolated variants while keeping common Model-C
Lua/action shape fixed:

- BLOB-free;
- built-in `fake_default_tls`;
- external `fake_tls_7.bin` mapped through canonical ResourceInventory.

The lifecycle-locked harness launches one temporary `dvtws2` at a time through the accepted
narrow adapter on dedicated ports `9990..9992`. It never calls `route-add`, never stops or
reconfigures normal Zapret2, and does not drop OS caches. Default measurement is 9 trials per
variant with balanced/interleaved ordering. Readiness requires two consecutive qualified
snapshots; raw readiness and RSS samples plus pairwise median deltas are persisted.

Acceptance requires initial/final semantic service state/config/runtime/firewall evidence to
match and dedicated workers/rules to be clean. `_3` always reports
`production_change_recommended=false`; one accepted measurement is evidence for
reproducibility review, not permission to alter production BLOB loading.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

Current logical change: `v0.4.1_3` BLOB loading / startup / RSS measurement.

Required gates:

- focused measurement regression and canonical corrective matrix PASS;
- canonical resource-root correction PASS;
- production Model C/B/A, leasing and adaptive budgets unchanged;
- FreeBSD 15 package PASS;
- testing prerelease publication;
- owner-installed measurement with `conclusion=measurement_accepted`, complete samples,
  lifecycle restoration and cleanup PASS.

Only reproducible evidence may justify a separate future production BLOB-loading patch.

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
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=2`
Current source candidate: `os-zapret2-restyle-0.4.1_2.pkg`
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

Testing `_2` publication identity:

- runtime/source merge `462c55b291ac737eb368ee9ec5e4f139bd239665`;
- merge tree `94a879ff5bcb94713f9dfba9e1d7e06e08a77a9a`;
- PR #187 — SOURCE/CI/FreeBSD 15 PASS;
- publication workflow run `31605249326` — SUCCESS;
- tag `v0.4.1_2` targeting exact runtime/source merge;
- GitHub Release ID `369290077`, prerelease=true;
- package `os-zapret2-restyle-0.4.1_2.pkg`, size `181696` bytes;
- digest `sha256:09d0edacd0527230a2657128c80099e6436f41b14621f5573586b4cc6fed9063`;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-publication.md`;
- owner-live evidence: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

The owner upgraded the OPNsense appliance to stable `0.4.1_1` and reported successful
upgrade and normal operation. The owner then installed `_2`; its non-destructive Lua
measurement is accepted as PASS. Detailed production Strategy Lab behavioral evidence
remains the unchanged `_26` runtime basis because `_2` did not change production Model C.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_LUA_INITIALIZATION.md`;
- `docs/patches/v0.4.1_2.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-publication.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
ACCEPTED OWNER-LIVE RUNTIME BASIS
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

`v0.4.1_2` is measurement-only. Production Model C is intentionally unchanged.

Every one of the 16 native Stage-60 expansion candidates declares the same Lua dependencies:
`zapret-lib.lua` and `zapret-antidpi.lua`. Model C already initializes their batch union plus
mandatory `zapret-auto.lua` and `strategy_lab_model_c.lua`.

The corrected owner-installed measurement using the canonical installed Lua root reported:

- `candidate_count=16`;
- all six current batches `equivalent_init_set=true`;
- `checks.all_required_files_present=true`;
- `checks.production_model_unchanged=true`;
- `runtime_comparison_required=false`;
- `conclusion=equivalent_init_set`.

Therefore current Model-C initialization and the candidate-minimal union are the same
four-file set for every current native batch. No timing/RSS speedup claim is valid or needed,
and production Model C must not change for Lua initialization.

The `_2` measurement command itself used the wrong default Lua root
`/usr/local/share/zapret2/lua`; canonical ResourceInventory uses
`/usr/local/etc/zapret2/lua`. This affected measurement file-presence reporting only. The
next packaged measurement patch must remove that duplicate/default-path mismatch.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

`v0.4.1_2` source, CI, FreeBSD 15 build, testing-prerelease publication and owner-live
measurement are PASS. Lua initialization optimization is closed without a production runtime
change.

Next logical change: measurement-only BLOB loading / startup / RSS tradeoff analysis. It must
first correct the `_2` measurement default-path mismatch, preserve production Model C/B/A,
CandidateSpec resource identity, source-port attribution, deadlines, cleanup and restoration,
and establish measured startup/readiness/RSS evidence before any BLOB-loading optimization is
considered.

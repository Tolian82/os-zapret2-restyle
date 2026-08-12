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
Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS
Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Published v0.4.1 identity:

- release-preparation merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- merge tree `74e3a67cb25c0e80bc0c00f7214e8c00c3daa7b9`;
- semantic tag `v0.4.1`;
- annotated tag object `8c860a01def48a3b84943a43ba0c5a30d9f37055` targeting the exact merge;
- Release workflow run `31596979559` — SUCCESS;
- GitHub Release ID `369226460`;
- package `os-zapret2-restyle-0.4.1_1.pkg`;
- package size `180305` bytes;
- package digest `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- GitHub Pages deployment `5869308071` — SUCCESS;
- publication evidence: `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`.

The workflow-created GitHub Release currently has `prerelease=true`; this is the existing
release-workflow behavior and does not change the semantic tag/package identity above.

The owner subsequently upgraded the OPNsense appliance to `0.4.1_1` and reported that the
upgrade completed successfully and normal plugin/service operation remained correct. This
is a package-upgrade smoke record, not a replacement for the detailed `_26` Strategy Lab
runtime evidence.

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
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
ACCEPTED OWNER-LIVE RUNTIME BASIS
==================================================

The detailed selected Strategy Lab live basis remains Extended `telegram.org`, `job.xhdgCU`:

- `adaptive-budget.json` persisted `policy=eligible-work-v1`;
- measured matrix: Extended, 2 endpoints, IPv4 available, IPv6 unavailable, QUIC/IPv4
  closed, Generic UDP unconfigured;
- effective budgets: Standard `150 s`, Extended `120 s`, search `270 s`, Stage 80 `120 s`;
- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- `stopped_reason=graph_exhausted`, 16/16 candidates completed, zero winners;
- `.parallel.fallbacks=[]`;
- Stage 60 duration `34209 ms`; total job duration `114644 ms`;
- Stage 90 restoration succeeded; post-job Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

==================================================
V0.4.1_2 LUA INITIALIZATION MEASUREMENT
==================================================

`v0.4.1_2` is measurement-only. Production Model C is intentionally unchanged.

Source inspection established that every one of the 16 native Stage-60 expansion candidates
currently declares exactly the same two Lua dependencies: `zapret-lib.lua` and
`zapret-antidpi.lua`. Model C already initializes the union of candidate-declared dependencies
for the active width-three batch and additionally requires `zapret-auto.lua` plus
`strategy_lab_model_c.lua` for the shared dispatcher.

Therefore the current Model-C initialization set and the candidate-minimal set are identical
for every current native batch:

- `zapret-lib.lua`;
- `zapret-antidpi.lua`;
- `zapret-auto.lua`;
- `strategy_lab_model_c.lua`.

The packaged command `strategy_lab_python.py lua-init-measure` persists/reports this fact as
`policy=lua-init-set-equivalence-v1`. When the sets are identical it MUST emit
`equivalent_init_set`, `runtime_comparison_required=false`, and MUST NOT invent timing/RSS
speedup claims. The next optimization candidate is BLOB loading/startup/RSS measurement.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

The stable `v0.4.1 / 0.4.1_1` release cycle is complete and owner upgrade smoke passed.

Current logical change: `v0.4.1_2` Lua initialization measurement. Acceptance requires:

- source/CI/FreeBSD package PASS;
- production Model C remains unchanged;
- all 16 current native expansion candidates are represented;
- every current width-three batch proves current Model-C Lua init equals candidate-minimal
  Lua init;
- no runtime speedup/RSS claim is made when the sets are identical;
- testing prerelease publication for owner-visible evidence.

If `_2` confirms `equivalent_init_set`, close this optimization without a production runtime
change and proceed to the independent BLOB loading/startup/RSS tradeoff measurement.

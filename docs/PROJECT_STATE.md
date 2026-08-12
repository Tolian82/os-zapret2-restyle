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
Latest owner-tested testing candidate: `v0.4.1_3` — BLOB startup/readiness/RSS measurement PASS
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

Published `_4` testing identity:

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
- owner-live common-set measurement: pending.

`_3` is accepted for its BLOB-free / built-in / representative single-external-file scope.
`_4` is published for the remaining bounded common-set scaling measurement but is not yet
owner-tested. Because `_2`, `_3`, and `_4` are measurement-only, detailed production behavior
still uses the accepted `_26` runtime evidence.

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
V0.4.1_4 BLOB COMMON-SET SCALING — PUBLISHED / OWNER-LIVE PENDING
==================================================

`_4` answers the remaining bounded question: does the eager common external declaration set used
by Model C cost measurable startup/readiness or RSS when it scales from one to the current
production candidate width of three?

Policy: `blob-common-set-scaling-v1`, schema `2`.

All variants use one physical adapter worker `external` on divert port `9992`; arguments are
rewritten immediately before each launch. Controlled variants are:

- `blob-free`;
- `inline-small` with `seqovl_pattern=0x1603`;
- `external-single` with canonical `fake_tls_7`;
- `external-common-3` with canonical `fake_tls_7`,
  `tls_clienthello_rutracker_org_kyber`, and `tls_clienthello_vk_com_kyber`, while only
  `fake_tls_7` is active and the other two are intentionally eager/unused declarations.

The common set is a bounded synthetic production-width upper bound, not a claim about one exact
current graph bucket. The resources are semantically compatible TLS ClientHello files rather than
unrelated BLOBs chosen only to inflate count.

Default run: 12 trials per variant / 48 starts, balanced over all four cyclic orders,
`cache_policy=natural-cache-no-drop`. Summaries retain mean/stdev in addition to
min/median/p90/max so a common-set delta can be judged against normal jitter.

Focused regression, complete Strategy Lab corrective matrix, lifecycle/production contracts and
FreeBSD 15 package build/inspection passed before merge. Testing prerelease `v0.4.1_4` is now
published from exact merge `461fe2d045b131f3400f285a9cb59808b5f33ce2`; Release asset digest is
`sha256:934fdd3a73117b3d914c9823f29eb7f2ca47196d97c30d94e3066a38159edbc9`.

`production_change_recommended=false` remains hard-coded. `_4` has no owner-live result yet.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

Install the published `v0.4.1_4` package on the owner OPNsense appliance and collect the 12x4
common-set startup/readiness/RSS measurement under the documented lifecycle lock and csh command
rules.

A material `external-common-3` vs `external-single` cost must be reproduced before any production
change. If no material cost appears above jitter at the current width-three bound, close BLOB
loading as a negative optimization result for the present architecture.

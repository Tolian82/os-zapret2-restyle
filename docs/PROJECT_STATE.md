# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Read this document completely through EOF before acting. Later current patch/live/release records override historical implementation evidence for current state.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.1`, `PLUGIN_REVISION=6`
Current source candidate: `os-zapret2-restyle-0.4.1_6.pkg` — DISCOVERY CLEANUP FINALIZER CORRECTIVE / OWNER-LIVE PASS
Current published release tag: `v0.4.1`
Current published stable package: `os-zapret2-restyle-0.4.1_1.pkg`
Latest persistently published testing package: `v0.4.1_6` / `os-zapret2-restyle-0.4.1_6.pkg`
Latest owner-tested stable package: `os-zapret2-restyle-0.4.1_1.pkg` — upgrade/install smoke PASS
Latest owner-tested testing candidate: `v0.4.1_6` — discovery cleanup-finalizer corrective ACCEPTED / measurement_accepted
Latest detailed Strategy Lab runtime basis: `v0.4.0_26` — adaptive-budget owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Active package-delivery rule:

- every owner-facing package/patch requested for testing, installation or delivery must be persistently hosted on GitHub;
- a GitHub Actions artifact is build evidence only and is not final owner delivery;
- a local/container/sandbox file is never the final project package;
- `не релиз, а пакет` means no stable/full project release, but still requires persistent GitHub publication of the testing `.pkg`;
- authority: `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`.

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

Published `_5` is the measurement-only discovery-probe experiment. It compares
`HEAD`, one-byte GET and the existing 4 KiB discovery GET with the current finalist deep-GET
reference on the same pinned endpoint epoch and native candidate corpus.

`_5` build-artifact identity:

- source PR #197 final head `a7504d95b2b5f0fe3c0b0bccea359e8f22148181`;
- exact-head squash merge/main `3f85d34f415d49c2b9a3ae25bd8bdebdad2f84dd`;
- identical final source tree on both commits: `3498b759161b14369921e9a47787e82ddbace6a2`;
- latest-head CI run `31645083105` / #785 — SUCCESS;
- artifact ID `9160582106`, name `os-zapret2-restyle-0.4.1_5`;
- package inside artifact `os-zapret2-restyle-0.4.1_5.pkg`, `410452` bytes;
- package digest `sha256:d2a8de95bb128739bcf59325433f97b6c28eb819124131c867f0f3cea9d67b4e`;
- post-merge main CI run `31645659351` / #786 — SUCCESS (`Verify main integrity` PASS);
- evidence: `docs/verification/evidence/2026-08-13-v0.4.1_5-ci-package-artifact.md`.

The Actions artifact above proves `_5` was built and inspected, but it did not by itself satisfy owner package delivery under the GitHub-only rule. That delivery gate is closed by the persistent GitHub publication below.

Published `_5` testing-package identity:

- publication workflow run `31652568754` / #42 — SUCCESS;
- tag `v0.4.1_5` targets exact runtime/source merge `3f85d34f415d49c2b9a3ae25bd8bdebdad2f84dd`;
- GitHub Release ID `369590644`, `draft=false`, `prerelease=true`;
- package asset ID `512227845`;
- package `os-zapret2-restyle-0.4.1_5.pkg`, `188854` bytes;
- package digest `sha256:f3c55966658d336a3f51a76d0847f194f79ba13d9e140553e7fa9c308ec5f6ce`;
- direct URL `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_5/os-zapret2-restyle-0.4.1_5.pkg`;
- publication branch `publish/v0.4.1_5` was deleted by the successful workflow;
- publication performed no Pages or pkg-repository promotion;
- evidence: `docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md`.

Accepted `_6` testing-package identity and corrective live evidence:

- exact source/squash merge: `9a76551d17289fa6a125c10fabedf87241d1a490`;
- source tree: `36019521fb74c1736a9c6da822780133df639820`;
- latest-head packaged source CI run `31687601966` / #808 — SUCCESS;
- post-merge main CI run `31688215371` / #809 — SUCCESS;
- publication workflow run `31689302668` / #43 — SUCCESS;
- tag `v0.4.1_6` targets exact source commit `9a76551d17289fa6a125c10fabedf87241d1a490`;
- GitHub Release ID `369818027`, `draft=false`, `prerelease=true`;
- package asset ID `512818044`;
- package `os-zapret2-restyle-0.4.1_6.pkg`, `188907` bytes;
- package digest `sha256:e708d2ac0eb13d41d1d79da96e2b5f1f6e9d4fc9e138366fd4e72e30b96a02b7`;
- direct URL `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_6/os-zapret2-restyle-0.4.1_6.pkg`;
- publication branch `publish/v0.4.1_6` was deleted by the successful workflow;
- no GitHub Pages or pkg-repository promotion occurred;
- corrected owner-live Rutracker measurement concluded `measurement_accepted`;
- post-run IPFW range `19100-19131`, candidate process/socket `9989` were empty and normal Zapret2 was restored running;
- evidence: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`.

`_6` fixes only the `_5` measurement finalizer boolean boundary. The shell worker passes cleanup success/failure as `1`/`0`; `_5` decoded only literal `true`, making successful cleanup persist as false. `_6` accepts canonical numeric/text booleans, rejects unknown values, and regression-tests both accepted and rejected finalization paths. The corrected owner-live run now proves the successful path on the appliance. Production Model C and production GET-4K are unchanged.

==================================================
CURRENT AUTHORITIES
==================================================

Current GitHub delivery authorities:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/patches/v0.4.1_6.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-input.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-source-verification-plan.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`;
- `docs/patches/v0.4.1_5.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-cleanup-finalizer-root-cause.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-ci-package-artifact.md`;
- `docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md`;
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
V0.4.1_5 DISCOVERY PROBE AGREEMENT — OWNER-LIVE DATA COLLECTED / FINALIZER DEFECT CONFIRMED
==================================================

Policy: `discovery-probe-agreement-v1`, schema `1`.

The experiment measures adaptive-search question 10 without changing the production search path.
For each selected eligible native TLS 1.3 candidate it performs four cold replays in balanced
cyclic order: `HEAD`, `GET Range 0-0`, the current discovery `GET Range 0-4095`, and the existing
deep finalist GET reference requiring `16384` bytes when the resource is long enough.

The owner-live multidomain set covers Telegram zero-winner exhaustive, Rutracker two-winner exhaustive and YouTube three-winner early-stop Model-C execution, all without fallback. Rutracker Stage 60 completed in `24204 ms`; YouTube Stage 60 completed in `9151 ms`. Across the three ten-candidate discovery corpora every cheap probe recorded 29/29 agreement on comparable pairs, zero false PASS and zero false FAIL, plus one expected Rutracker deep-inconclusive short-resource pair.

Equal-sample pooled mean total time was approximately `3452.97 ms` for HEAD, `3442.37 ms` for GET-1 and `3439.70 ms` for current GET-4K. No material cheaper-probe advantage was demonstrated, so production GET-4K remains unchanged.

All three `_5` reports were formally rejected only because `checks.cleanup_ok=false`. Source inspection proved this was deterministic: the shell worker supplied numeric `1`/`0`, while the Python finalizer accepted only literal `true`. Root-cause evidence: `docs/verification/evidence/2026-08-13-v0.4.1_5-cleanup-finalizer-root-cause.md`.

Historical FreeBSD-15 build evidence from latest-head CI #785 remains bound to the exact merged-main tree by `docs/verification/evidence/2026-08-13-v0.4.1_5-ci-package-artifact.md`. Persistent GitHub testing package `v0.4.1_5` remains published from the exact source commit by workflow `31652568754`; the published asset is `os-zapret2-restyle-0.4.1_5.pkg`, `188854` bytes, `sha256:f3c55966658d336a3f51a76d0847f194f79ba13d9e140553e7fa9c308ec5f6ce`. Publication evidence: `docs/verification/evidence/2026-08-13-v0.4.1_5-discovery-probe-publication.md`.

`production_model_changed=false`, `production_discovery_policy_changed=false`, and
`production_change_recommended=false`.

Patch contract: `docs/patches/v0.4.1_5.md`.

==================================================
V0.4.1_6 DISCOVERY CLEANUP FINALIZER — ACCEPTED / OWNER-LIVE PASS
==================================================

`_6` fixes only the experiment cleanup boolean boundary. Numeric shell values `1`/`0` and textual `true`/`false` are decoded canonically; unknown values fail closed. Regression coverage proves successful cleanup can satisfy the finalizer and failed cleanup still rejects the measurement.

Patch contract: `docs/patches/v0.4.1_6.md`.
Preserved corrective input: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-input.md`.
Accepted publication/live evidence: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`.

The persistent `_6` package is published at tag `v0.4.1_6`. The corrected Rutracker measurement concluded `measurement_accepted`; immediate post-run checks showed no reserved IPFW rules, no candidate worker/listener on port `9989`, and normal Zapret2 restored running.

Production Stage 60 and discovery policy are unchanged. `_6` does not promote HEAD or GET-1 and does not modify Model C, Model B, Model A, source-port dispatch, the native search graph or candidate semantics.

==================================================
CURRENT BOUNDARY / NEXT WORK
==================================================

The Model-C Lua initialization, BLOB startup/RSS questions and discovery-probe agreement/cost question are closed by owner-live evidence without production changes. `_5` established the multidomain agreement/cost result; `_6` corrected the measurement finalizer and is now owner-live accepted.

No further discovery-probe corrective repeat is required unless a new regression appears. The current multidomain data did not demonstrate a material reproducible cost benefit for HEAD or GET-1 over GET-4K, so production discovery remains bounded GET-4K.

Detailed accepted production runtime behavior remains based on `_26`; `_2` through `_6` did not change production behavior.

Production behavior remains
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

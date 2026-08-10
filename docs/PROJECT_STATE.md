# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary,
blockers, active architectural direction, and next action.

Read after:
`AGENTS.md` and `docs/INDEX.md`.

Do not store here:
Full chronological history, detailed implementation design, or complete test logs.
Those belong in `docs/devlog/`, `docs/patches/`, and `docs/verification/evidence/`.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current published project release/package: `v0.4.0` / `os-zapret2-restyle-0.4.0_1.pkg`
Latest published testing prerelease: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`
Latest owner-tested testing candidate: `v0.4.0_16` / `os-zapret2-restyle-0.4.0_16.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=17`
Current source candidate: `os-zapret2-restyle-0.4.0_17.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Model B `_16` owner-live coexistence ACCEPT; `_17` failed-readiness fail-fast corrective qualified and published as testing prerelease; owner installation pending**
Current source overlay: **`_17` preserves the accepted `_16` ready-pool path and rejects immediately after `all_workers_ready=false`, before any route/probe/stop/death work, while retaining bounded cleanup/restoration**
Revision note: **`_15` remains intentionally unclaimed by this source line because a stale concurrent `_15` branch exists; no `_15` package/release or live result is recorded here**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**
Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**
Model B experiment gate: **`v0.4.0_16` OWNER-LIVE COEXISTENCE ACCEPT; EXPERIMENT ONLY; `production_approved=false`**

Current primary Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`;
- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Current GitHub delivery authority:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current live-gate authority:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Latest accepted live experiment evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`.

Accepted Model A reference evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Previous Model B reject evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Model B experiment contract:
`docs/patches/v0.4.0_12.md`.

Model B access corrective contract:
`docs/patches/v0.4.0_14.md`.

Current source corrective contract:
`docs/patches/v0.4.0_17.md`.

Current live-release-gate decision:
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

==================================================
MIGRATION OWNERSHIP
==================================================

The automated Strategy Lab Python migration is complete. Python is authoritative for:

- automated-job state/progress/event persistence;
- stage orchestration, budgets, cancellation and finalization;
- finite request/probe execution and parsing;
- candidate runtime/readiness/interception and Stage-50 screening;
- Stage-60 expansion, Stage-70 stability and Stage-80 extended orchestration;
- final profile construction, replay, shortlist and automated circular eligibility;
- active Diagnostics status/reload presentation state.

The shared lifecycle lock, audited FreeBSD system mutations, and private circular-session
state remain deliberate shell boundaries. Corrective/adaptive/experimental work must not
move those boundaries without a new architectural decision.

==================================================
ADAPTIVE SEARCH IMPLEMENTATION STATE
==================================================

Approved and implemented progression:

- `_28` / `0.4.0_2` — removed Stage-50 accepted-family hard gating;
- `_29` / `0.4.0_3` — canonical immutable `CandidateSpec` and job-scoped
  `ResourceInventory`;
- `_30` / `0.4.0_4` — native Zapret2 search DAG, golden corpus, semantic resource branches
  and candidate-defined ranges;
- `_31` / `0.4.0_5` — live-evidence adaptive ordering, fixed search epoch, two-to-three
  winner defaults and durable timing telemetry;
- `_32` / `0.4.0_6`–`0.4.0_8` — telemetry-driven timeout containment, owner-live passed on
  the observed Standard and Extended no-winner paths;
- `_33` / `0.4.0_9` — bounded lightweight discovery, fail-fast strict 3/3 stability and
  cold finalist depth validation, change-specific owner-live passed on winner and
  no-winner paths;
- `0.4.0_10` — read-only Model A cold-reference measurement summarizer plus candidate RSS
  collection at the FreeBSD snapshot boundary; first appliance report exposed a Python
  readiness propagation gap;
- `0.4.0_11` — preserved snapshot `rss_kb` in persisted Python readiness/candidate
  evidence and owner recheck collected the complete Model A cold reference;
- `0.4.0_12` — experiment-only Model B coexistence harness for three exact Model-A
  reference candidates on distinct warm `dvtws2` processes/divert ports with strictly
  sequential rule-selected probes, independent-stop/death checks and mandatory semantic
  restoration; first owner launch was blocked before worker startup by a false clean
  preflight status;
- `0.4.0_13` — corrected clean preflight and reached the worker/probe path on the owner
  appliance; all three workers disappeared before readiness, probes were diverted to the
  dedicated ports without qualifying listeners, and the experiment truthfully ended
  `reject` with complete semantic restoration;
- `0.4.0_14` — reused the previously owner-proven bounded post-drop hostlist access lease:
  active Model B session ancestors are `0711` while warm workers run and the retained root
  returns to private `0700` during cleanup;
- `0.4.0_16` — retained the `_14` access lease and normalized the Strategy Lab legacy `ax`
  all-process selector at the shared FreeBSD process-query boundary so native `ps` receives
  compatible `-xww -A ...` flags. The owner-live rerun then reached final
  `conclusion=accept` with all required Model B checks and restoration true;
- `0.4.0_17` — closes the separate failed-readiness control defect proven by `_13`: once
  the warm pool reports any non-ready worker, Model B records the failed slots and rejects
  before route/probe/independent-stop/controlled-death work. Existing cleanup and semantic
  restoration ownership remain unchanged. Canonical CI, FreeBSD 15 package inspection and
  testing-prerelease publication are complete.

Warm runtime selection remains evidence-gated by the A/B/C experiment plan. Model B is a
measurement harness only. No Model B/C worker, dispatcher, warm preload or parallel
candidate probing is production-approved.

==================================================
LATEST AUTOMATED SEARCH OWNER RESULT — `v0.4.0_9`
==================================================

Owner evidence contains three complete automated Strategy Lab jobs on
`os-zapret2-restyle-0.4.0_9`:

- Standard `telegram.org` `job.tU3wiL` — truthful `NO_CANDIDATE`, all 16 expansion nodes
  exhausted, mandatory restoration verified;
- Extended `telegram.org` `job.hsP8Ro` — truthful `NO_CANDIDATE`, Extended Stage 80 passed
  with unavailable/configured branches explicitly skipped, mandatory restoration verified;
- Standard `rutracker.org` `job.UPRDlc` — `SUCCESS`, Stage 60 stopped after six tested
  candidates when three working candidates were found, Stage 70 proved all three strict
  3/3, and Stage 85 executed one cold exact-profile replay per finalist.

The three finalist responses were successful HTTP 301 responses of 162 bytes, so the
16-KiB depth criterion was truthfully classified `inconclusive` rather than false PASS or
network FAIL. The separate 3/3 connectivity/stability evidence remained valid.

Post-run evidence showed the initially RUNNING Zapret2 service restored, strategy
unchanged, temporary runtime clean, and no reserved Strategy Lab IPFW rule residue. The
live set did not contain an unstable finalist, so fail-fast rejection remains automated
regression evidence rather than owner-live evidence.

Exact record:
`docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`.

==================================================
MODEL A — COLD REFERENCE COLLECTED ON `_11`
==================================================

Owner Standard `rutracker.org` job `job.TtZeaH` on `v0.4.0_11` completed `SUCCESS` and
produced 25 cold candidate samples. The read-only `model-a summarize` command returned
`conclusion=reference_collected` with every machine-checkable coverage item true.

The accepted report proves known PASS/FAIL candidates, repeated execution, required
`blob-free`/`builtin`/`external` resources, `-d8`/`-d10`, 16 unique overlapping TLS/443
specs, numeric candidate RSS on all samples and verified clean restoration.

Measured cold distributions across the 25 `_11` samples:

- total candidate median 1580 ms, p90 3411 ms, max 3463 ms;
- readiness median 1046 ms, p90 1052 ms, max 1138 ms;
- combined prepare median 140 ms, p90 160 ms, max 165 ms;
- launch median 17 ms, p90 20 ms, max 21 ms;
- probe median 220 ms, p90 2045 ms, max 2055 ms;
- stop + cleanup median 81 ms, p90 102 ms, max 109 ms;
- RSS minimum 4316 KiB, median 4332 KiB, p90 4348 KiB, maximum 4356 KiB.

Exact accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Previous `_10` gap evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_10-model-a-rss-gap.md`.

==================================================
MODEL B — OWNER-LIVE COEXISTENCE ACCEPT ON `_16`
==================================================

The Model B harness remains separate from normal Strategy Lab search and consumes retained
Model A job `job.TtZeaH`. The corpus remains exactly three compatible TLS 1.3/TCP/443
reference specs: repeated blob-free PASS, builtin FAIL, and external `-d8` FAIL.

Historical progression:

- `_12` was blocked before worker startup by a false clean-preflight status leak;
- `_13` fixed preflight but all three workers disappeared before readiness because the
  private Model B session ancestors prevented post-drop hostlist traversal;
- `_14` applied the bounded `0711` traversal lease already proven by normal Strategy Lab;
- `_16` retained that lease and fixed the FreeBSD `process_query.sh` legacy `ax` selector
  interface before repeating the same owner-live experiment.

The `_16` owner report is a real `accept`:

- `preliminary_accept=true`;
- `conclusion=accept`;
- all required checks are true;
- semantic restoration is verified;
- `experiment_only=true`;
- `parallel_probes=false`;
- `production_approved=false`.

Warm pool evidence:

- `pass`: PID 11486, divert 9990, RSS 4324 KiB, ready;
- `builtin`: PID 25203, divert 9991, RSS 4320 KiB, ready;
- `external`: PID 40825, divert 9992, RSS 4320 KiB, ready;
- aggregate pool RSS 12964 KiB;
- pool startup 1162 ms.

All A/B/C/A sequential probe classifications matched Model A. Selected IPFW rules moved,
inactive rules stayed absent, all workers remained ready during coexistence, repeated PASS
selection stayed PASS, independent stop preserved survivor correctness, and controlled
worker death left the remaining PASS worker healthy and equivalent to Model A.

Measured Model B medians were dispatch 12.0 ms and probe 200.5 ms. The accepted Model A
cold total-candidate median is 1580 ms. A narrow three-candidate amortization using only
metrics retained by both reports estimates about 600 ms/candidate for Model B versus
1580 ms/candidate cold, roughly 62% lower. This is promising measurement evidence, not a
production performance decision: the current report lacks a directly comparable full-run
wall-clock distribution and contains only one accepted owner-live Model B run.

Final restoration records RUNNING -> RUNNING, unchanged strategy/runtime arguments and
normal firewall, clean temporary runtime, and no dedicated Model B rule residue.

Exact accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`.

Previous `_13` reject evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

The owner-live `accept` closes the `_14` access and `_16` process-query live rerun gate. It
does **not** approve Model B for production Strategy Lab use.

`v0.4.0_17` leaves this accepted ready-pool path unchanged. It changes only the negative
boundary proven by `_13`: after readiness evidence is persisted, a non-ready pool now
records `failed_readiness.failed_slots`, marks `downstream_actions_skipped=true`, returns a
truthful experiment reject, requests common cleanup, and never reaches route/probe/stop/
controlled-death actions. Exact source contract: `docs/patches/v0.4.0_17.md`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed by the adaptive timeout/search and measurement series:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed 70-second parent timeout on `0.4.0_6` — closed by `_7` owner evidence.
3. Stage-70/80/85/90 normal-path containment — closed by `_8` owner evidence.
4. `_33` winner/no-winner adaptive validation boundary — closed change-specifically by
   `_9` owner evidence, with fail-fast rejection still source-regression-only.
5. `_10` Model A RSS propagation gap — source-corrected and owner-live closed by `_11`;
   Model A returns `reference_collected`.
6. `_12` Model B false clean-preflight failure — source-corrected by `_13` and owner-live
   closed when `_13` advanced into worker startup.
7. `_13` Model B post-drop hostlist traversal / `_16` process-query rerun boundary — closed
   by `_16` owner-live `conclusion=accept` with all worker readiness, identity, RSS,
   attribution, coexistence, stop/death and restoration checks true.

Current Model B control corrective:

8. `_13` proves that when `all_workers_ready=false` the harness continued into route/probe/
   stop/death work, causing avoidable timeouts and allowing downstream `kill-owned` failure
   to obscure the first readiness failure. `_17` source-corrects that exact branch with an
   immediate reject plus common cleanup; focused regression proves the downstream actions
   are skipped. CI/FreeBSD 15 qualification and testing-prerelease publication are complete;
   owner installation is pending.

Other product/regression observations remain separate backlog unless selected by the
risk-based live gate:

- issue #155: idle-state presentation/localization (`Status` / `ready`, `Статус` / `готов`)
  without changing the internal `state: idle` contract;
- immediate stale/new-job GUI error recheck;
- active GUI no-output message recheck;
- complete progress/reload presentation recheck;
- PARTIAL summary wording;
- dedicated STOPPED-state restoration row;
- cancellation, hard timeout and controlled internal failure rows;
- live extended TLS/HTTP, QUIC and configured generic UDP rows;
- circular/settings/retention/reboot regression rows.

See `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` for the canonical inventory.

==================================================
DELIVERY AND LIVE-GATE BOUNDARY
==================================================

The stable `v0.4.0 / 0.4.0_1` release cycle remains complete. The mandatory v0.4.0
post-migration live row remains PASS on `_27`, `_28` retains its focused adaptive owner
PASS, `_32` retains its timeout-containment owner PASS through `_8`, and `_33` retains its
change-specific owner-live PASS on `_9`.

`v0.4.0_11` remains the accepted Model A cold reference. `v0.4.0_17` is the latest
published testing prerelease. `v0.4.0_16` remains the latest owner-tested candidate and its
experiment-only Model B rerun returns `accept` with complete restoration. Current source
candidate is `_17`, limited to the failed-readiness control boundary. Model B still
explicitly records `production_approved=false`; no warm-worker production architecture is
approved. Revision `_15` remains unclaimed by this source line.

==================================================
NEXT ACTION
==================================================

1. Install `os-zapret2-restyle-0.4.0_17.pkg` on the owner OPNsense appliance and verify the
   installed package identity plus normal Zapret2 service state.
2. Preserve `_16` as the accepted ready-pool coexistence baseline. The direct `_17`
   change-specific gate is already covered by the focused negative-path regression proving
   no downstream probe/control action after failed readiness while cleanup/restoration
   remain intact; do not induce an unsafe worker failure solely to manufacture live proof.
3. Keep Model B experiment-only and sequential; do not add production warm reuse, Model C,
   source-port dispatch, preload-policy changes or true parallel candidate probing in this
   corrective.
4. Continue the measurement plan with repeated comparable wall-clock runs before any
   architecture-selection decision.

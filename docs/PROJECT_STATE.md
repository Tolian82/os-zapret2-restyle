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
Latest published testing prerelease: `v0.4.0_19` / `os-zapret2-restyle-0.4.0_19.pkg`
Latest owner-tested testing candidate: `v0.4.0_19` / `os-zapret2-restyle-0.4.0_19.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=20`
Current source candidate: `os-zapret2-restyle-0.4.0_20.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **`_19` sequential exhaustive Model B ACCEPT 5/5 on the complete `telegram.org` no-candidate corpus; `_20` controlled three-worker parallel candidate-probe experiment in source/CI**
Current source overlay: **`_20` preserves production Model A and the accepted `_19` sequential warm path; up to three already-isolated Model B candidates are probed concurrently with unique TCP source-port-qualified IPFW ownership while pinned endpoints inside each candidate remain sequential**
Revision note: **`_15` remains intentionally unclaimed by this source line because a stale concurrent `_15` branch exists; no `_15` package/release or live result is recorded here**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**
Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**
Model B experiment gate: **first owner-live coexistence ACCEPT on `v0.4.0_16`; repeated coexistence ACCEPT 5/5 on `v0.4.0_17`; sequential exhaustive ACCEPT 5/5 on `v0.4.0_19`; `_20` controlled parallel candidate probes selected; EXPERIMENT ONLY; `production_approved=false`**

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
`docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

Latest live exhaustive corrective evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

First accepted Model B coexistence evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`.

Accepted Model A reference evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Previous Model B reject evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Model B experiment contract:
`docs/patches/v0.4.0_12.md`.

Model B access corrective contract:
`docs/patches/v0.4.0_14.md`.

Current source experiment contract:
`docs/patches/v0.4.0_20.md`.

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
  testing-prerelease publication are complete. The owner installed `_17` and then repeated
  the unchanged ready-pool coexistence experiment five times; all five runs returned
  `conclusion=accept` with restoration verified;
- `0.4.0_18` — added the experiment-only exhaustive no-candidate benchmark and was
  published. Owner reference `job.tMYnFA` reached truthful Standard `NO_CANDIDATE`, 16/16
  Stage-60 `graph_exhausted`, `partial=false`, with verified restoration. The first
  exhaustive attempt then rejected before any warm batch because `_18` incorrectly
  required exactly one pinned endpoint while `telegram.org` has multiple required pinned
  endpoints;
- `0.4.0_19` — accepted all pinned reference endpoints and completed the exact retained
  16-candidate/two-endpoint `telegram.org` corpus. Five sequential exhaustive runs all
  returned `conclusion=accept` with restoration verified. Warm exhaustive wall time was
  74.600–75.083 s (mean 74.8082 s) versus 89.012 s cold Stage-60 candidate runtime, for a
  mean measured candidate-runtime speedup of about 15.96%. Peak three-worker RSS stayed
  around 12.98 MiB. The projected full-job improvement remains a projection, not a measured
  Model B full Strategy Lab run;
- `0.4.0_20` — current experiment-only source candidate: reuse the same three isolated warm
  workers but execute up to three candidate probes concurrently. Each candidate/endpoint
  probe owns a unique controlled TCP source port and an exact source-port-qualified IPFW
  rule, while endpoints within one candidate remain sequential. Logical CPU count is
  recorded as measurement metadata only; it does not gate width or architecture.

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

The no-winner/winner timing distinction is material for the active benchmark. Standard
`telegram.org` checked all 16 Stage-60 candidates with `stopped_reason=graph_exhausted`,
Stage 60 about 89.247 s and total through mandatory restoration about 144.125 s. Extended
`telegram.org` took about 169.262 s. Standard `rutracker.org` stopped after six Stage-60
candidates and completed in about 71.023 s. Maximum search timing must therefore use a
no-candidate graph-exhausted target rather than a successful early-stop target.

The three finalist responses on the winner run were successful HTTP 301 responses of 162
bytes, so the 16-KiB depth criterion was truthfully classified `inconclusive` rather than
false PASS or network FAIL. The separate 3/3 connectivity/stability evidence remained
valid.

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
MODEL B — OWNER-LIVE COEXISTENCE ACCEPT AND `_17` REPRODUCIBILITY
==================================================

The Model B harness remains separate from normal Strategy Lab search and consumes retained
Model A job `job.TtZeaH`. The initial coexistence corpus remains exactly three compatible
TLS 1.3/TCP/443 reference specs: repeated blob-free PASS, builtin FAIL, and external `-d8`
FAIL.

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

Measured `_16` Model B medians were dispatch 12.0 ms and probe 200.5 ms. The accepted
Model A cold total-candidate median is 1580 ms. A narrow three-candidate amortization using
only metrics retained by both reports estimates about 600 ms/candidate for Model B versus
1580 ms/candidate cold, roughly 62% lower.

The owner-installed `_17` repeated set strengthens reproducibility without changing the
architecture claim: five sequential runs all returned `accept` with restoration verified.
External harness wall time ranged 14.90–15.03 s; mean pool startup was 1163.6 ms, mean
dispatch median 12.4 ms and mean probe median 200.3 ms. The already-warm mean
dispatch+probe path of about 212.7 ms is roughly 86.5% below the 1580 ms cold-candidate
median, while startup-amortized three-candidate cost is about 600.6 ms/candidate, roughly
62.0% lower. Neither percentage is a full-search result.

After the five `_17` runs the normal Zapret2 service was running and dedicated Model B
rules `19128–19130` were absent.

Exact evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

Previous `_13` reject evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Model B remains experiment-only and does **not** have production approval.

==================================================
MODEL B EXHAUSTIVE NO-CANDIDATE BENCHMARK — `_18` / `_19`
==================================================

The exhaustive benchmark requires a completed fresh Standard domain reference with
`outcome=NO_CANDIDATE`, Stage-60 `stopped_reason=graph_exhausted`, zero working Stage-60
candidates, complete persisted `candidates`/`schedule`, verified restoration and the same
current `ResourceInventory`.

The owner created complete `_18` reference `job.tMYnFA` on `telegram.org` with a
measurement-only 210-second Standard budget override. The job completed all 16 Stage-60
candidates with `graph_exhausted`, `partial=false`, and verified RUNNING -> RUNNING
restoration. This is the selected cold exhaustive reference.

The first `_18` warm exhaustive attempt did not reach any batch. The report returned
`error="exhaustive Model B requires one pinned endpoint"`, `reference=null`, no timing or
comparison payload, `preliminary_accept=false` and final `conclusion=reject`. Cleanup and
semantic restoration were nevertheless fully verified. This result identifies only a
harness input-contract gap: the real `telegram.org` epoch contains multiple required
pinned endpoints while `_18`'s synthetic regression covered one.

`_19` corrected that boundary. The exact persisted Stage-60 candidate corpus/order remained
batched at at most three warm workers. Every target-bound worker received all pinned
endpoint names in its hostlist. For every candidate, every pinned endpoint was probed
sequentially against its own fixed selected IP. Candidate PASS required all endpoint probes
to pass; every no-candidate replay remained non-PASS. Endpoint-level route/interception
evidence, worker identity/readiness, numeric RSS, exact corpus order, cleanup between
batches and semantic restoration all passed.

The owner repeated the corrected `_19` exhaustive run five times on `job.tMYnFA`. All five
returned `conclusion=accept` with restoration verified. Warm exhaustive search times were
74886, 74692, 75083, 74780 and 74600 ms: mean 74808.2 ms, median 74780 ms and only 483 ms
min/max spread. Mean measured Stage-60 candidate-runtime speedup versus the retained
89012 ms cold corpus was about 15.96%. Peak aggregate three-worker RSS stayed between
12976 and 12992 KiB. The report's full-job value remains explicitly projected rather than
a measured Model B full Strategy Lab run.

Exact contracts/evidence:

- `docs/patches/v0.4.0_18.md`;
- `docs/patches/v0.4.0_19.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_18-model-b-exhaustive-multi-endpoint-gap.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

The next selected experiment is `_20` controlled parallel candidate probing. Production
Strategy Lab remains Model A until a separate architecture decision is justified.

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
8. `_13` failed-readiness continuation — source-corrected by `_17` with immediate reject
   plus common cleanup. Owner installation is complete and five ready-pool repeats all
   accept, confirming no regression of the accepted coexistence path; the intentionally
   broken negative path remains regression evidence only.
9. `_18` single-endpoint exhaustive input assumption — corrected by `_19`; five owner-live
   full-corpus sequential exhaustive runs all accept with stable timing and restoration.

Current measurement gap:

10. `_20` controlled parallel candidate probing is not yet owner-live measured. It must
    prove simultaneous candidate overlap, exact source-port-qualified route attribution,
    unchanged no-candidate results, worker health, bounded width, cleanup and semantic
    restoration before any performance conclusion. CPU count is measurement metadata, not
    an acceptance gate.

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
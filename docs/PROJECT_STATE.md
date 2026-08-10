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
Latest published testing prerelease: `v0.4.0_13` / `os-zapret2-restyle-0.4.0_13.pkg`
Latest owner-tested testing candidate: `v0.4.0_13` / `os-zapret2-restyle-0.4.0_13.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=16`
Current source candidate: `os-zapret2-restyle-0.4.0_16.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Model B `_13` reached worker startup and rejected with no resident workers; `_14` post-drop hostlist traversal corrective pending CI/publication/live rerun**
Current source overlay: **`_16` fixes the FreeBSD `process_query.sh`/legacy `ax` selector interface before that same Model B live rerun**
Revision note: **`_15` is intentionally not claimed by this source line because a concurrent `_15` branch already exists; no `_15` package or live result is recorded here**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**
Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**
Model B experiment gate: **`v0.4.0_13` OWNER-LIVE REJECT AT WORKER STARTUP; `v0.4.0_14` ACCESS CORRECTIVE PENDING LIVE**

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
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Latest Model B live evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Model B experiment contract:
`docs/patches/v0.4.0_12.md`.

Current Model B access corrective contract:
`docs/patches/v0.4.0_14.md`.

Current source corrective contract:
`docs/patches/v0.4.0_16.md`.

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
- `0.4.0_14` — reuses the previously owner-proven bounded post-drop hostlist access lease:
  active Model B session ancestors are `0711` while warm workers run and the retained root
  returns to private `0700` during cleanup;
- `0.4.0_16` — normalizes the Strategy Lab legacy `ax` all-process selector at the shared
  FreeBSD process-query boundary so native `ps` receives compatible `-xww -A ...` flags;
  non-FreeBSD process queries remain transparent. Revision `15` is intentionally skipped
  by this source line and is not claimed as a package or live result here.

Warm runtime selection remains evidence-gated by the A/B/C experiment plan. Model B is a
measurement harness only. No Model B/C worker, dispatcher, warm preload or parallel
candidate probing is production-approved.

==================================================
LATEST OWNER LIVE RESULT — `v0.4.0_9`
==================================================

Owner evidence contains three complete jobs on `os-zapret2-restyle-0.4.0_9`:

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
MODEL B — `_13` WORKER-STARTUP REJECT / `_14` ACCESS CORRECTIVE
==================================================

The Model B harness remains separate from normal Strategy Lab search and consumes retained
Model A job `job.TtZeaH`. The corpus remains exactly three compatible TLS 1.3/TCP/443
reference specs: repeated blob-free PASS, builtin FAIL, and external `-d8` FAIL.

`v0.4.0_13` proved that the `_12` clean-preflight bug is closed. The owner run advanced
past preflight and created the full Model B report. It also exposed the next FreeBSD worker
startup blocker:

- all three pool snapshots: `pid=null`, `process_identity=false`, `socket_ready=false`,
  `rss_kb=null`;
- `all_workers_ready=false` and `unique_worker_identity=false`;
- selected IPFW rule counters moved for every attempted probe;
- all curls timed out with no remote endpoint because no qualifying worker remained on the
  selected divert port;
- the known-pass slot therefore classified `fail`;
- later controlled-death handling produced `Model B system adapter kill-owned failed`
  because there was no owned external-worker PID;
- final semantic restoration remained fully verified: RUNNING -> RUNNING, normal firewall
  unchanged, strategy/runtime arguments unchanged, temporary runtime clean.

The deterministic source condition matches the previously owner-proven normal Strategy Lab
`v0.3.3_16` hostlist failure: dvtws2 loads a hostlist, drops to `nobody`, then checks/reopens
that hostlist. `_13` made the Model B root and session directory `0700`, so a mode-0644
hostlist nested below them cannot be traversed after the privilege drop.

`v0.4.0_14` grants only search permission (`0711`) to those two active session ancestors
while the lifecycle-owned experiment runs. The tree remains non-listable. Cleanup restores
the retained Model B root to private `0700` before deleting the per-run session. This is the
same bounded access pattern already accepted for normal Strategy Lab candidate runtime.

Before that access correction can be rechecked live, `v0.4.0_16` also closes a separate
FreeBSD process-query interface defect found in the same Model B investigation: production
routes `STRATEGY_LAB_PS_BIN` through `process_query.sh`, while full-process scans pass the
legacy selector `ax`. The adapter now normalizes only that leading selector to `-A`, so
FreeBSD native `ps` receives the compatible `-xww -A ...` form.

Exact `_13` evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Even a future live `conclusion=accept` means only that the coexistence experiment passed.
The report retains `experiment_only=true`, `parallel_probes=false`, and
`production_approved=false`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed by the adaptive timeout/search series:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed 70-second parent timeout on `0.4.0_6` — closed by `_7` owner evidence.
3. Stage-70/80/85/90 normal-path containment — closed by `_8` owner evidence.
4. `_33` winner/no-winner adaptive validation boundary — closed change-specifically by
   `_9` owner evidence, with fail-fast rejection still source-regression-only.
5. `_10` Model A RSS propagation gap — source-corrected and owner-live closed by `_11`;
   Model A now returns `reference_collected`.
6. `_12` Model B false clean-preflight failure — source-corrected by `_13` and owner-live
   closed when `_13` advanced into worker startup.

Current experiment blocker:

7. `_13` Model B post-drop hostlist traversal failure — owner evidence shows no resident
   workers/readiness; source-corrected by `_14`; `_16` additionally closes the FreeBSD
   process-query selector incompatibility found before the same live rerun; live rerun pending.

Separate confirmed Model B control defect:

8. `_13` continues route/probe/stop/death work after `all_workers_ready=false`, causing
   avoidable timeouts and allowing downstream `kill-owned` to obscure the first readiness
   failure. Keep this as a separate logical corrective before any production approval.

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

`v0.4.0_11` remains the accepted Model A cold reference. `v0.4.0_13` is the latest
published and owner-tested testing prerelease. Its Model B run is a real `reject` at worker
startup, not a preflight block, and restoration passed. `v0.4.0_16` is the current source
candidate: it retains the `_14` bounded post-drop access corrective and adds the narrow
FreeBSD process-query selector normalization. None of `_12`–`_16` is a production
warm-worker architecture; `_15` is intentionally not claimed by this source line.

==================================================
NEXT ACTION
==================================================

1. Qualify `os-zapret2-restyle-0.4.0_16.pkg` through the focused FreeBSD process-query and
   Model B regressions, canonical CI and FreeBSD 15 package inspection.
2. After testing-prerelease publication, install `_16` on the owner appliance while
   retaining `job.TtZeaH`.
3. Repeat the same experiment-only launcher against `job.TtZeaH` and preserve its JSON
   report.
4. Verify that all three workers now have unique PIDs, listening divert ports and numeric
   RSS before interpreting any A/B/C/A result.
5. Keep the separately confirmed failed-readiness fail-fast defect out of `_16`; correct it
   in its own logical cycle before any production Model B decision.
6. Keep Model C, source-port dispatch, preload-policy changes and true parallel candidate
   probing out of scope.
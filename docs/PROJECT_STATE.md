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
Latest published testing prerelease: `v0.4.0_12` / `os-zapret2-restyle-0.4.0_12.pkg`
Latest owner-tested testing candidate: `v0.4.0_12` / `os-zapret2-restyle-0.4.0_12.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=13`
Current source candidate: `os-zapret2-restyle-0.4.0_13.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Model B `_12` owner-live preflight defect identified; `_13` corrective source candidate pending CI/publication/live rerun**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**
Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**
Model B experiment gate: **`v0.4.0_12` OWNER-LIVE BLOCKED BEFORE WORKER LAUNCH; `v0.4.0_13` CORRECTIVE PENDING LIVE**

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

Model B experiment contract:
`docs/patches/v0.4.0_12.md`.

Current Model B corrective contract:
`docs/patches/v0.4.0_13.md`.

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
- `0.4.0_13` — corrective clean-preflight return contract: a fully free dedicated
  rule/port set now returns success while actual occupied rule/port and prerequisite
  failures remain rejection paths; focused real-shell regression added.

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
MODEL B — `_12` EXPERIMENT / `_13` PREFLIGHT CORRECTIVE
==================================================

`v0.4.0_12` does not alter normal Strategy Lab search. It adds an explicit laboratory
entry point that acquires the same Zapret2 lifecycle lock and consumes the retained Model A
reference job.

The first coexistence corpus is exactly three compatible TLS 1.3/TCP/443 reference specs:

- repeated known PASS / `blob-free`;
- known FAIL / `builtin`;
- known FAIL / `external` with `-d8`.

They are designed to run on dedicated warm ports `9990–9992` and dedicated temporary
rules `19128–19130`. Only the selected worker's rule is present for each probe; the other
warm workers remain alive but unrouted. The sequence is strictly sequential and includes
A/B/C/A repetition, independent stop of one worker and controlled death/cleanup of a
second worker.

Source/live acceptance requires exact Model-A classification equivalence, selected-rule
counter movement, inactive-rule absence, unique PID/divert identity, numeric
per-worker/aggregate RSS, survivor correctness after stop/death, dedicated residue cleanup,
and final semantic restoration of service state/config/runtime arguments/normal firewall.

The first `_12` owner invocation did not execute that experiment. Appliance diagnostics
showed `ipfw` and `ipdivert` loaded, `net.inet.ip.fw.enable=1`, executable `dvtws2` and
`daemon(8)`, absent rules `19128–19130`, and no listeners/divert sockets on ports
`9990–9992`. A direct `sh -x` adapter trace showed all checks passing and then
`preflight()` returning status 1 after the final free-port check.

Root cause: `port_in_use` intentionally returns status 1 for a free port. The final
`port_in_use "9992" && return 1` list therefore had status 1, and because `preflight()` had
no explicit successful return after the loop, POSIX shell propagated that expected
negative-predicate status as the whole function result.

`v0.4.0_13` adds an explicit `return 0` after all dedicated rule/port checks complete
without conflict and adds a real-shell regression proving clean success plus occupied-rule
and occupied-port rejection. No worker topology, routing, classification, timeout,
restoration or production approval behavior changes.

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

Current experiment blocker:

6. `_12` Model B clean preflight false failure — root cause localized by owner `sh -x`
   trace; source-corrected by `_13`; live rerun pending.

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

`v0.4.0_11` remains the accepted Model A cold reference. `v0.4.0_12` is the latest
published and owner-tested testing prerelease, but its Model B experiment did not pass or
reject: it was blocked before worker launch by the clean-preflight source defect.
`v0.4.0_13` is the current corrective source candidate. Neither `_12` nor `_13` is a
production warm-worker architecture.

==================================================
NEXT ACTION
==================================================

1. Qualify `os-zapret2-restyle-0.4.0_13.pkg` through focused regressions, canonical CI and
   FreeBSD 15 package inspection.
2. After testing-prerelease publication, install `_13` on the owner appliance while
   retaining `job.TtZeaH`.
3. Repeat the same experiment-only launcher against `job.TtZeaH` and preserve its JSON
   report.
4. Accept Model B coexistence only if result equivalence, traffic attribution, worker
   identity/RSS, independent stop, controlled death cleanup and semantic restoration all
   pass on the appliance.
5. If accepted, update the adaptive-search decision before considering any production
   warm-worker use. If rejected, keep Model A cold execution authoritative.
6. Keep Model C, source-port dispatch, preload-policy changes and true parallel candidate
   probing out of scope.

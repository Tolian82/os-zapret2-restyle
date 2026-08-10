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
Latest published testing prerelease: `v0.4.0_9` / `os-zapret2-restyle-0.4.0_9.pkg`
Latest owner-tested testing candidate: `v0.4.0_9` / `os-zapret2-restyle-0.4.0_9.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=10`
Current source candidate: `os-zapret2-restyle-0.4.0_10.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **post-`_33` Model A cold-reference measurement experiment**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**

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

Latest change-specific live evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`.

Current Model A patch/source contract:
`docs/patches/v0.4.0_10.md`.

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
- `0.4.0_10` — current post-`_33` experiment slice: read-only Model A cold-reference
  measurement summarizer plus candidate readiness RSS evidence.

Warm runtime selection remains evidence-gated by the A/B/C experiment plan. No Model B/C
worker, dispatcher, warm preload or parallel candidate probing is production-approved.

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
MODEL A — CURRENT `0.4.0_10` SLICE
==================================================

The next approved step is measurement before warm-runtime architecture selection.
`v0.4.0_10` has one logical purpose: turn retained cold candidate evidence into a
reproducible Model A baseline.

Current source contract:

- packaged command:
  `model-a summarize OUTPUT JOB_ID [JOB_ID ...]`;
- read-only operation over retained completed Strategy Lab jobs;
- no lifecycle lock acquisition, candidate launch, service stop/start, job mutation or
  evidence deletion;
- samples come from Stage 50, Stage 60, Stage 70 attempt files and Stage 85 cold deep
  replay files;
- report retains immutable candidate/spec identity, endpoint/interception identity,
  resource class/range, search epoch and resource inventory identity;
- per-phase and per-candidate distributions record count, median, nearest-rank p90 and max;
- readiness snapshots add `rss_kb` using the already validated candidate PID;
- machine-checkable experiment coverage includes observed PASS/FAIL, repeated candidate,
  required resource classes, `-d8`, overlapping TLS/443 specs, RSS and verified clean
  restoration for all input jobs;
- missing coverage yields `inconclusive`; only complete currently observable coverage
  yields `reference_collected`;
- current `cleanup_ms` is named `stop_cleanup_ms` because stop and remaining cleanup are
  not yet independently measured;
- `resource_init_ms` remains null where initialization is included in launch/readiness;
- no warm-runtime mechanism is enabled by this patch.

Focused regression:
`scripts/test-strategy-lab-model-a-measurement.sh`.

Implementation/devlog:
`docs/devlog/2026-08-10-v0.4.0_10-model-a-measurement.md`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed by the adaptive timeout/search series:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed 70-second parent timeout on `0.4.0_6` — closed by `_7` owner evidence.
3. Stage-70/80/85/90 normal-path containment — closed by `_8` owner evidence.
4. `_33` winner/no-winner adaptive validation boundary — closed change-specifically by
   `_9` owner evidence, with fail-fast rejection still source-regression-only.

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
PASS, `_32` retains its timeout-containment owner PASS through `_8`, and `_33` now has its
change-specific owner-live PASS on `_9`.

`v0.4.0_9` is the latest published and owner-tested testing prerelease. `v0.4.0_10` is the
current Model A measurement source candidate. Source/CI/FreeBSD qualification must
complete before merge/publication. Owner authorization covers the resulting installable
testing prerelease for this cycle; no Pages/pkg-repository promotion is implied.

==================================================
NEXT ACTION
==================================================

1. Complete latest-head CI and FreeBSD 15 package qualification for `v0.4.0_10`.
2. Squash merge the verified Model A PR with the exact candidate prefix.
3. Publish the authorized `v0.4.0_10` testing prerelease with exactly one FreeBSD 15
   `.pkg`.
4. On OPNsense, collect several comparable normal Strategy Lab jobs under the same target
   and runtime conditions, then run `model-a summarize` over those job IDs.
5. Preserve the first appliance Model A report under `docs/verification/evidence/` and use
   its measured coverage/tails to decide whether finer cold instrumentation is required or
   whether the project can proceed to the Model B coexistence experiment.
6. Keep Model B/C, source-port dispatch and true parallel probing experimental until their
   explicit equivalence/safety gates are satisfied.
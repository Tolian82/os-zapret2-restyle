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
Latest published testing prerelease: `v0.4.0_8` / `os-zapret2-restyle-0.4.0_8.pkg`
Latest owner-tested testing candidate: `v0.4.0_8` / `os-zapret2-restyle-0.4.0_8.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=9`
Current source candidate: `os-zapret2-restyle-0.4.0_9.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **adaptive-search `_33` discovery/stability/finalist validation source slice**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**

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
`docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md`.

Current `_33` patch/source contract:
`docs/patches/v0.4.0_9.md`.

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
state remain deliberate shell boundaries. Corrective/adaptive work must not move those
boundaries without a new architectural decision.

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
- `_32` / `0.4.0_6`–`0.4.0_8` — telemetry-driven timeout containment, now owner-live
  passed on the observed Standard and Extended no-winner paths;
- `_33` / `0.4.0_9` — current source slice: bounded lightweight discovery, fail-fast 3/3
  stability and cold finalist depth validation.

Warm runtime selection remains evidence-gated by the A/B/C experiment plan and is not
silently promoted by `_33`.

==================================================
LATEST OWNER LIVE RESULT — `v0.4.0_8`
==================================================

The owner tested `telegram.org` in both Standard and Extended modes on
`os-zapret2-restyle-0.4.0_8.pkg`.

Standard job `job.FgjRCR`:

- Stages 00–70 PASS;
- Stage 60 checked all 16 graph candidates and found no winner;
- Stage 80 correctly SKIPPED in Standard mode;
- Stage 85 PASS with an empty shortlist;
- Stage 90 PASS with the UI reporting temporary process/rule cleanup and healthy
  restoration of the initially running Zapret2 service;
- Stage 99 ended truthfully as `NO_CANDIDATE`.

Extended job `job.pv2Q09`:

- Stages 00–80 PASS;
- Stage 60 checked all 16 graph candidates and found no winner;
- Stage 80 reported `QUIC=skipped`, `UDP=skipped` for the observed capability/input state;
- Stage 85 PASS with an empty shortlist;
- Stage 90 PASS with successful restoration;
- Stage 99 ended truthfully as `NO_CANDIDATE`.

This closes the change-specific `_32` late-stage timeout-containment live boundary. The
screenshots do not provide precise stage timings, so no new timing values are claimed.
Exact preserved evidence is in
`docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md`.

==================================================
ADAPTIVE `_33` — CURRENT `_9` SLICE
==================================================

`v0.4.0_9` has one logical purpose: separate mass-discovery evidence from finalist depth
validation while avoiding redundant work after stability failure.

Current source contract on the `_9` branch:

- Stage-50/60 discovery and Stage-80 candidate discovery use a bounded 4-KiB GET while
  retaining the previous three-second network deadline;
- Stage 70 remains strict fresh-connection 3/3, but one failure rejects the candidate
  immediately and records remaining repetitions as unnecessary;
- Stage 85 evaluates at most the normal publication limit of three finalists;
- each finalist receives one cold exact-profile replay after the independent Stage-70
  stability gate;
- HTTP/TLS finalist depth targets 16 KiB, with a 64-KiB bounded request range;
- successful responses shorter than 16 KiB are `inconclusive` for byte depth and do not
  erase separate 3/3 connectivity/stability evidence;
- network/protocol/interception/HTTP failures are `fail`;
- finalist work is admitted only when execution + termination + cleanup + guard fits the
  Stage-85 parent deadline;
- proactive finalist budget exhaustion preserves timeout status 124 through the stage
  adapter;
- Standard/Extended total budgets remain 150/270 seconds;
- no warm runtime, parallel probing, graph expansion or QUIC-search redesign is included.

Focused regression:
`scripts/test-strategy-lab-adaptive-validation.sh`.

Implementation/devlog:
`docs/devlog/2026-08-10-v0.4.0_9-adaptive-validation.md`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed by the adaptive timeout series:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed 70-second parent timeout on `0.4.0_6` — closed by `_7` owner evidence.
3. Stage-70/80/85/90 normal-path containment — closed by `_8` owner evidence.

Other product/regression observations remain separate backlog unless selected by the
risk-based live gate:

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
post-migration live row remains PASS on `_27`, and `_28` retains its focused adaptive
owner-live PASS. Later testing candidates are forward corrective/adaptive work, not a
retroactive invalidation of the stable-release evidence.

`v0.4.0_8` is the latest published and owner-tested testing prerelease and closes the
observed `_32` timeout-containment path. `v0.4.0_9` is the current `_33` source candidate.
Source/CI/FreeBSD qualification must complete before merge/publication. The owner has
already authorized the resulting installable testing prerelease. Owner-live testing remains
required after publication, especially a target that yields at least one working candidate
so fail-fast and deep-finalist evidence can be observed live rather than only in source
regression.

==================================================
NEXT ACTION
==================================================

1. Complete latest-head CI and FreeBSD 15 package qualification for `v0.4.0_9`.
2. Squash merge the verified `_9` PR with the exact candidate prefix.
3. Publish the authorized `v0.4.0_9` testing prerelease with exactly one FreeBSD 15 `.pkg`.
4. Owner retests the blocked target in Standard and Extended modes; if no winner exists,
   preserve the no-winner regression and additionally test a target/provider condition
   that yields a working candidate so Stage-70 fail-fast and Stage-85 depth evidence can
   be inspected live.
5. Keep warm-runtime A/B/C experiments separate until their explicit equivalence/safety
   gates are executed.

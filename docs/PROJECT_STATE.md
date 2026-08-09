# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary,
blockers, active architectural direction, and next action.

Updated when:
Current source/package identity, live boundary, blocker, approved implementation direction,
or next action changes.

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
Latest published testing prerelease: `v0.4.0_7` / `os-zapret2-restyle-0.4.0_7.pkg`
Latest owner-tested testing candidate: `v0.4.0_7` / `os-zapret2-restyle-0.4.0_7.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=8`
Current source candidate: `os-zapret2-restyle-0.4.0_8.pkg` (implementation candidate; source qualification in progress on PR)
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **adaptive-search `_32` final late-stage timeout-containment source slice; `_33` remains next**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**

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

Current live evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`.

Current `_8` patch/source contract:
`docs/patches/v0.4.0_8.md`.

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
state remain deliberate shell boundaries. Corrective work must not move those boundaries
without a new architectural decision.

==================================================
ADAPTIVE SEARCH IMPLEMENTATION STATE
==================================================

The approved post-migration sequence is now:

- `_28` / `0.4.0_2` — removed Stage-50 accepted-family hard gating; focused owner-live PASS;
- `_29` / `0.4.0_3` — canonical immutable `CandidateSpec` and job-scoped `ResourceInventory`;
- `_30` / `0.4.0_4` — native Zapret2 search DAG, golden corpus, semantic resource branches,
  candidate-owned ranges;
- `_31` / `0.4.0_5` — live-evidence adaptive ordering, fixed search epoch, two-to-three
  winner defaults and durable timing telemetry;
- `_32` / `0.4.0_6`–`0.4.0_8` — telemetry-driven timeout containment;
- `_33` — lightweight discovery, fail-fast 3/3 stability and finalist deep validation.

Warm-runtime selection remains evidence-gated by the A/B/C experiment plan and is not
silently promoted by `_32` or `_33`.

==================================================
LATEST OWNER LIVE RESULT — `v0.4.0_7`
==================================================

The owner tested `telegram.org` in both Standard and Extended modes on
`os-zapret2-restyle-0.4.0_7.pkg`.

Standard job `job.RFVs75`:

- Stage 50 PASS;
- Stage 60 PASS, all 16 expansion candidates completed in about 90.243 seconds;
- Stage 70 PASS with zero stability candidates because expansion found no winner;
- Stage 80 correctly SKIPPED in Standard mode;
- Stage 85 PASS;
- Stage 90 PASS;
- terminal outcome `NO_CANDIDATE`;
- total time through mandatory restoration about 145.181 seconds.

Extended job `job.QbUuYO`:

- Stage 50 PASS;
- Stage 60 PASS, all 16 expansion candidates completed in about 89.249 seconds;
- Stage 70 PASS with zero stability candidates;
- Stage 80 PASS; QUIC and generic UDP were explicitly skipped by capability/input state;
- Stage 85 PASS;
- Stage 90 PASS;
- terminal outcome `NO_CANDIDATE`;
- total time through mandatory restoration about 169.427 seconds.

Post-run evidence showed the normal Zapret2 service running and only normal IPFW rule
`19000`; no reserved Strategy Lab rule `19100–19131` remained.

This closes the observed `_6` Stage-60 70-second parent timeout. Exact evidence is in
`docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`.

==================================================
CORRECTIVE `_32` — CURRENT `_8` SLICE
==================================================

The `_7` jobs exposed the remaining timeout-containment asymmetry:

- Stage 70 may begin stability attempts with very little Standard-search budget remaining;
- Stage-80 TCP/QUIC/UDP candidate loops had a shared stage envelope but no per-candidate
  admission check;
- Stage 85 had no explicit Python parent operation timeout;
- mandatory Stage 90 restoration had bounded shell lifecycle operations but no Python
  parent timeout.

`v0.4.0_8` therefore has one logical purpose: finish `_32` late-stage containment.

Current source behavior on the `_8` branch:

- Stage 70 checks the full cold candidate execution + termination + cleanup + guard
  envelope before every stability attempt;
- insufficient Stage-70 budget rejects the next attempt before launch and persists
  structured partial stability evidence;
- Stage-80 TCP/QUIC/configured-UDP candidate entry uses the same pre-launch admission rule;
- Stage 85 receives an explicit parent bound capped by the remaining overall search budget;
- Stage 90 receives a separate 180-second Python parent bound outside exhausted search
  budget, large enough to contain the existing internally bounded lifecycle transaction;
- the 150-second Standard and 270-second Extended total search budgets remain unchanged;
- `_33` discovery/stability/deep-validation semantics are not pulled into `_8`.

Focused regression:
`scripts/test-strategy-lab-late-stage-containment.sh`.

Implementation/devlog:
`docs/devlog/2026-08-10-v0.4.0_8-late-stage-containment.md`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed or directly addressed by the adaptive timeout series:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed 70-second parent timeout on `0.4.0_6` — closed by `_7` owner evidence.
3. Remaining Stage-70/80/85/90 containment — `_8` source correction; owner-live pending.

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

The stable `v0.4.0 / 0.4.0_1` release cycle is complete. The mandatory v0.4.0
post-migration live row remains PASS on `_27`, and `_28` retains its focused adaptive
owner-live PASS. Later testing candidates are forward corrective/adaptive work, not a
retroactive invalidation of the stable-release evidence.

`v0.4.0_7` is the latest published and owner-tested testing prerelease. It closes the
observed Stage-60 timeout and supplies the timing evidence selecting `_8`.

`v0.4.0_8` is the current source candidate. Source/CI/FreeBSD qualification must complete
before merge/publication. The owner has already authorized the resulting installable
testing prerelease. Owner-live Standard and Extended retesting remains required before
`_32` can be marked live-complete.

==================================================
NEXT ACTION
==================================================

1. Complete latest-head CI and FreeBSD 15 package qualification for `v0.4.0_8`.
2. Squash merge the verified `_8` PR with the exact candidate prefix.
3. Publish the authorized `v0.4.0_8` testing prerelease with exactly one FreeBSD 15 `.pkg`.
4. Owner retests `telegram.org` in Standard and Extended modes and preserves terminal
   status/timing/restoration evidence.
5. If `_8` live acceptance passes, close `_32` and begin `_33` discovery/stability/finalist
   validation as a separate logical cycle.

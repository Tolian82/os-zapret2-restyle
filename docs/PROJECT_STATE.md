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

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_25` / `os-zapret2-restyle-0.3.3_25.pkg`
Latest owner-tested testing candidate: `v0.3.3_25` / `os-zapret2-restyle-0.3.3_25.pkg`
Current source line: `VERSION=0.3.3`
Current package revision: `PLUGIN_REVISION=26`
Current corrective source candidate: `os-zapret2-restyle-0.3.3_26.pkg`
Current migration source candidate: `os-zapret2-restyle-0.3.3_26.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab post-migration live correction — Stage-50 candidate isolation**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Current GitHub delivery authority:
`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and the other active dated
GitHub decisions referenced by the publication authority.

Current live-gate authority:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Current live evidence:
`docs/verification/evidence/2026-08-08-v0.3.3_25-scenario-01-stage50-candidate-isolation.md`.

==================================================
MIGRATION OWNERSHIP
==================================================

The automated Strategy Lab migration is complete through Patch 8:

- Patch 1 (`_18`) — FreeBSD 15 / Python 3.13 packaging and compatibility;
- Patch 2 (`_19`) — Python automated-job state/progress/event persistence;
- Patch 3 (`_20`) — Python numbered-stage orchestration, budgets, cancellation and finalization;
- Patch 4 (`_21`) — Python finite request/probe execution and Stage-30/40 parsing;
- Patch 5 (`_22`) — Python candidate runtime/readiness/interception and Stage-50 screening;
- Patch 6 (`_23`) — Python Stage-60 expansion, Stage-70 stability/replay and Stage-80 extended protocols;
- Patch 7 (`_24`) — Python final profile construction, exact replay, shortlist and automated circular eligibility;
- Patch 8 (`_25`) — GUI/status reconciliation and post-migration live-gate handoff.

The shared lifecycle lock, audited FreeBSD system mutations and private circular-session
state remain deliberate shell boundaries. Corrective work must not reopen automated Python
ownership without a new architectural decision.

==================================================
LATEST OWNER LIVE RESULT — `_25`
==================================================

Owner-assisted Standard Strategy Lab test:

- candidate: `v0.3.3_25` / `os-zapret2-restyle-0.3.3_25.pkg`;
- target: `rutracker.org`;
- job: `job.c0oydv`;
- initial Zapret2 state: RUNNING;
- 00 PASS;
- 10 PASS;
- 20 PASS;
- 30 PASS — IPv4 available; IPv6 unavailable; QUIC/IPv4 closed;
- 40 PASS — DNS OK; direct TLS 1.3 connection not established;
- 50 ERROR — visible message `Temporary candidate runtime failed internally.`;
- 60–85 SKIPPED;
- 90 PASS — temporary state removed and initial RUNNING Zapret2 restored healthy;
- 99 ERROR.

Patch-8 GUI/status live observations:

- the owner still saw an immediate visible `Статус: ОШИБКА` briefly after pressing Run;
- a later active screenshot correctly showed `Статус: ВЫПОЛНЯЕТСЯ`;
- persisted progress was visible at 36% / Stage 40 instead of remaining at 0% until terminal;
- no unsupported closure is claimed for GUI observations that were not explicitly exercised.

The previous shell-era `_17` result remains historical evidence, but `_25` is now the
latest published and owner-tested live boundary.

==================================================
STAGE-50 LIVE DIAGNOSIS
==================================================

The `_25` failure is **not** evidence that the temporary dvtws2 runtime could not start.
Preserved `candidate-smoke.json` and candidate runtime evidence prove:

- Stage 50 completed 4 of 7 catalog families before aborting;
- `multisplit` failed normally;
- `multidisorder` failed normally;
- `seqovl` **passed** and opened the blocked target;
- `fake` failed normally;
- `accepted=["seqovl"]` and `all_pass=true` were already persisted;
- the `seqovl` candidate runtime had `process_identity:true`, `socket_ready:true`,
  `log_clean:true`, `stable:true`, `ready:true`;
- its reserved IPFW rule counter increased (`intercepted:true`);
- curl returned success against the selected endpoint with HTTP 301;
- candidate shutdown was clean;
- Stage 90 restoration passed.

Source diagnosis:

`strategy_lab_py/candidate.py` deliberately writes a structured JSON result for a
candidate-local error. `strategy_lab_candidate_runner.sh` returns status 1 when that result
contains `"error":true`. Before `_26`, `strategy_lab_py/family.py` treated every nonzero
runner status as a fatal Stage-50 exception before reading the structured candidate result.
Therefore one candidate-local error after the first four catalog entries aborted the whole
screening run, even though `seqovl` had already succeeded.

==================================================
CORRECTIVE `_26`
==================================================

Corrective `_26` has one logical purpose: **candidate-local failure isolation inside
Stage 50**.

Required behavior:

- candidate timeout remains a rejected candidate and screening continues;
- nonzero candidate-runner status accompanied by a fresh, valid structured result with
  `error:true` remains a rejected candidate and screening continues;
- accepted candidates already found are preserved;
- screening proceeds through the remaining catalog entries;
- missing/invalid candidate evidence, runner launch failure, cancellation or another true
  screening/system failure may still abort Stage 50;
- stale candidate JSON must never be reused as evidence for a new attempt.

Implementation:

- `strategy_lab_py/family.py` removes any old per-candidate result before launch;
- it reads fresh structured candidate evidence even when the compatibility runner returns
  nonzero;
- structured `error:true` is aggregated as rejected and records `runner_status`;
- nonzero status without structured candidate error evidence remains fatal.

Focused regression:
`scripts/test-strategy-lab-stage50-candidate-isolation.sh`.

Existing Python candidate/family regression remains authoritative:
`scripts/test-strategy-lab-python-candidate-family.sh`.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All owner-observed items remain open until replacement evidence closes them.

1. **Scenario 1 fails on `_25` at Stage 50.** Corrective `_26` source addresses the
   candidate-isolation defect; live retest required.
2. **Immediate stale/new-job GUI error.** Still observed briefly on `_25`; root cause remains
   open and must be rechecked after Stage 50 can progress further.
3. **Active GUI no-output message.** Patch 8 separates transient reads from persisted state;
   `_25` evidence did not explicitly reproduce or close this item.
4. **GUI progress stuck at 0%.** `_25` showed live persisted progress at 36%; retain as
   partially improved evidence until a complete Scenario-1 run confirms behavior through
   later stages.
5. **Terminal reload/state presentation.** Live recheck still required.
6. **Baseline target-type / DNS parser / DNS failure-class corrections from Patch 4.** Source
   regressions pass; final live closure remains tied to the matrix.
7. **Candidate fatal-log classification from Patch 5.** Source regressions pass; final live
   closure remains tied to the matrix.

==================================================
DELIVERY AND LIVE-GATE BOUNDARY
==================================================

Corrective `_26` is a source candidate only until the normal delivery gates pass:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION=26`;
- candidate identity is `os-zapret2-restyle-0.3.3_26.pkg`;
- focused Stage-50 candidate-isolation regression must pass;
- all Python migration continuity tests must pass;
- complete Strategy Lab corrective matrix must pass;
- repository CI/governance/hygiene must pass;
- FreeBSD 15 package build/inspection must pass.

Testing-prerelease publication remains a separate operation requiring explicit owner
authorization under `docs/GITHUB_PUBLICATION.md`. Do not create tag/prerelease/Release or
publish a package merely because `_26` source/CI is complete.

After an authorized `_26` prerelease is installed, repeat Scenario 1 on `rutracker.org`.
The expected next boundary is that Stage 50 completes all family entries without turning a
single candidate-local failure into terminal ERROR, preserves the already proven `seqovl`
family when applicable, and proceeds to Stage 60. Scenario 1 remains failed until the owner
collects replacement live evidence.

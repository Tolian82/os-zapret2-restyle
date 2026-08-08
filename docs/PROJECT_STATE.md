# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary, blockers, active architectural direction, and next action.

Updated when:
Current source/package identity, live boundary, blocker, approved implementation direction, or next action changes.

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
Latest published testing prerelease: `v0.3.3_17` / `os-zapret2-restyle-0.3.3_17.pkg`
Latest owner-tested testing candidate: `v0.3.3_17` / `os-zapret2-restyle-0.3.3_17.pkg`
Current source line: `VERSION=0.3.3`
Current package revision: `PLUGIN_REVISION=22`
Current migration source candidate: `os-zapret2-restyle-0.3.3_22.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 5 — Python candidate runtime and family screening**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Current GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

==================================================
MIGRATION PATCH 1 FOUNDATION
==================================================

Migration Patch 1 established the supported OPNsense 26.7 platform contract:

- FreeBSD 15.1 / Python 3.13 (`PYTHON=313`);
- stable OPNsense interpreter link `/usr/local/bin/python3`;
- direct plugin dependency `python313` mapped to `lang/python313`;
- standard-library-only Python migration code;
- packaged Python launcher/entry point/foundation.

==================================================
MIGRATION PATCH 2 STATE OWNERSHIP
==================================================

Migration Patch 2 made `strategy_lab_py/state.py` the authoritative automated-job
persistence owner for schema-2 state, revisioned mutations, progress, cancellation,
events and structured result/lifecycle fields. `strategy_lab/state.sh` remains a
compatibility adapter; private circular-session `state.json` remains shell-owned.

==================================================
MIGRATION PATCH 3 ORCHESTRATION OWNERSHIP
==================================================

Migration Patch 3 made Python the production owner of:

- numbered stage order `00,10,20,30,40,50,60,70,80,85,90,99`;
- Standard/Extended absolute budgets and per-stage arbitration;
- cancellation/signal/timeout orchestration;
- mandatory Stage 90 restoration and Stage 99 convergence;
- terminal state/outcome/report policy and `RESTORE_FAILED` override.

The production path is:

```text
zapret_service.sh
  -> strategy_lab_worker.sh
  -> strategy_lab_python_launcher.sh
  -> strategy_lab_python.py orchestrate JOB_ID
  -> strategy_lab_py/orchestrator.py
  -> strategy_lab_stage_adapter.sh for still-unmigrated stage algorithms
```

The inherited lifecycle lock fd 9 remains authoritative and is passed to adapters.

==================================================
MIGRATION PATCH 4 REQUEST / PROBE OWNERSHIP
==================================================

Migration Patch 4 made Python 3.13 authoritative for bounded DNS/TLS/HTTP/TCP/QUIC-control
subprocess execution and Stage 30/40 probe parsing.

`strategy_lab_py/request.py` owns finite request execution with command, return code,
stdout, stderr, timeout/termination/signal and duration preserved separately.
`strategy_lab_py/probe.py` owns Stage 30 network capability probing and Stage 40 clean
baseline execution/parsing while preserving the public `network.json` and `baseline.json`
contracts. DNS A/AAAA records are accepted only from the real `ANSWER SECTION`.

Shell request/probe files are compatibility adapters only. Patch 4 also corrected terminal
publication ordering so circular eligibility is persisted before terminal state is visible.

==================================================
MIGRATION PATCH 5 CANDIDATE / FAMILY OWNERSHIP
==================================================

Migration Patch 5 makes Python 3.13 authoritative for the standard TLS 1.3 Stage-50 path.

`strategy_lab_py/candidate.py` owns:

- endpoint-to-IPv4 binding via the Patch-4 DNS parser;
- standard candidate runtime sequencing;
- readiness qualification from process identity, divert socket and startup-log evidence;
- two-stable-snapshot readiness convergence;
- fatal startup-log classification;
- endpoint-bound TLS 1.3/TCP checks;
- remote-IP identity and IPFW before/after interception evidence;
- standard candidate success/error evidence and mandatory cleanup request.

`strategy_lab_py/family.py` owns:

- the existing ordered seven-family TLS 1.3 catalog;
- one-candidate-at-a-time isolation;
- per-candidate timeout and cancellation;
- `family.json` completed/accepted/rejected aggregation.

`strategy_lab_candidate_adapter.sh` is the narrow shell boundary for audited FreeBSD
mutations/observations only: WAN lookup, candidate files, reserved IPFW rules/counters,
job-directory access, daemon launch/stop, process identity and divert-socket snapshots.
It does not choose readiness, candidate outcome, family order or timeout policy.

`strategy_lab_candidate_runner.sh` and `strategy_lab_family_runner.sh` are Python launch
boundaries. The candidate runner preserves its historical 3–7 argument/default contract.
The old shell `strategy_lab_family_screen()` owner is retired and has no fallback.

Expansion/stability and TLS 1.2/HTTP/QUIC/UDP extended orchestration remain shell-owned
until Migration Patch 6.

==================================================
FINAL SHELL-ERA LIVE BOUNDARY
==================================================

Owner-assisted Standard Strategy Lab test on `v0.3.3_17`:

- target: `rutracker.org`;
- job shown by GUI: `job.w0nXxQ`;
- initial Zapret2 state: RUNNING.

Final stages:

- 00 PASS — target initialized as domain;
- 10 PASS — initial RUNNING state captured;
- 20 PASS — normal Zapret2 stopped;
- 30 PASS — IPv4 available; IPv6 unavailable; QUIC/IPv4 closed;
- 40 PASS — DNS OK; direct TLS 1.3 connection not established;
- 50 ERROR — `Temporary candidate runtime failed internally.`;
- 60–85 SKIPPED;
- 90 PASS — temporary state cleaned and original Zapret2 restored healthy RUNNING;
- 99 ERROR.

Immediate active-GUI observation on the same run:

- the new job ID appeared together with `Статус: ОШИБКА` immediately after Run;
- `Strategy Lab returned no output.` was displayed while the job was still active;
- visible progress stayed at 0% during active work;
- terminal presentation jumped directly to 100%.

No `_17` candidate-runtime log bundle was collected in this run. Therefore the exact
remaining `_17` Stage-50 root cause is intentionally not claimed.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All owner-observed items remain open until replacement evidence closes them. Source
migration does not substitute for live/UI evidence.

1. **Stage 50 remains ERROR on `_17`.** Exact `_17` root cause is not yet established.
2. **Immediate stale/new-job GUI error.** A fresh job ID can be shown with visible `ERROR` before terminal evidence exists.
3. **Active GUI no-output message.** `Strategy Lab returned no output.` can appear while backend work continues.
4. **GUI progress stuck at 0%.** Backend work advances while visible progress remains 0%, then jumps to terminal 100%.
5. **Baseline target-type corruption.** Patch 4 removes the old shell-global mechanism in source; live/UI closure is still pending.
6. **DNS answer parser weakness.** Patch 4 replaces the old parser with ANSWER-section-aware Python parsing; live closure is still pending where applicable.
7. **DNS diagnostics flatten failure classes.** Patch 4 adds distinct structured timeout/command/parser evidence; live closure is still pending where applicable.
8. **Terminal reload/state presentation defect.** Retained terminal state can be presented incorrectly on Diagnostics reopen.
9. **Candidate fatal-log classification defect.** Patch 5 replaces the standard-candidate readiness mechanism and adds focused fatal-log rejection regression; live closure remains pending.

==================================================
PYTHON MIGRATION PATCH SEQUENCE
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**.

Patch 2 — Python automated-job state, progress, and structured persistence: **COMPLETE / MERGED AS `_19`**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **COMPLETE / MERGED AS `_20`**.

Patch 4 — Python finite request/probe execution and parsing: **COMPLETE / MERGED AS `_21`**.

Patch 5 — Python candidate runtime and family screening: **CURRENT `_22` SOURCE CHANGE**.

Patch 6 — Python expansion, stability, and extended protocol orchestration: **NEXT AFTER PATCH 5 QUALIFICATION**.

Patch 7 — Python result/shortlist completion and obsolete shell-orchestration retirement.

Patch 8 — GUI/status reconciliation and post-migration live gate.

==================================================
DELIVERY AND PACKAGE BOUNDARY
==================================================

Migration Patch 5 is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `22`;
- current source candidate is `os-zapret2-restyle-0.3.3_22.pkg`;
- latest published/owner-tested live evidence remains `_17`;
- `_22` does not resume the owner-assisted live matrix because Patch 6–8 responsibilities
  have not yet reached the designated Python parity gate.

The `_22` source must pass Python foundation/state/orchestration/request-probe/candidate-
family tests, the complete corrective matrix, full repository CI, and FreeBSD 15
package/content/manifest verification before squash merge. Testing-prerelease publication
remains a separate operation requiring explicit publication authority.

Stable release and pkg-repository promotion remain blocked until the Python path reaches
functional parity and the owner-assisted live matrix passes.

==================================================
NEXT ACTION
==================================================

Complete Migration Patch 5 qualification on `_22`:

1. focused Python candidate/runtime/readiness/family regression;
2. Python foundation/state/orchestration/request-probe compatibility checks;
3. canonical Strategy Lab corrective matrix;
4. full repository CI;
5. FreeBSD 15 Python 3.13 candidate/family test and package/content/manifest verification;
6. squash merge only from the successfully validated latest head.

After Patch 5 is merged, begin **Migration Patch 6 only**: move parameter expansion,
stability/replay, and extended-protocol orchestration to Python. Final result/shortlist
retirement remains Patch 7 and GUI/status reconciliation remains Patch 8.

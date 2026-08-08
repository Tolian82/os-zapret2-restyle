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
Current package revision: `PLUGIN_REVISION=23`
Current migration source candidate: `os-zapret2-restyle-0.3.3_23.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 6 — Python search and extended orchestration**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Current GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

==================================================
MIGRATION OWNERSHIP THROUGH PATCH 5
==================================================

Migration Patch 1 established FreeBSD 15 / Python 3.13 packaging and compatibility.
Migration Patch 2 made `strategy_lab_py/state.py` the automated-job persistence owner.
Migration Patch 3 made `strategy_lab_py/orchestrator.py` the numbered-stage, budget,
cancellation and terminal restoration/finalization owner. Migration Patch 4 made
`strategy_lab_py/request.py` and `probe.py` authoritative for finite requests and Stage
30/40 parsing. Migration Patch 5 made `candidate.py` and `family.py` authoritative for the
standard TLS 1.3 candidate runtime/readiness/interception path and ordered Stage-50 family
screening.

The shared lifecycle lock, private circular-session state, and audited FreeBSD system
mutations remain outside Python unless explicitly migrated by a designated patch.

==================================================
MIGRATION PATCH 6 SEARCH / EXTENDED OWNERSHIP
==================================================

Migration Patch 6 makes Python 3.13 authoritative for Stages 60, 70 and 80 search policy.

`strategy_lab_py/search.py` owns:

- Stage-60 accepted-family expansion catalog selection and ordering;
- per-expansion-candidate timeout/cancellation and early-stop policy;
- incremental expansion result aggregation with existing stop reasons;
- Stage-70 passing-source collection and strategy de-duplication;
- deterministic stability ranking by line count, character count and id;
- replay-attempt sequencing, candidate limits, stable/unstable aggregation and early stop;
- process-group termination plus audited cleanup request after candidate timeout/cancel.

`strategy_lab_py/extended.py` owns:

- Stage-80 TLS 1.2 and HTTP catalog sequencing and first-working selection;
- QUIC capability-derived skip policy, sequential candidate search and first-working/not-found result;
- configured generic-UDP input consumption, skip policy, sequential candidate search and first-working/not-found result.

`strategy_lab_py/candidate.py` is generalized rather than duplicated. TLS 1.3, TLS 1.2,
HTTP, QUIC and generic UDP now share one Python candidate lifecycle/readiness/interception/
cleanup policy. PASS requires successful finite request execution, exact selected endpoint,
and verified IPFW packet-counter growth.

`strategy_lab_py/request.py` now also owns exact selected-endpoint QUIC and generic-UDP
request/response execution while preserving structured subprocess evidence.

`strategy_lab_candidate_adapter.sh` remains a narrow shell system boundary for audited
FreeBSD mutations/observations. It accepts explicit protocol transport/port/L7 settings but
does not choose search order, timeouts, readiness verdict or candidate/protocol outcome.

Production expansion/stability/extended-TCP/QUIC/UDP runners are thin Python launchers.
Legacy shell search/extended modules remain packaged only until Patch 7 retires obsolete
orchestration surfaces; they are not production owners after `_23`.

==================================================
FINAL SHELL-ERA LIVE BOUNDARY
==================================================

Owner-assisted Standard Strategy Lab test on `v0.3.3_17`:

- target: `rutracker.org`;
- job shown by GUI: `job.w0nXxQ`;
- initial Zapret2 state: RUNNING;
- Stage 40 PASS — DNS OK, direct TLS 1.3 not established;
- Stage 50 ERROR — `Temporary candidate runtime failed internally.`;
- Stages 60–85 skipped;
- Stage 90 PASS — initial RUNNING state restored healthy;
- terminal Stage 99 ERROR.

Observed GUI defects on the same run remain open: immediate visible ERROR for the new job,
`Strategy Lab returned no output.` while active, and visible 0% progress until terminal.
No `_17` candidate-runtime log bundle exists, so the exact `_17` Stage-50 root cause is not
claimed.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All owner-observed items remain open until replacement evidence closes them. Source
migration does not substitute for live/UI evidence.

1. **Stage 50 remains ERROR on `_17`.** Exact `_17` root cause is not established.
2. **Immediate stale/new-job GUI error.** A fresh job ID can be shown with visible ERROR before terminal evidence exists.
3. **Active GUI no-output message.** `Strategy Lab returned no output.` can appear while backend work continues.
4. **GUI progress stuck at 0%.** Backend work advances while visible progress remains 0%, then jumps to terminal 100%.
5. **Baseline target-type corruption.** Patch 4 replaces the old source mechanism; live/UI closure remains pending.
6. **DNS answer parser weakness.** Patch 4 replaces the old parser with ANSWER-section-aware Python parsing; live closure remains pending where applicable.
7. **DNS diagnostics flatten failure classes.** Patch 4 preserves distinct timeout/command/parser evidence; live closure remains pending where applicable.
8. **Terminal reload/state presentation defect.** Retained terminal state can be presented incorrectly on Diagnostics reopen.
9. **Candidate fatal-log classification defect.** Patch 5 replaces the standard source mechanism and regression-covers fatal-log rejection; live closure remains pending.

==================================================
PYTHON MIGRATION PATCH SEQUENCE
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**.

Patch 2 — Python automated-job state, progress, and structured persistence: **COMPLETE / MERGED AS `_19`**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **COMPLETE / MERGED AS `_20`**.

Patch 4 — Python finite request/probe execution and parsing: **COMPLETE / MERGED AS `_21`**.

Patch 5 — Python candidate runtime and family screening: **COMPLETE / MERGED AS `_22`**.

Patch 6 — Python expansion, stability/replay, and extended protocol orchestration: **CURRENT `_23` SOURCE CHANGE**.

Patch 7 — Python final result/shortlist completion and obsolete shell-orchestration retirement: **NEXT AFTER PATCH 6 QUALIFICATION**.

Patch 8 — GUI/status reconciliation and post-migration live gate.

==================================================
DELIVERY AND PACKAGE BOUNDARY
==================================================

Migration Patch 6 is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `23`;
- current source candidate is `os-zapret2-restyle-0.3.3_23.pkg`;
- latest published and owner-tested live candidate remains `_17`;
- `_23` does not resume the owner-assisted live matrix because final result/shortlist
  retirement and GUI/status reconciliation remain Patches 7 and 8.

The `_23` source must pass all earlier Python migration regressions, the focused Patch-6
search/extended regression, the complete Strategy Lab corrective matrix, full repository
CI, and FreeBSD 15 package/content/manifest verification before squash merge.
Testing-prerelease publication remains a separate operation requiring explicit authority.

Stable release and pkg-repository promotion remain blocked until the Python path reaches
functional parity and the owner-assisted live matrix passes.

==================================================
NEXT ACTION
==================================================

Complete Migration Patch 6 qualification on `_23`:

1. focused Python expansion/stability/extended protocol regression;
2. all Patch-1…5 Python compatibility checks;
3. canonical Strategy Lab corrective matrix;
4. full repository CI;
5. FreeBSD 15 Python 3.13 Patch-6 test and package/content/manifest verification;
6. squash merge only from the successfully validated latest head.

After Patch 6 merges, begin **Migration Patch 7 only**: move final result/shortlist
completion to the intended owner and retire obsolete shell orchestration. GUI/status
reconciliation and owner-assisted live verification remain Patch 8.

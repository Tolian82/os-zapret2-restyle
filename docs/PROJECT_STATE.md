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
Current package revision: `PLUGIN_REVISION=25`
Current migration source candidate: `os-zapret2-restyle-0.3.3_25.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 8 — GUI/status reconciliation and post-migration live gate**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Current GitHub delivery authority:
`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and the other active dated
GitHub decisions referenced by the publication authority.

==================================================
AUTOMATED PYTHON OWNERSHIP THROUGH PATCH 7
==================================================

Migration Patch 1 established FreeBSD 15 / Python 3.13 packaging and compatibility.
Migration Patch 2 made `strategy_lab_py/state.py` the automated-job persistence owner.
Migration Patch 3 made `strategy_lab_py/orchestrator.py` the numbered-stage, budget,
cancellation and terminal restoration/finalization owner. Migration Patch 4 made
`strategy_lab_py/request.py` and `probe.py` authoritative for finite requests and Stage
30/40 parsing. Migration Patch 5 made `candidate.py` and `family.py` authoritative for the
unified candidate runtime/readiness/interception path and Stage-50 family screening.
Migration Patch 6 made `search.py` and `extended.py` authoritative for Stage-60 expansion,
Stage-70 stability/replay and Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP orchestration.
Migration Patch 7 made `result.py` authoritative for complete profile construction, exact
three-pass final replay, unified shortlist publication and automated circular eligibility,
and removed the competing automated shell replay/result/stage-machine owners.

The shared lifecycle lock, audited FreeBSD system mutations and private circular-session
state remain deliberate shell boundaries. Patch 8 must not reopen automated backend
ownership that Patches 2–7 moved to Python.

==================================================
MIGRATION PATCH 8 GUI / STATUS RECONCILIATION
==================================================

The `_25` source candidate addresses the presentation/status boundary required before the
post-migration live matrix can resume.

Confirmed source defect:

- automated `start_job()` launched the long-lived lifecycle worker through `daemon(8)`
  without closing launcher lock FD 9;
- the private circular launcher already closed FD 9 correctly;
- the automated worker could therefore inherit the launcher serialization lock while
  status/result/cancel requests attempted the same nonblocking lock;
- transient/empty configd output was then rendered by Diagnostics as if transport
  `status:error` were persisted job `state:error`.

Patch 8 source reconciliation:

- automated daemon launch now uses `9>&-`;
- empty/invalid configd output is marked `transient=true` by the API controller;
- AJAX/network errors use the same transient channel;
- Diagnostics renders job state only from a validated persisted job snapshot;
- transport `status` can no longer masquerade as visible job state;
- transient active polling preserves the last valid state/progress and retries;
- accepted starts render immediately as queued Stage 00;
- persisted Python `progress.percent` remains authoritative;
- active reload discovery retries transient reads but explicit idle does not resurrect
  retained terminal history;
- circular presentation preserves its last valid state across transient/busy reads.

Focused source regression:
`scripts/test-strategy-lab-gui-status-reconciliation.sh`.

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

Observed GUI defects on the same run remain open until replacement live evidence exists:

- immediate visible ERROR for the new job;
- `Strategy Lab returned no output.` while the job remained active;
- visible progress remained 0%, then jumped to terminal 100%;
- terminal/reload state presentation required recheck.

No `_17` candidate-runtime log bundle exists, so the exact `_17` Stage-50 root cause is not
claimed.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All owner-observed items remain open until replacement evidence closes them. Source
migration or a focused regression does not substitute for live/UI evidence.

1. **Stage 50 remains ERROR on `_17`.** Exact `_17` root cause is not established.
2. **Immediate stale/new-job GUI error.** `_25` changes the launcher/status mechanism; live closure pending.
3. **Active GUI no-output message.** `_25` separates transient reads from persisted state; live closure pending.
4. **GUI progress stuck at 0%.** `_25` restores concurrent status reads and persisted-progress rendering; live closure pending.
5. **Baseline target-type corruption.** Patch 4 replaced the old source mechanism; live closure pending.
6. **DNS answer parser weakness.** Patch 4 replaced the old parser; live closure pending.
7. **DNS diagnostics flatten failure classes.** Patch 4 preserves distinct evidence; live closure pending.
8. **Terminal reload/state presentation defect.** `_25` reconciles active discovery versus idle history; live closure pending.
9. **Candidate fatal-log classification defect.** Patch 5 replaced the source mechanism; live closure pending.

==================================================
PYTHON MIGRATION PATCH SEQUENCE
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**.

Patch 2 — Python automated-job state, progress, and structured persistence: **COMPLETE / MERGED AS `_19`**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **COMPLETE / MERGED AS `_20`**.

Patch 4 — Python finite request/probe execution and parsing: **COMPLETE / MERGED AS `_21`**.

Patch 5 — Python candidate runtime and family screening: **COMPLETE / MERGED AS `_22`**.

Patch 6 — Python expansion, stability/replay, and extended protocol orchestration: **COMPLETE / MERGED AS `_23`**.

Patch 7 — Python final result/shortlist completion and obsolete shell-orchestration retirement: **COMPLETE / MERGED AS `_24`**.

Patch 8 — GUI/status reconciliation and post-migration live gate: **CURRENT `_25` SOURCE CHANGE; LIVE EVIDENCE PENDING**.

==================================================
DELIVERY AND LIVE-GATE BOUNDARY
==================================================

Migration Patch 8 `_25` is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `25`;
- current source candidate is `os-zapret2-restyle-0.3.3_25.pkg`;
- latest published and owner-tested live candidate remains `_17`;
- no `_25` tag/prerelease/Release is authorized merely by starting this source patch.

Before squash merge, `_25` must pass the focused GUI/status reconciliation regression,
all Python migration continuity tests, the complete Strategy Lab corrective matrix, full
repository CI/governance/hygiene checks and the FreeBSD 15 package gate.

After source merge, testing-prerelease publication is a separate operation requiring
explicit owner authorization under `docs/GITHUB_PUBLICATION.md`. Only after an authorized
post-migration candidate is installed can Scenario 1 resume and the frozen live defects be
closed or carried forward from new evidence.

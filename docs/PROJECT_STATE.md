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
Current package revision: `PLUGIN_REVISION=24`
Current migration source candidate: `os-zapret2-restyle-0.3.3_24.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 7 — Python final result ownership and shell-orchestration retirement**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Current GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

==================================================
MIGRATION OWNERSHIP THROUGH PATCH 6
==================================================

Migration Patch 1 established FreeBSD 15 / Python 3.13 packaging and compatibility.
Migration Patch 2 made `strategy_lab_py/state.py` the automated-job persistence owner.
Migration Patch 3 made `strategy_lab_py/orchestrator.py` the numbered-stage, budget,
cancellation and terminal restoration/finalization owner. Migration Patch 4 made
`strategy_lab_py/request.py` and `probe.py` authoritative for finite requests and Stage
30/40 parsing. Migration Patch 5 made `candidate.py` and `family.py` authoritative for the
standard TLS 1.3 candidate runtime/readiness/interception path and ordered Stage-50 family
screening. Migration Patch 6 made `search.py` and `extended.py` authoritative for Stage-60
parameter expansion, Stage-70 stability/replay, and Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP
orchestration while generalizing the Python candidate owner across those protocols.

The shared lifecycle lock, private circular-session state, and audited FreeBSD system
mutations remain outside Python unless explicitly migrated by a designated patch.

==================================================
MIGRATION PATCH 7 FINAL RESULT OWNERSHIP
==================================================

Migration Patch 7 makes Python 3.13 authoritative for the remaining automated final-result
policy.

`strategy_lab_py/result.py` owns:

- complete user-ready profile construction and validation;
- deterministic collection/ranking of stable TLS 1.3 and Extended protocol sources;
- exact three-attempt replay of the complete published profile;
- replay verification requiring request success plus exact profile identity on every pass;
- Standard and Extended unified shortlist selection;
- recommendation and circular-compatible TLS 1.3 subset publication;
- automated-job circular-eligibility evaluation after Stage 90 restoration.

Final replay reuses `strategy_lab_py/candidate.py`; there is no separate runtime,
readiness, interception, cleanup, timeout or protocol candidate state machine. The narrow
`strategy_lab_profile_candidate_adapter.sh` changes only the validated static domain
selector into the temporary runtime hostlist required by dvtws2 and delegates every other
candidate system action to `strategy_lab_candidate_adapter.sh`.

`strategy_lab_worker.sh` routes Stage 85 and automated eligibility through
`strategy_lab_python_stage_adapter.sh`; all non-final OS-specific stage actions continue to
the audited system stage adapter. Legacy shell final-profile/replay/eligibility ownership
is being removed in this same patch rather than retained as a fallback competitor.

Public status/shortlist/profile/circular contracts remain compatible. Private circular
session `state.json` and its frozen-parent consumer remain shell-owned by design.

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

Patch 6 — Python expansion, stability/replay, and extended protocol orchestration: **COMPLETE / MERGED AS `_23`**.

Patch 7 — Python final result/shortlist completion and obsolete shell-orchestration retirement: **CURRENT `_24` SOURCE CHANGE**.

Patch 8 — GUI/status reconciliation and post-migration live gate: **NEXT AFTER PATCH 7 QUALIFICATION**.

==================================================
DELIVERY AND PACKAGE BOUNDARY
==================================================

Migration Patch 7 is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `24`;
- current source candidate is `os-zapret2-restyle-0.3.3_24.pkg`;
- latest published and owner-tested live candidate remains `_17`;
- `_24` does not resume or close the owner-assisted live matrix;
- GUI/status reconciliation and the post-migration owner-assisted live gate remain Patch 8.

The `_24` source must pass all earlier Python migration regressions, focused final-result
ownership/replay/shortlist coverage, the complete Strategy Lab corrective matrix, full
repository CI, and FreeBSD 15 package/content/manifest verification before squash merge.
Testing-prerelease publication remains a separate operation requiring explicit authority.

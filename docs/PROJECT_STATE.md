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
Current package revision: `PLUGIN_REVISION=18`
Current migration source candidate: `os-zapret2-restyle-0.3.3_18.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 1 — packaged Python platform/compatibility foundation**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` together with repository-root `AGENTS.md` and `docs/GITHUB_PUBLICATION.md`.

==================================================
MIGRATION PATCH 1 FOUNDATION
==================================================

The supported OPNsense 26.7 platform contract is now explicit:

- OPNsense 26.7 build configuration targets FreeBSD 15.1 and Python 3.13 (`PYTHON=313`);
- OPNsense core provides `/usr/local/bin/python3` as the stable interpreter link;
- the plugin declares the direct package dependency `python313`;
- the custom package manifest maps it to `lang/python313`;
- Python migration code remains standard-library-only; no third-party `pip` dependency is approved.

Packaged foundation files:

- `strategy_lab_python_launcher.sh` — thin runtime/version check and compatibility launcher;
- `strategy_lab_python.py` — minimal packaged entry point;
- `strategy_lab_py/` — Python compatibility foundation module.

Important cutover boundary:

`zapret_service.sh` still launches the existing `strategy_lab_worker.sh` directly. The
Python launcher is packaged and tested but is not the production call path in Migration
Patch 1. Therefore no Strategy Lab state-machine, lifecycle, persistence, probe,
candidate, or result ownership changes in `_18`.

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
- 99 ERROR — internal Strategy Lab error with retained results.

Immediate active-GUI observation on the same run:

- the new job ID appeared together with `Статус: ОШИБКА` immediately after Run;
- `Strategy Lab returned no output.` was displayed while the job was still active;
- visible progress stayed at 0% during active work;
- terminal presentation jumped directly to 100%.

No `_17` candidate-runtime log bundle was collected in this run. Therefore the exact
remaining `_17` Stage-50 root cause is intentionally not claimed. The previous `_16`
hostlist traversal failure was real and corrected in `_17`, but the repeated high-level
Stage-50 message proves only that another Stage-50 failure remains.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
CONFIRMED LIVE SUB-GATES
==================================================

The owner-assisted series has established these reusable facts:

- FreeBSD DNS foreground-timeout correction is live-proven: stage 40 can pass with `DNS: OK`;
- normal Zapret2 restoration is live-proven after the earlier FreeBSD timeout correction: stage 90 repeatedly returns initially RUNNING service to healthy RUNNING;
- temporary Strategy Lab runtime can reach real dvtws2 startup/bind/privilege-drop paths;
- `v0.3.3_17` still does not complete Stage 50 successfully;
- no complete Standard Strategy Lab scenario is yet live PASS.

Authoritative live matrix:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

==================================================
APPROVED IMPLEMENTATION DIRECTION
==================================================

The project will not continue growing the large sourced POSIX-shell Strategy Lab worker
as the primary orchestration implementation.

Approved target boundary:

```text
Diagnostics GUI / JavaScript
        ↓
OPNsense PHP MVC/API
        ↓
configd
        ↓
thin compatibility launcher
        ↓
Python Strategy Lab orchestration
        ↓
small explicit FreeBSD/OPNsense system adapters and external tools
```

Responsibilities intended for Python:

- job/state model and atomic JSON persistence;
- stage machine, progress, budgets, cancellation, and terminal finalization;
- subprocess execution with separate return code/stdout/stderr/timeout state;
- DNS/TLS/HTTP parsing and error classification;
- candidate and family orchestration;
- expansion, stability, extended-protocol orchestration;
- structured result/shortlist generation.

Responsibilities intentionally retained outside Python unless separately justified:

- PHP MVC/API request validation and configd integration;
- small audited shell/service adapters for Zapret2 lifecycle, shared lock, `ipfw`, process
  ownership, and other short FreeBSD-specific mutations where reusing existing behavior
  is safer than duplicating it.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All items remain open until replacement evidence closes them. Migration does not reset
or automatically resolve the backlog.

1. **Stage 50 remains ERROR on `_17`.** Exact `_17` root cause is not yet established.
2. **Immediate stale/new-job GUI error.** A fresh job ID can be shown with visible `ERROR` before terminal evidence exists.
3. **Active GUI no-output message.** `Strategy Lab returned no output.` can appear while backend work continues.
4. **GUI progress stuck at 0%.** Backend work advances while visible progress remains 0%, then jumps to terminal 100%.
5. **Baseline target-type corruption.** Shell-global `_strategy_lab_type` can turn domain state into `A`.
6. **DNS answer parser is semantically weak.** `IN A`/`IN AAAA` text can be matched without proving an answer-section record.
7. **DNS diagnostics flatten failure classes.** Timeout, command failure, and parser rejection can collapse into generic failure code 1.
8. **Terminal reload/state presentation defect.** Retained terminal state can be presented incorrectly on Diagnostics reopen.
9. **Candidate fatal-log classification defect.** Readiness evidence can report a clean log while fatal runtime text exists.

The Python migration plan maps these defects to replacement tests and later live/UI
verification. A defect may disappear because the old implementation mechanism is
removed, but it is closed only after a focused regression and required live evidence.

==================================================
PYTHON MIGRATION PATCH SEQUENCE
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **CURRENT `_18` SOURCE CHANGE**.

Patch 2 — Python job state, progress, and structured persistence: **NEXT AFTER PATCH 1 QUALIFICATION**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization.

Patch 4 — Python request/probe execution and parsing.

Patch 5 — Python candidate runtime and family screening.

Patch 6 — Python expansion, stability, and extended protocol orchestration.

Patch 7 — Python result/shortlist completion and obsolete shell-orchestration retirement.

Patch 8 — GUI/status reconciliation and post-migration live gate.

The specialist plan may split a listed patch further when one item exceeds one logical
change. It must not compress the migration into a monolithic rewrite.

==================================================
DELIVERY AND PACKAGE BOUNDARY
==================================================

Migration Patch 1 is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `18`;
- current source candidate is `os-zapret2-restyle-0.3.3_18.pkg`;
- published and owner-tested live evidence remains `_17` until a newer artifact is actually published/tested;
- `_18` does not resume the live matrix because the production Strategy Lab call path is unchanged.

The `_18` source must pass the normal Ready-PR, complete CI, and FreeBSD 15 package gate
before squash merge. Testing-prerelease publication follows the owner's standing
installable-patch authority without an additional routine confirmation.

Stable release and pkg-repository promotion remain blocked until the Python path reaches
functional parity and the owner-assisted live matrix passes.

==================================================
NEXT ACTION
==================================================

Complete Migration Patch 1 qualification on `_18`:

1. focused Python 3.13 foundation test;
2. canonical Strategy Lab corrective matrix;
3. full repository CI;
4. FreeBSD 15 package build/content/manifest verification;
5. squash merge only from the successfully validated latest head.

After Patch 1 is merged, begin **Migration Patch 2 only**: move job state, progress, and
structured persistence to Python while preserving the public JSON contract and keeping the
stage machine outside that patch.

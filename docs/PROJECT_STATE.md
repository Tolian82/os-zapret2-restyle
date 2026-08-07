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
Current package revision: `PLUGIN_REVISION=17`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Python migration handoff; source migration not started yet**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` together with repository-root `AGENTS.md` and `docs/GITHUB_PUBLICATION.md`.

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

No Python interpreter path/version is assumed yet. Migration Patch 1 must verify the
supported OPNsense Python runtime/dependency model before packaged code relies on it.
No third-party `pip` dependency is approved by default.

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

Patch 0 — documentation/handoff: **CURRENT DOCUMENTATION CHANGE**.

Patch 1 — Python platform and compatibility foundation.

Patch 2 — Python job state, progress, and structured persistence.

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

This handoff is documentation/governance only:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` remains `17`;
- no new package bytes are required for the documentation handoff;
- the already published `_17` package remains the final shell-era live evidence package.

Every packaged Python migration change uses the normal Ready-PR/CI/squash path and
FreeBSD 15 package build. Testing-prerelease publication follows the owner's standing
installable-patch authority without an additional routine confirmation.

Stable release and pkg-repository promotion remain blocked until the Python path reaches
functional parity and the owner-assisted live matrix passes.

==================================================
NEXT ACTION
==================================================

Start the next development topic from current `main` and read, in order:

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. this `docs/PROJECT_STATE.md`;
4. `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`;
5. `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Then inspect current Strategy Lab source and perform **Migration Patch 1 only**:
verify the target OPNsense Python interpreter/dependency model and add the minimal
packaged Python compatibility foundation without changing product behavior.

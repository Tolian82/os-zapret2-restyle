# DIAG-001 — Synchronous Blockcheck replacement by Strategy Lab

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What is broken in the current Blockcheck chain and how will remediation be verified?

Purpose:
Maintain the complete approved remediation record for replacement of the synchronous
Blockcheck implementation.

Read after:
`docs/AUDIT.md`.

==================================================
CLASSIFICATION
==================================================

Finding:
broken / replacement implementation in progress

==================================================
CURRENT LEGACY CHAIN
==================================================

Diagnostics GUI 600-second AJAX request
        ↓
DiagnosticsController long synchronous action
        ↓
650-second backend wait
        ↓
600-second configd action
        ↓
`blockcheck.sh` 1500-second timeout
        ↓
service stop/start, PF/IPFW mutation, upstream blockcheck2, textual SUMMARY parsing

The legacy chain remains the active Run-button path until Patch 13.

==================================================
CONFIRMED PROBLEMS
==================================================

- browser, PHP, configd, wrapper, and upstream timeout ownership is inconsistent;
- a long synchronous HTTP request cannot provide resilient resumable progress;
- initial and restored service state is not represented by a complete staged contract;
- restoration failure cannot be reported as `RESTORE_FAILED`;
- process, PF/IPFW, upstream execution, parser, and JSON responsibilities are combined
  in one wrapper;
- textual SUMMARY parsing is not a stable basis for family-first search, required
  endpoints, stability, shortlist, extended protocols, or circular validation;
- there is no persistent asynchronous job, ordered event stream, or controlled partial
  result after cancellation;
- canceled, timed-out, skipped, and unexecuted work cannot be represented consistently.

==================================================
APPROVED REMEDIATION
==================================================

Implement the 13-patch asynchronous Strategy Lab architecture in
`docs/architecture/STRATEGY_LAB.md`.

The final system provides start/status/events/cancel/result, one active job, shared
lifecycle restoration, numbered stages 00–99, bounded timeouts, fixed network prechecks,
isolated candidates, family-first search, 3/3 stability, bilingual reporting, extended
protocols, circular validation, and final removal of the synchronous caller chain.

==================================================
CANCELLATION ACCEPTANCE
==================================================

Cancellation preserves completed results, stops current work, skips interrupted and
remaining stages, executes mandatory restoration, and returns a partial normal result.

Exact messages:

- Russian: `SKIPPED — отменено`;
- English: `SKIPPED — canseled`.

Restoration failure remains `RESTORE_FAILED` regardless of prior results.

==================================================
PATCH 1 EVIDENCE
==================================================

Status:
COMPLETE

- complete architecture and patch series recorded;
- PR #50 contained one documentation-only atomic commit;
- Validate Project and FreeBSD package build passed;
- squash merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- task branch removed;
- `main` verified before Patch 2 preparation.

==================================================
PATCH 2 REMEDIATION
==================================================

Status:
SOURCE IMPLEMENTED / AUTOMATED CONTRACT PASSED / IN DELIVERY

New files:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/common.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/state.sh`;
- `scripts/test-strategy-lab-job-contract.sh`.

Implemented contract:

- immediate generated `job_id`;
- start, status, cancel, and result modes;
- detached worker through `daemon(8)`;
- one active job with busy response;
- launcher serialization through `lockf`;
- atomically replaced `status.json` and ordered `events.ndjson`;
- active pointer, PID, cancellation marker, and log path;
- honest framework-only `PARTIAL` completion;
- cancellation produces `PARTIAL` and exact selected-language skipped text;
- idle state after active cleanup;
- four configd actions and four API actions;
- dormant GUI polling/progress/Stop helpers;
- legacy Blockcheck Run-button behavior unchanged.

Explicit Patch 2 exclusions:

- no network probe;
- no normal Zapret2 stop/start;
- no temporary candidate dvtws2;
- no firewall mutation;
- no migration of the active Run button.

Automated verification completed before publication:

- shell and PHP syntax;
- mocked detached start and immediate job ID;
- normal framework completion;
- busy response for a second job;
- exact Russian and English cancellation text;
- unfinished-stage SKIPPED state;
- active pointer cleanup and idle result;
- unsafe target rejection;
- static actions/API/GUI contract;
- static confirmation that legacy Blockcheck remains active.

==================================================
REMAINING PATCHES
==================================================

Patch 3 implements lifecycle stop, cleanup, and exact restoration. Later patches add
network precheck, candidate runtime, family search, stability, reporting, extended
protocols, circular validation, and final migration.

==================================================
OWNER-ASSISTED VERIFICATION
==================================================

No manual OPNsense checks are requested during Patches 1 through 13. Every patch must
pass automated tests, CI, package build where applicable, full merge processing, and
branch cleanup. One consolidated owner-assisted matrix follows Patch 13.

==================================================
SERIAL DELIVERY BLOCKER
==================================================

Patch 3 preparation is prohibited until Patch 2 completes every PR check, squash merge,
post-merge workflow, branch cleanup, `main` verification, and all remaining GitHub
processing.

==================================================
FINAL ACCEPTANCE
==================================================

DIAG-001 is resolved only after all 13 patches pass the serial gate, the old synchronous
path is removed, exact service restoration and cancellation pass the final owner-assisted
OPNsense matrix, and `docs/AUDIT.md` records final live evidence.

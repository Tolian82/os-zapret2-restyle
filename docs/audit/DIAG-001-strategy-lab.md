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
- PR #50 checks and FreeBSD package build passed;
- squash merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- task branch removed;
- `main` verified before Patch 2 preparation.

==================================================
PATCH 2 EVIDENCE
==================================================

Status:
COMPLETE

- asynchronous job, state, events, cancellation, API/configd, and dormant GUI shell
  implemented;
- PR #51 passed title validation, Validate Project, and FreeBSD package build;
- squash merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- post-merge processing completed and task branch was removed;
- legacy Blockcheck remained active;
- Patch 3 preparation began only after the serial gate closed.

==================================================
PATCH 3 REMEDIATION
==================================================

Status:
SOURCE IMPLEMENTED / AUTOMATED CONTRACT PASSED / IN DELIVERY

Affected files:

- `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/state.sh`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/lifecycle.sh`;
- `scripts/test-strategy-lab-lifecycle.sh`;
- `scripts/test-strategy-lab-job-contract.sh`.

Implemented chain:

Strategy Lab launcher
        ↓
`daemon(8)` starts `zapret_service.sh strategy-lab JOB_ID`
        ↓
service owns `/var/run/zapret2-lifecycle.lock` through descriptor 9
        ↓
worker snapshots complete RUNNING or STOPPED state
        ↓
normal service is stopped and verified absent
        ↓
all later exit paths converge on stage 90
        ↓
exact initial state is restored and verified

Internal `strategy-lab-status`, `strategy-lab-stop`, and `strategy-lab-start` actions
are accepted only when both the inherited lifecycle-owner marker and open descriptor 9
are present. They are not ordinary unlocked service actions.

Automated evidence:

- RUNNING was stopped and restored to RUNNING;
- STOPPED remained STOPPED without start/stop mutation;
- cancel after stop preserved completed stages and restored RUNNING;
- exact Russian and English `SKIPPED` messages were verified;
- second job returned busy while the first remained active;
- injected restore-start failure produced `RESTORE_FAILED` and stage 90 FAIL;
- incomplete initial state failed closed before mutation;
- service-owned transaction inherited descriptor 9;
- an internal lifecycle action without inherited ownership returned status 77;
- POSIX syntax checks passed.

Explicit Patch 3 exclusions:

- no DNS, TLS, IPv4, IPv6, QUIC, HTTP, or UDP probe;
- no temporary candidate dvtws2;
- no temporary candidate firewall rule;
- no active Diagnostics Run-button migration.

==================================================
REMAINING PATCHES
==================================================

Patch 4 implements target validation, network capability precheck, and clean baseline.
Later patches add candidate runtime, family search, stability, reporting, extended
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

Patch 4 preparation is prohibited until Patch 3 completes every PR check, squash merge,
post-merge workflow, branch cleanup, `main` verification, and all remaining GitHub
processing.

==================================================
FINAL ACCEPTANCE
==================================================

DIAG-001 is resolved only after all 13 patches pass the serial gate, the old synchronous
path is removed, exact service restoration and cancellation pass the final owner-assisted
OPNsense matrix, and `docs/AUDIT.md` records final live evidence.

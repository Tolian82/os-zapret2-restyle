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
- initial and restored service state was not represented by a complete staged contract;
- restoration failure could not be reported as `RESTORE_FAILED`;
- process, PF/IPFW, upstream execution, parser, and JSON responsibilities are combined
  in one wrapper;
- textual SUMMARY parsing is not a stable basis for family-first search, required
  endpoints, stability, shortlist, extended protocols, or circular validation;
- there was no persistent asynchronous job, ordered event stream, or controlled partial
  result after cancellation;
- canceled, timed-out, skipped, and unexecuted work could not be represented consistently.

==================================================
APPROVED REMEDIATION
==================================================

Implement the 13-patch asynchronous Strategy Lab architecture in
`docs/architecture/STRATEGY_LAB.md`.

Cancellation preserves completed results, marks interrupted and remaining test work
with the exact selected-language message, executes mandatory restoration, and returns a
partial normal result:

- Russian: `SKIPPED — отменено`;
- English: `SKIPPED — canseled`.

Restoration failure remains `RESTORE_FAILED` regardless of prior results.

==================================================
PATCH 1 EVIDENCE
==================================================

Status: COMPLETE

- architecture and 13-patch sequence recorded;
- PR #50 checks and package build passed;
- squash merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- task branch removed.

==================================================
PATCH 2 EVIDENCE
==================================================

Status: COMPLETE

- asynchronous job, atomic state, events, cancellation, API/configd, and dormant GUI
  shell implemented;
- PR #51 checks and package build passed;
- squash merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- task branch removed;
- legacy Blockcheck remained active.

==================================================
PATCH 3 EVIDENCE
==================================================

Status: COMPLETE

- shared lifecycle transaction and stages 10, 20, and 90 implemented;
- complete RUNNING/STOPPED snapshot and fail-closed incomplete state implemented;
- normal Zapret2 stop and exact final-state restoration implemented;
- cancellation, signal, timeout/error, and normal completion converge on stage 90;
- explicit `RESTORE_FAILED` implemented;
- mocked RUNNING→RUNNING, STOPPED→STOPPED, cancel, incomplete-state, lock-ownership,
  and restore-failure contracts passed;
- first delivery PR #52 was closed after an unrelated stale branch-hygiene revision
  assertion failed;
- clean replacement corrected that test, PR #53 passed every check and the FreeBSD
  package build, and squash merged as
  `100f324d09539e672586b12e3cd96c26baf351b2`;
- task branch removed and `main` verified before Patch 4 preparation.

==================================================
PATCH 4 REMEDIATION
==================================================

Status:
SOURCE IMPLEMENTED / AUTOMATED CONTRACT PASSED / IN DELIVERY

Affected implementation:

- `strategy_lab_launcher.sh` and `strategy_lab/launch.sh`;
- `strategy_lab_worker.sh`;
- new `strategy_lab_probe_runner.sh`;
- `strategy_lab/state.sh`;
- new `strategy_lab/target.sh`;
- new `strategy_lab/request.sh`;
- new `strategy_lab/result.sh`;
- new `strategy_lab/probe.sh`;
- `scripts/test-strategy-lab-job-contract.sh`;
- `scripts/test-strategy-lab-lifecycle.sh`;
- new `scripts/test-strategy-lab-precheck.sh`.

Implemented chain:

stage 00
        ↓
normalize and classify domain or IPv4 target
        ↓
record explicit required endpoints
        ↓
stage 30 under six-second budget
        ↓
run IPv4, IPv6, and fixed QUIC/IPv4 controls concurrently
        ↓
classify enabled/skipped protocol branches
        ↓
stage 40 under five-second budget
        ↓
DNS plus clean TLS 1.3 domain baseline, or direct TCP/443 IPv4 baseline
        ↓
record each endpoint and return TARGET_ACCESSIBLE or continue
        ↓
mandatory stage 90 restoration

Contract details:

- Telegram target `telegram.org` has explicit required endpoints `telegram.org` and
  `web.telegram.org`;
- other domains use the submitted domain as the required endpoint in Patch 4;
- IPv4 targets use an explicit TCP/443 baseline and do not pretend to have hostname,
  SNI, or DNS semantics;
- IPv6 requires both a default IPv6 route and successful IPv6 control connection;
- QUIC control is fixed to `yandex.ru:443`, IPv4, ALPN `h3`, and two seconds;
- QUIC success is determined only from command exit status;
- up to two domain endpoints use the same clean baseline stage;
- DNS, TLS, TCP, prerequisite, timeout, and implementation failures remain distinct;
- an entirely clean-accessible target ends with `TARGET_ACCESSIBLE` before strategy
  search;
- stage timeouts preserve recorded data and execute stage 90.

Automated evidence:

- mixed-case/trailing-dot domain normalization and domain/IP classification passed;
- invalid numeric IPv4-like target rejection passed;
- Telegram two-endpoint resolution passed;
- IPv4-only, complete IPv4/IPv6/QUIC, IPv4 failure, and QUIC status-only scenarios
  passed;
- clean TLS failure, clean success, DNS failure, and IP TCP/443 scenarios passed;
- stage-30 timeout produced final `TIMEOUT` and stage-90 PASS;
- existing async job, lifecycle, cancel, bilingual output, and legacy-path contracts
  continue to pass;
- shell syntax passed for all modified and new scripts.

Explicit Patch 4 exclusions:

- no candidate dvtws2;
- no candidate firewall rules;
- no strategy-family catalog or search;
- no active Diagnostics GUI migration;
- no removal of legacy `blockcheck.sh`.

==================================================
REMAINING PATCHES
==================================================

Patch 5 adds one isolated temporary candidate runtime. Later patches add family search,
parameter expansion, stability, shortlist/reporting, extended protocols, circular
validation, and final synchronous-path replacement.

==================================================
OWNER-ASSISTED VERIFICATION
==================================================

No manual OPNsense checks are requested during Patches 1 through 13. Every patch must
pass automated tests, CI, package build where applicable, full merge processing, and
branch cleanup. One consolidated owner-assisted matrix follows Patch 13.

==================================================
SERIAL DELIVERY BLOCKER
==================================================

Patch 5 preparation is prohibited until Patch 4 completes every PR check, squash merge,
post-merge workflow, branch cleanup, `main` verification, and all remaining GitHub
processing.

==================================================
FINAL ACCEPTANCE
==================================================

DIAG-001 is resolved only after all 13 patches pass the serial gate, the old synchronous
path is removed, and the consolidated owner-assisted OPNsense matrix records successful
end-to-end cancellation, timeout, temporary-runtime cleanup, and exact service
restoration.

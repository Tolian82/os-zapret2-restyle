# DIAG-001 — Synchronous Blockcheck replacement by Strategy Lab

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What is broken in the current Blockcheck chain and how will remediation be verified?

Purpose:
Expand the original timeout-only DIAG-001 finding into the complete approved Strategy
Lab remediation record without deleting the historical evidence in `docs/AUDIT.md`.

Read after:
`docs/AUDIT.md`.

==================================================
CLASSIFICATION
==================================================

Finding:
broken / architecture replacement approved / implementation not started

==================================================
AFFECTED CURRENT LOCATIONS
==================================================

- `src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt`
  - synchronous AJAX request and browser timeout;
  - result parsing and rendering;
- `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php`
  - long synchronous `blockcheckAction()`;
- `src/opnsense/service/conf/actions.d/actions_zapret.conf`
  - synchronous `zapret blockcheck` configd action;
- `src/opnsense/scripts/OPNsense/Zapret/blockcheck.sh`
  - service-state detection;
  - direct service stop/start;
  - PF/IPFW manipulation;
  - upstream blockcheck2 invocation;
  - timeout handling;
  - SUMMARY and partial-winner parsing;
  - JSON result construction.

Related lifecycle authority:

- `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`;
- Backend v2 launcher, firewall, supervisor, and orchestrator modules;
- `/var/run/zapret2-lifecycle.lock`.

==================================================
CURRENT CHAIN
==================================================

Diagnostics GUI
        ↓
600-second browser AJAX request
        ↓
PHP `blockcheckAction()` with raised execution limit
        ↓
650-second backend wait
        ↓
600-second configd action
        ↓
`blockcheck.sh` with 1500-second internal timeout
        ↓
upstream interactive-style blockcheck2 workflow
        ↓
text SUMMARY or synthetic partial SUMMARY

==================================================
CONFIRMED PROBLEMS
==================================================

1. Timeout ownership is inconsistent across browser, PHP, configd, wrapper, and upstream
   work.
2. A long synchronous HTTP request is the wrong transport for a staged multi-minute job.
3. Closing or refreshing the page cannot reliably resume progress display.
4. The wrapper determines initial service state mainly from one dvtws2 PID condition
   rather than the complete service, supervisor, and firewall state contract.
5. The wrapper performs service and firewall mutation outside an explicit complete
   Strategy Lab transaction using the shared lifecycle boundary.
6. Restoration is attempted but is not represented as a separately verified stage.
7. A restoration failure cannot be expressed with the approved `RESTORE_FAILED`
   semantics.
8. Direct PF disable/reload and IPFW manipulation are concentrated in one large wrapper.
9. Upstream text parsing is brittle and does not provide a stable structured stage
   contract.
10. The current winner parser is not a sufficient basis for family-first Zapret2 search,
    endpoint requirements, 3/3 stability, shortlist ranking, or circular validation.
11. The current implementation has no persistent asynchronous job state, event stream,
    or controlled user cancel result.
12. Cancellation or timeout may lose the distinction between completed, skipped, and
    unexecuted work.
13. The current path hardcodes one upstream scan profile instead of the approved numbered
    Strategy Lab stages.
14. Adding all approved behavior to the existing monolithic wrapper would increase
    lifecycle and firewall safety risk.

==================================================
APPROVED REMEDIATION
==================================================

Replace the chain through the 13-patch series in
`docs/architecture/STRATEGY_LAB.md`:

- asynchronous start/status/events/cancel/result job contract;
- one active job;
- shared lifecycle transaction and exact service-state restoration;
- numbered stages 00 through 99;
- fixed IPv4/IPv6/QUIC precheck contract;
- clean target baseline;
- isolated one-candidate runtime;
- family screening;
- accepted-family parameter expansion;
- stability confirmation;
- shortlist and bilingual structured report;
- extended TLS 1.2, HTTP, QUIC, and UDP;
- temporary circular validation;
- final removal of the synchronous caller chain.

The old `blockcheck.sh` is fully rewritten in functional terms. It may temporarily
remain during migration, and the final patch may either delete it or retain only a thin
asynchronous CLI adapter. None of its current long synchronous execution, direct
firewall orchestration, or text SUMMARY parsing remains authoritative.

==================================================
CANCELLATION ACCEPTANCE
==================================================

A user cancel must:

- preserve every completed stage result;
- stop the active probe and temporary candidate runtime;
- remove temporary rules;
- display the interrupted and remaining stages as skipped;
- use exact approved output:
  - `SKIPPED — отменено` for Russian;
  - `SKIPPED — canseled` for English;
- run mandatory cleanup and exact service restoration;
- publish a partial result rather than an ordinary error;
- report `RESTORE_FAILED` if exact restoration fails.

==================================================
TIMEOUT ACCEPTANCE
==================================================

The implementation must enforce:

- per-operation limits;
- per-stage limits;
- 150-second standard overall budget;
- separate 120-second extended budget;
- no new candidate when insufficient budget remains for start, probe, stop, and cleanup;
- preservation of completed results after timeout;
- mandatory restoration after timeout.

Initial exact values are maintained in `docs/architecture/STRATEGY_LAB.md`.

==================================================
AUTOMATED VERIFICATION PLAN BY PATCH
==================================================

Patch 1:

- documentation-only scope;
- no package metadata changes;
- architecture, decision, finding, state, roadmap, and devlog synchronized.

Patch 2:

- asynchronous job ID;
- atomic status;
- ordered events;
- polling;
- bilingual output;
- busy and cancel contract without runtime mutation.

Patch 3:

- RUNNING and STOPPED snapshots;
- normal service stop;
- exact cleanup and restoration;
- cancel, error, and signal paths;
- shared lifecycle exclusion.

Patch 4:

- target validation;
- IPv4 and IPv6 gates;
- fixed QUIC precheck;
- one and two endpoint baseline tests.

Patch 5:

- one temporary dvtws2;
- temporary rules;
- success, failure, timeout, and cancel teardown.

Patch 6:

- seven family representatives;
- strict sequential strategies;
- accepted and rejected family reporting.

Patch 7:

- accepted-family-only expansion;
- candidate budget and early stop;
- preservation of partial findings.

Patch 8:

- 3/3 required-endpoint stability;
- unstable candidate rejection;
- shortlist ranking;
- complete and partial bilingual reports.

Patches 9 through 11:

- extended TLS 1.2/HTTP, QUIC gate, and arbitrary UDP contracts.

Patch 12:

- temporary circular profile, Stop control, cleanup, and restoration.

Patch 13:

- no synchronous browser/PHP/configd execution path;
- no old SUMMARY parser;
- no old direct PF/IPFW wrapper orchestration;
- all callers use the asynchronous contract.

==================================================
OWNER-ASSISTED VERIFICATION
==================================================

By owner decision, no manual OPNsense checks are requested during patches 1 through 13.
Every patch must first pass its automated tests, PR CI, package build where applicable,
merge processing, main workflows, and branch cleanup.

After all patches are complete, one consolidated owner-assisted matrix validates the
full feature and lifecycle behavior. The matrix is defined in
`docs/architecture/STRATEGY_LAB.md` and finalized by patch 13.

==================================================
SERIAL DELIVERY BLOCKER
==================================================

No later Strategy Lab patch may be prepared while the current patch has an open or
failed PR, incomplete checks, incomplete post-merge workflows, an undeleted task branch,
or otherwise unresolved GitHub processing.

This finding is remediated in strict patch order. Skipping ahead invalidates the
approved verification chain.

==================================================
ACCEPTANCE CRITERIA
==================================================

DIAG-001 can be marked resolved only when:

- all 13 patches have passed the serial delivery gate;
- the asynchronous job survives page refresh and supports controlled cancellation;
- normal Zapret2 is absent during baseline and candidate testing;
- only one candidate strategy runs at a time;
- operation, stage, and overall timeouts are enforced;
- completed results survive cancel and timeout;
- exact bilingual messages are produced;
- exact RUNNING-to-RUNNING and STOPPED-to-STOPPED restoration pass;
- restoration failure is explicit;
- old synchronous Blockcheck behavior is removed;
- consolidated owner-assisted OPNsense verification passes;
- `docs/AUDIT.md` is updated with final evidence and resolved status.

==================================================
CURRENT REMEDIATION STATUS
==================================================

Architecture approved and recorded. Implementation has not started. Patch 1 contains
documentation only.

# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered implementation and delivery stages.

Updated when:
A stage starts, completes, changes order, or gains approved work.

Read after:
`docs/DEVLOG.md`.

Do not store here:
Detailed history, architecture rationale, or complete procedures.

==================================================
CURRENT STAGE
==================================================

Milestone 8 — GUI maintenance and managed upstream components

Current source candidate:
`v0.3.2_3`

Current work package:
Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Current patch:
Patch 1 — documentation and approved architecture.

Package metadata:
Unchanged. Patch 1 modifies documentation only.

Specialist plan:
`docs/architecture/STRATEGY_LAB.md`

==================================================
BLOCKING SERIAL DELIVERY RULE
==================================================

The Strategy Lab series is strictly sequential.

Do not prepare, stage, or publish Patch N+1 until Patch N has:

- one final atomic commit;
- one ready pull request;
- all pull-request checks completed successfully;
- one squash merge;
- the resulting `main` commit verified;
- every workflow triggered by the merge completed successfully;
- automatic task-branch cleanup completed;
- the task branch verified absent;
- no remaining unresolved GitHub processing.

This gate applies between every patch listed below.

==================================================
MANUAL VERIFICATION RULE
==================================================

Manual checks requiring project-owner participation are performed only after all
Strategy Lab implementation patches have been published, merged, cleaned up, and fully
processed by GitHub.

Each patch still requires focused automated tests, syntax/static validation, standard
CI, package build where applicable, and synchronized documentation.

==================================================
PATCH 1 — DOCUMENTATION AND APPROVED ARCHITECTURE
==================================================

Status:
IN DELIVERY

Scope:

- [x] Record the complete Strategy Lab product and runtime contract.
- [x] Record stages 00 through 99.
- [x] Record service stop, cleanup, and exact restoration rules.
- [x] Record asynchronous job, online progress, and cancel behavior.
- [x] Record operation, stage, standard, and extended timeout budgets.
- [x] Record the fixed QUIC precheck.
- [x] Record target and endpoint requirements.
- [x] Record family-first search, parameter expansion, 3/3 stability, and shortlist.
- [x] Record extended TLS 1.2, HTTP, QUIC, UDP, and circular scope.
- [x] Record approved English and Russian short messages.
- [x] Record `SKIPPED — отменено` and `SKIPPED — canseled` for canceled stages.
- [x] Record the complete patch sequence.
- [x] Record deferred owner-assisted verification.
- [x] Record the blocking serial GitHub processing gate.
- [x] Keep `VERSION`, `Makefile`, and package revision unchanged.

Completion gate:
PR checks, squash merge, post-merge workflows, automatic branch cleanup, verified
`main`, verified branch absence, and no unresolved GitHub processing.

==================================================
PATCH 2 — ASYNCHRONOUS JOB AND GUI SHELL
==================================================

Status:
BLOCKED BY PATCH 1 GATE

Scope:

- asynchronous start/status/events/cancel/result contract;
- immediate `job_id` response;
- one active job and busy response;
- atomic `status.json` and ordered `events.ndjson`;
- GUI polling and page-refresh recovery;
- online stage/current-operation output;
- Stop test control;
- English default and Russian `ru*` output;
- canceled stage presentation as approved `SKIPPED` messages;
- no real network or Zapret2 runtime mutation yet;
- focused job, polling, busy, cancel, and localization tests.

==================================================
PATCH 3 — LIFECYCLE STOP, CLEANUP, AND RESTORATION
==================================================

Status:
BLOCKED BY PATCH 2 GATE

Scope:

- shared lifecycle exclusion;
- initial RUNNING/STOPPED snapshot;
- reject incomplete initial state;
- stop and verify normal dvtws2, supervisor, and plugin-owned rules;
- mandatory cleanup after normal completion, cancel, timeout, signal, and error;
- exact RUNNING-to-RUNNING and STOPPED-to-STOPPED restoration;
- explicit `RESTORE_FAILED`;
- focused lifecycle and restoration tests.

Implements stages 10, 20, and 90.

==================================================
PATCH 4 — TARGETS, CAPABILITY PRECHECK, AND CLEAN BASELINE
==================================================

Status:
BLOCKED BY PATCH 3 GATE

Scope:

- domain and IP target validation;
- primary target and required endpoints;
- DNS A/AAAA;
- IPv4 control;
- usable IPv6 route and connectivity gate;
- fixed QUIC precheck;
- direct TLS 1.3 baseline;
- one or two required endpoints;
- exclusion of unavailable IPv6 and QUIC branches;
- focused precheck and baseline tests.

Implements stages 00, 30, and 40.

==================================================
PATCH 5 — ONE ISOLATED TEMPORARY CANDIDATE RUNTIME
==================================================

Status:
BLOCKED BY PATCH 4 GATE

Scope:

- temporary candidate runtime;
- one temporary dvtws2;
- candidate-scoped temporary rules;
- up to two endpoint probes under the same strategy;
- complete teardown before the next candidate;
- teardown on success, failure, timeout, cancel, and signal;
- one fixture candidate only;
- focused runtime-isolation tests.

==================================================
PATCH 6 — TLS 1.3 FAMILY SCREENING
==================================================

Status:
BLOCKED BY PATCH 5 GATE

Scope:

- approved family catalog:
  - multisplit;
  - multidisorder;
  - seqovl;
  - fake;
  - fake plus split;
  - syndata;
  - hostfakesplit;
- one representative per family;
- families strictly sequential;
- accept or reject using every required endpoint;
- 45-second stage budget;
- accepted and rejected family messages;
- focused screening tests.

Implements stage 50.

==================================================
PATCH 7 — ACCEPTED-FAMILY PARAMETER EXPANSION
==================================================

Status:
BLOCKED BY PATCH 6 GATE

Scope:

- expand accepted families only;
- split positions, seqovl, approved BLOBs, repeats, out-range, and family-specific
  Zapret2 parameters;
- stop after enough working candidates;
- preserve candidates found before timeout or cancel;
- 60-second stage budget;
- focused expansion, budget, and early-stop tests.

Implements stage 60.

==================================================
PATCH 8 — STABILITY, SHORTLIST, AND REPORT
==================================================

Status:
BLOCKED BY PATCH 7 GATE

Scope:

- sequential fresh connections;
- every required endpoint 3 of 3;
- unstable candidate rejection;
- optional finalist 5 of 5 only when budget permits;
- shortlist of three to five strategies;
- candidate ranking and strategy number 1 recommendation;
- complete and partial bilingual reports;
- report construction only from recorded stages;
- focused stability, ranking, cancellation, timeout, and report tests.

Implements stages 70, 85, and 99.

==================================================
PATCH 9 — EXTENDED TLS 1.2 AND HTTP
==================================================

Status:
BLOCKED BY PATCH 8 GATE

Scope:

- separate extended mode;
- TLS 1.2;
- plain HTTP;
- approved additional URIs;
- separate 120-second extended budget;
- extended profile result messages;
- focused extended web tests.

Implements the TLS 1.2 and HTTP branches of stage 80.

==================================================
PATCH 10 — QUIC STRATEGY BRANCH
==================================================

Status:
BLOCKED BY PATCH 9 GATE

Scope:

- QUIC candidate catalog;
- run only after successful fixed QUIC/IPv4 precheck;
- QUIC/IPv4;
- QUIC/IPv6 only when usable IPv6 exists;
- strict sequential candidates;
- skip the complete branch when QUIC/IPv4 is closed;
- focused QUIC gate and candidate tests.

==================================================
PATCH 11 — ARBITRARY UDP STRATEGY BRANCH
==================================================

Status:
BLOCKED BY PATCH 10 GATE

Scope:

- explicit IP/UDP target and port contract;
- arbitrary UDP probes separate from QUIC;
- UDP candidate catalog;
- UDP result and shortlist reporting;
- focused UDP tests.

==================================================
PATCH 12 — TEMPORARY CIRCULAR LIVE VALIDATION
==================================================

Status:
BLOCKED BY PATCH 11 GATE

Scope:

- temporary circular profile from three to five shortlist strategies;
- target-scoped runtime only;
- separate start/status/stop flow;
- browser or application validation;
- no permanent Traffic Strategy modification;
- complete cleanup and exact service restoration;
- focused circular contract tests.

==================================================
PATCH 13 — FINAL SYNCHRONOUS BLOCKCHECK REPLACEMENT
==================================================

Status:
BLOCKED BY PATCH 12 GATE

Scope:

- remove the long synchronous browser request;
- remove the long PHP/configd execution chain;
- remove old textual SUMMARY and partial-winner parsing;
- remove old direct PF/IPFW wrapper orchestration;
- remove `blockcheck.sh` or retain only a thin asynchronous CLI adapter;
- route every GUI caller through the new asynchronous contract;
- update DIAG-001 implementation status;
- prepare the consolidated owner-assisted OPNsense verification matrix;
- focused final migration and no-old-caller tests.

==================================================
POST-PATCH-13 OWNER-ASSISTED VERIFICATION
==================================================

Status:
BLOCKED UNTIL ALL 13 PATCH GATES COMPLETE

One consolidated OPNsense matrix verifies:

- initially running and initially stopped service states;
- page refresh and online progress;
- cancellation during multiple stages;
- exact canceled-stage English and Russian output;
- operation, stage, and overall timeouts;
- IPv4, IPv6, and QUIC gating where environments permit;
- one and two required endpoints;
- family screening and parameter expansion;
- 3/3 stability and shortlist ranking;
- extended TLS 1.2, HTTP, QUIC, and UDP;
- circular validation;
- cleanup after success, failure, timeout, cancel, and signal;
- explicit restoration failure;
- absence of old synchronous callers and residual temporary runtime.

==================================================
OTHER MILESTONE 8 WORK
==================================================

The following work remains outside the active Strategy Lab series and must not be mixed
into its patches:

- passive notification when a newer stable bol-van/zapret2 release exists;
- additional BLOB repository management after the owner supplies and approves its
  repository and technical contract;
- unrelated diagnostics, duplicate-route, lifecycle, and audit backlog items.

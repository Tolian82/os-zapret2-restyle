# 2026-08-04 — Strategy Lab asynchronous job shell

Logical change:
Implement Patch 2 of the approved Strategy Lab series without network or lifecycle
mutation.

Base:
`76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`

Completed:

- added the detached launcher/worker job boundary;
- added common and state modules;
- added atomic current state and ordered events;
- added one-active-job enforcement and busy result;
- added cancel marker and partial canceled result;
- preserved exact approved canceled-stage strings;
- added start/status/cancel/result configd and API actions;
- added dormant GUI polling/progress/Stop helpers;
- deliberately left the existing Blockcheck button on its legacy endpoint;
- advanced package candidate from `0.3.2_3` to `0.3.2_4`;
- synchronized audit, state, roadmap, workflow, changelog, and patch notes.

Focused verification performed:

- all new shell scripts pass `sh -n`;
- DiagnosticsController passes `php -l`;
- mock daemon creates a detached worker PID;
- start returns a generated job ID immediately;
- a second job reports busy;
- normal framework completion returns honest `PARTIAL`;
- Russian cancellation marks all unfinished stages `SKIPPED — отменено`;
- English cancellation marks all unfinished stages `SKIPPED — canseled`;
- completed and canceled jobs clear the active pointer;
- status returns idle afterward;
- unsafe target syntax is rejected;
- new actions, API methods, and dormant GUI elements are present;
- the legacy `/api/zapret/diagnostics/blockcheck` caller remains present.

Excluded deliberately:

- no network probes;
- no Zapret2 stop or restoration;
- no candidate dvtws2;
- no firewall mutation;
- no active GUI migration.

Next:
Complete the full GitHub gate for Patch 2. Only then begin Patch 3 lifecycle stop,
cleanup, and exact restoration.

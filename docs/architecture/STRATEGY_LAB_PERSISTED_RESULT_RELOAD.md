# Strategy Lab reload and persisted-result contract

## Contract

The backend maintains atomic `latest.job` alongside `active.job`. Every accepted start
writes the new job as latest before publishing it as active. Persisted terminal results
remain available by explicit validated job ID until retention removes them.

Backend status modes are intentionally separate:

- `status @active` is the automatic Diagnostics discovery mode and returns only active work;
- `status -` preserves the historical backend contract: active job first, otherwise the
  latest retained job;
- `status JOB_ID` returns that validated retained job directly.

The API controller uses `@active` when the browser does not provide a validated job ID.
Therefore Diagnostics initialization behaves as follows:

- when `active.job` identifies a queued, running, or cancellation-requested job, the page
  restores that job and resumes polling;
- when there is no active job, the API returns `{ "status": "idle" }` even when a latest
  completed or failed result exists;
- a completed or failed result remains visible in the current page until navigation or
  reload, after which the Strategy Lab controls return to their initial state;
- explicit status/result requests by job ID and backend `status -` continue to expose
  retained evidence.

`latest.job` remains an evidence and retention pointer. For installations predating the
pointer, the backend can scan existing job directories, select the newest valid status,
and repair the pointer. Automatic page initialization does not consume that historical
fallback.

Beginning with Migration Patch 2 (`v0.3.3_19` source), Python 3.13 owns revisioned and
atomic automated-job `status.json`/`events.ndjson` persistence. The active/latest pointer
files remain the existing small shell persistence surface. Private circular-session
`state.json` remains a separate shell-owned contract.

## Patch 8 transient-read reconciliation

Migration Patch 8 (`v0.3.3_25` source) makes automatic Diagnostics discovery consume the
persisted state contract without confusing transport failures with retained job state.

The automated background worker must close launcher lock FD 9 when `daemon(8)` is started,
so the long-lived worker cannot retain the short nonblocking launcher serialization lock
needed by status/result/cancel reads.

Empty or invalid configd output and browser/AJAX failures are classified as transient read
failures. They are not valid automated job snapshots. Diagnostics accepts a job snapshot
only when it has a valid `job.*` identifier and a persisted state of `queued`, `running`,
`cancel_requested`, `completed`, or `error`.

During automatic discovery:

- a valid active snapshot resumes polling immediately;
- a transient read is retried for a bounded number of attempts while the page preserves
  its last valid presentation;
- explicit `{ "status": "idle" }` opens the idle view and never resurrects retained
  terminal history;
- a non-transient invalid/error reply stops automatic discovery without fabricating a
  terminal Strategy Lab state.

During active polling, transient reads preserve the last valid state/progress and polling
continues. The GUI does not replace `data.state` with transport `data.status`.

## Safety

- pointers contain only validated `job.*` IDs with readable status files;
- automated-job status/event writes are atomic and revisioned through the Python owner;
- active ownership remains authoritative;
- a page reload never mutates or deletes saved evidence or lifecycle state;
- terminal results remain available to explicit backend consumers until retention removes them;
- stale terminal errors are not presented as the state of a newly opened Diagnostics page;
- transient transport/read errors are not presented as persisted job ERROR;
- existing backend history consumers retain their `status -` behavior.

## Verification

The focused reload test covers active-only API discovery, idle reload after completed/error
work, historical `status -`, explicit job lookup, latest-pointer repair, and preservation of
stored terminal evidence.

`scripts/test-strategy-lab-gui-status-reconciliation.sh` additionally requires bounded
transient active discovery/retry, persisted-snapshot validation, separation of transport
status from job state, and launcher FD isolation.

The end-to-end suite continues to verify the historical backend recovery contract
independently of GUI initialization. Owner-assisted appliance evidence is still required to
close the frozen `_17` reload/presentation defect.

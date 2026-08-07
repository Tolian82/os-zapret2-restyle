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
files remain the existing small shell persistence surface. This language boundary does
not change any reload, explicit lookup, or retention behavior described above.

Private circular-session `state.json` is a separate contract and remains on its existing
shell writer in Patch 2.

## Safety

- pointers contain only validated `job.*` IDs with readable status files;
- automated-job status/event writes are atomic and revisioned through the Python owner;
- active ownership remains authoritative;
- a page reload never mutates or deletes saved evidence or lifecycle state;
- terminal results remain available to explicit backend consumers until retention removes them;
- stale terminal errors are not presented as the state of a newly opened Diagnostics page;
- existing backend history consumers retain their `status -` behavior.

## Verification

The focused reload test covers active-only API discovery, idle reload after completed/error work,
historical `status -`, explicit job lookup, latest-pointer repair, and preservation of stored
terminal evidence. Migration Patch 2 additionally runs the Python state-persistence regression
for atomic JSON/NDJSON, revision semantics, concurrency, and public progress/schema parity.
The end-to-end suite continues to verify the historical backend recovery contract independently
of GUI initialization.

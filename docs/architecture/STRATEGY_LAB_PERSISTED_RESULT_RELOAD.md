# Strategy Lab reload and persisted-result contract

## Contract

The backend maintains atomic `latest.job` alongside `active.job`. Every accepted start
writes the new job as latest before publishing it as active. Persisted terminal results
remain available by explicit validated job ID until retention removes them.

Automatic Diagnostics initialization uses `status -` only to discover active work:

- when `active.job` identifies a queued, running, or cancellation-requested job, the page
  restores that job and resumes polling;
- when there is no active job, `status -` returns `{ "status": "idle" }` even when a latest
  completed or failed result exists;
- a completed or failed result remains visible in the current page until navigation or
  reload, after which the Strategy Lab controls return to their initial state;
- explicit status/result requests by job ID continue to expose retained evidence.

`latest.job` remains an evidence and retention pointer. For installations predating the
pointer, the backend can scan existing job directories, select the newest valid status,
and repair the pointer. Automatic page initialization does not use that historical pointer.

## Safety

- pointers contain only validated `job.*` IDs with readable status files;
- writes are atomic;
- active ownership remains authoritative;
- a page reload never mutates or deletes saved evidence or lifecycle state;
- terminal results remain available to explicit backend consumers until retention removes them;
- stale terminal errors are not presented as the state of a newly opened Diagnostics page.

## Verification

The focused test covers active-job reload, idle reload after completed/error work, explicit
historical lookup, latest-pointer repair, and preservation of stored terminal evidence.
